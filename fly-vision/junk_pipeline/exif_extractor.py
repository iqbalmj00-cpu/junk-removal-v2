"""
ExifTool-based metadata extraction for production reliability.

Runs ExifTool on raw original bytes (temp file) to get maximum metadata.
"""

import os
import json
import math
import tempfile
import subprocess
from typing import Optional
from io import BytesIO

from PIL import Image, ImageOps


def is_heic(raw_bytes: bytes) -> bool:
    """Detect HEIC by scanning ftyp brands."""
    if len(raw_bytes) < 32:
        return False
    if raw_bytes[4:8] != b'ftyp':
        return False
    brand_area = raw_bytes[8:40].lower()
    return any(b in brand_area for b in [b'heic', b'heix', b'heif', b'mif1', b'msf1'])


def detect_format(raw_bytes: bytes) -> str:
    """Detect image format from magic bytes."""
    if is_heic(raw_bytes):
        return 'heic'
    if raw_bytes[:2] == b'\xff\xd8':
        return 'jpeg'
    if raw_bytes[:8] == b'\x89PNG\r\n\x1a\n':
        return 'png'
    return 'unknown'


def extract_exif_with_exiftool(raw_bytes: bytes, original_ext: str = '.heic') -> dict:
    """
    Extract EXIF using ExifTool on temp file from raw bytes.
    This is the authoritative extraction method.
    """
    ext_map = {
        'heic': '.heic',
        'jpeg': '.jpg',
        'png': '.png',
        'unknown': '.bin'
    }
    suffix = ext_map.get(detect_format(raw_bytes), original_ext)
    
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
            f.write(raw_bytes)
            temp_path = f.name
        
        result = subprocess.run(
            ['exiftool', '-json', '-n', temp_path],
            capture_output=True, text=True, timeout=10
        )
        
        if result.returncode != 0:
            return {}
        
        data = json.loads(result.stdout)
        if not data:
            return {}
        
        exif = data[0]
        return {
            'Make': exif.get('Make'),
            'Model': exif.get('Model'),
            'FocalLength': exif.get('FocalLength'),
            'FocalLengthIn35mmFilm': exif.get('FocalLengthIn35mmFilm'),
            'Orientation': exif.get('Orientation', 1),
            'LensModel': exif.get('LensModel'),
            'LensSpecification': exif.get('LensSpecification'),
            'DigitalZoomRatio': exif.get('DigitalZoomRatio'),
            'ImageWidth': exif.get('ImageWidth'),
            'ImageHeight': exif.get('ImageHeight'),
            'ExifImageWidth': exif.get('ExifImageWidth'),
            'ExifImageHeight': exif.get('ExifImageHeight'),
        }
    except Exception as e:
        print(f"[EXIFTOOL] Extraction failed: {e}")
        return {}
    finally:
        try:
            os.unlink(temp_path)
        except:
            pass


def decode_and_orient(raw_bytes: bytes) -> tuple[Image.Image, dict]:
    """
    Decode + physically rotate pixels based on EXIF orientation.
    
    Returns:
        (img_oriented, dims_dict)
    """
    # Handle HEIC
    if is_heic(raw_bytes):
        try:
            from pillow_heif import register_heif_opener
            register_heif_opener()
        except ImportError:
            print("[DECODE] pillow_heif not available, HEIC decode may fail")
    
    img_raw = Image.open(BytesIO(raw_bytes))
    decoded_raw_dims = img_raw.size  # Before rotation
    
    # PHYSICALLY rotate pixels based on EXIF orientation
    img_oriented = ImageOps.exif_transpose(img_raw)
    decoded_oriented_dims = img_oriented.size  # After rotation
    
    return img_oriented, {
        'decoded_raw_width': decoded_raw_dims[0],
        'decoded_raw_height': decoded_raw_dims[1],
        'decoded_oriented_width': decoded_oriented_dims[0],
        'decoded_oriented_height': decoded_oriented_dims[1],
    }


def identify_lens(
    exif: dict,
    make: Optional[str] = None,
    model: Optional[str] = None
) -> tuple[str, str, str]:
    """
    Identify lens from available signals.
    
    Fallback ladder:
        1. LensModel (best)
        2. FocalLengthIn35mmFilm (good)
        3. FocalLength + device patterns (MED)
        4. Unknown (gate HIGH)
    
    Returns:
        (lens_id, reason, source)
    """
    lens_model = exif.get('LensModel') or ''
    focal_35mm = exif.get('FocalLengthIn35mmFilm')
    focal_mm = exif.get('FocalLength')
    
    # 1. LensModel (best)
    if lens_model:
        lm = lens_model.lower()
        if 'ultra' in lm or 'wide' in lm:
            return ("ultra", f"LensModel={lens_model}", "lens_model")
        if 'tele' in lm or 'telephoto' in lm:
            return ("tele", f"LensModel={lens_model}", "lens_model")
        return ("main", f"LensModel={lens_model}", "lens_model")
    
    # 2. FocalLengthIn35mmFilm (good)
    if focal_35mm:
        try:
            f35 = float(focal_35mm)
            if f35 <= 15:
                return ("ultra", f"f35={f35:.0f}<=15", "focal_35mm")
            elif 16 <= f35 <= 40:
                return ("main", f"f35={f35:.0f} in [16-40]", "focal_35mm")
            elif f35 > 40:
                return ("tele", f"f35={f35:.0f}>40", "focal_35mm")
        except:
            pass
    
    # 3. FocalLength + device patterns (MED)
    if focal_mm and model:
        try:
            f_mm = float(focal_mm)
            model_lower = model.lower() if model else ''
            
            # iPhone patterns
            if 'iphone' in model_lower:
                if f_mm < 2.5:
                    return ("ultra", f"focal_mm={f_mm:.1f}<2.5", "focal_mm_device")
                elif 2.5 <= f_mm <= 6:
                    return ("main", f"focal_mm={f_mm:.1f} in [2.5-6]", "focal_mm_device")
                else:
                    return ("tele", f"focal_mm={f_mm:.1f}>6", "focal_mm_device")
        except:
            pass
    
    # 4. Unknown (gate HIGH)
    return ("unknown", "no_lens_signals", "fallback")


def compute_fx_diagonal(
    focal_35mm: Optional[float],
    oriented_width: int,
    oriented_height: int,
    digital_zoom_ratio: float = 1.0
) -> tuple[float, float, list[str]]:
    """
    Compute fx/fy using diagonal formula from 35mm equivalent.
    
    Formula: fx = (f35 / 43.27) * diagonal_px
    (43.27mm is full-frame diagonal)
    """
    warnings = []
    
    if focal_35mm and focal_35mm > 0:
        diag_px = math.sqrt(oriented_width**2 + oriented_height**2)
        fx = (focal_35mm / 43.27) * diag_px
        fy = fx
        
        # Apply digital zoom
        if digital_zoom_ratio > 1.0:
            fx *= digital_zoom_ratio
            fy *= digital_zoom_ratio
            warnings.append(f"zoom_applied:{digital_zoom_ratio:.2f}")
        
        return fx, fy, warnings
    
    # Fallback: assume 60° FOV
    diag_px = math.sqrt(oriented_width**2 + oriented_height**2)
    fx = diag_px / (2 * math.tan(math.radians(30)))
    fy = fx
    warnings.append("fallback_fov_60")
    
    return fx, fy, warnings


def apply_zoom_policy(
    digital_zoom_ratio: Optional[float]
) -> tuple[float, float, list[str]]:
    """
    Apply zoom policy: assume 1.0 if missing + soft penalty.
    
    Returns:
        (effective_zoom, anchoring_mult, warnings)
    """
    warnings = []
    anchoring_mult = 1.0
    
    if digital_zoom_ratio is None:
        digital_zoom_ratio = 1.0
        anchoring_mult = 0.85  # Soft penalty
        warnings.append("zoom_unknown_assume_1.0")
    
    return digital_zoom_ratio, anchoring_mult, warnings


def compute_confidence(
    exif_from_server: bool,
    make: Optional[str],
    model: Optional[str],
    lens_id: str,
    fx_source: str
) -> str:
    """
    Compute calibration confidence.
    HIGH requires: server EXIF + Make/Model + known lens + reliable fx.
    """
    # lens_id unknown → can't be HIGH
    if lens_id == "unknown":
        return "MED"
    
    if not exif_from_server:
        return "MED"
    
    if not make or not model:
        return "MED"
    
    if fx_source == "fallback_fov_60":
        return "LOW"
    
    return "HIGH"
