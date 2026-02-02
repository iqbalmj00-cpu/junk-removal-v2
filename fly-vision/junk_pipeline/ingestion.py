"""
Stage 1: Hardened Ingestion (The Input Contract)
Goal: Reject bad data immediately and establish the "Physics Baseline."
"""

import base64
import hashlib
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path
from typing import Optional

# v6.7.0: Import CalibrationBundle for production-grade intrinsics
from .calibration_bundle import CalibrationBundle

# Constants
TARGET_WIDTH = 1024  # Resolution lock
BLUR_THRESHOLD = 100.0  # Laplacian variance threshold
BRIGHTNESS_MIN = 30  # Minimum mean pixel intensity
BRIGHTNESS_MAX = 225  # Maximum mean pixel intensity
INGESTION_SCORE_REJECT = 40  # Below this = reject


@dataclass
class FrameMetadata:
    """Extracted metadata for a single frame."""
    image_id: str
    original_path: str
    width: int
    height: int
    focal_length_mm: Optional[float] = None
    device_model: Optional[str] = None
    orientation: int = 1
    blur_score: float = 0.0
    brightness: float = 128.0
    exif_present: bool = False
    ingestion_score: int = 100
    rejected: bool = False
    rejection_reason: Optional[str] = None
    
    # v6.5.1: Extended tracking fields
    # File identity
    file_name: str = ""
    file_size_bytes: int = 0
    file_hash: str = ""  # Full SHA256
    
    # EXIF details
    camera_make: Optional[str] = None
    focal_length_35mm: Optional[float] = None
    image_width_exif: Optional[int] = None
    image_height_exif: Optional[int] = None
    exif_tags_found: list = None  # Key tags present
    
    # Decode/resize trace
    original_width: int = 0
    original_height: int = 0
    orientation_applied: bool = False
    resize_applied: bool = False
    final_width: int = 0
    final_height: int = 0
    output_quality: int = 90
    
    # v6.6.0: Preprocessed pixel hash for cache determinism
    preproc_sha256: str = ""


@dataclass 
class IngestedFrame:
    """A validated, normalized frame ready for perception."""
    metadata: FrameMetadata
    image_data: bytes  # Resized to 1024px width
    data_uri: str  # Base64 data URI for Replicate
    calibration_bundle: Optional[CalibrationBundle] = None  # v6.7.0
    
    def get_pil(self):
        """Get PIL Image from stored image_data bytes."""
        from PIL import Image
        from io import BytesIO
        return Image.open(BytesIO(self.image_data))


@dataclass
class IngestionResult:
    """Result of Stage 1 ingestion."""
    frames: list[IngestedFrame] = field(default_factory=list)
    rejected_frames: list[FrameMetadata] = field(default_factory=list)
    uncalibrated_mode: bool = False  # True if no EXIF on any frame


def _generate_image_id(image_bytes: bytes) -> str:
    """Content-based hash for stable image identity (Rule 139)."""
    return hashlib.sha256(image_bytes).hexdigest()[:16]


def _extract_exif(img) -> dict:
    """Extract EXIF metadata from PIL Image."""
    exif_data = {}
    try:
        from PIL.ExifTags import TAGS
        raw_exif = img._getexif()
        if raw_exif:
            for tag_id, value in raw_exif.items():
                tag = TAGS.get(tag_id, tag_id)
                exif_data[tag] = value
    except Exception:
        pass
    return exif_data


# Key EXIF tags to track for logging
KEY_EXIF_TAGS = [
    'Make', 'Model', 'FocalLength', 'FocalLengthIn35mmFilm',
    'ImageWidth', 'ImageLength', 'ExifImageWidth', 'ExifImageHeight',
    'Orientation', 'DateTime', 'DateTimeOriginal', 'Software', 
    'ExifOffset', 'GPSInfo', 'LensModel', 'FNumber', 'ISOSpeedRatings',
    'ExposureTime'
]


def _get_jpeg_markers(raw_bytes: bytes) -> dict:
    """Check for JPEG APP markers (EXIF, ICC, XMP)."""
    markers = {
        'has_exif_app1': False,
        'has_icc': False,
        'has_xmp': False,
    }
    try:
        # EXIF APP1 marker: FF E1
        if b'\xff\xe1' in raw_bytes[:1000]:
            markers['has_exif_app1'] = True
        # ICC profile marker: FF E2 with 'ICC_PROFILE'
        if b'ICC_PROFILE' in raw_bytes[:5000]:
            markers['has_icc'] = True
        # XMP marker: 'http://ns.adobe.com/xap'
        if b'http://ns.adobe.com/xap' in raw_bytes[:10000]:
            markers['has_xmp'] = True
    except Exception:
        pass
    return markers


def _compute_pixel_hash(img) -> str:
    """Compute SHA256 of raw RGB pixel data after preprocessing."""
    import numpy as np
    try:
        arr = np.array(img.convert('RGB'))
        return hashlib.sha256(arr.tobytes()).hexdigest()[:64]
    except Exception:
        return "error"


def _log_ingestion_fingerprint(
    frame_id: str,
    file_name: str,
    raw_bytes: bytes,
    exif: dict,
    metadata: FrameMetadata,
    original_size: tuple,
    post_orient_size: tuple,
    final_size: tuple,
    preproc_hash: str
):
    """
    v6.5.1: Comprehensive Ingestion Fingerprint per frame.
    
    Logs:
    A. Raw file identity (proves identical files)
    B. EXIF/metadata extraction (proves what survives)
    C. Decode + orientation trace (proves pixel geometry)
    D. Resize/preprocess trace with pixel hash (smoking gun)
    """
    markers = _get_jpeg_markers(raw_bytes)
    file_hash = hashlib.sha256(raw_bytes).hexdigest()
    
    print(f"\n[FINGERPRINT] ========== Frame {frame_id[:8]} ==========")
    
    # A. Raw File Identity
    print(f"[FINGERPRINT] A. Raw File Identity:")
    print(f"  frame_id: {frame_id}")
    print(f"  orig_filename: {file_name}")
    print(f"  byte_len: {len(raw_bytes):,}")
    print(f"  sha256: {file_hash[:64]}")
    print(f"  jpeg_markers: EXIF_APP1={markers['has_exif_app1']}, ICC={markers['has_icc']}, XMP={markers['has_xmp']}")
    
    # B. EXIF / Metadata Extraction
    print(f"[FINGERPRINT] B. EXIF Extraction:")
    print(f"  exif_present: {metadata.exif_present}")
    if metadata.exif_present:
        print(f"  make: {exif.get('Make', 'N/A')}")
        print(f"  model: {exif.get('Model', 'N/A')}")
        print(f"  lens_model: {exif.get('LensModel', 'N/A')}")
        focal = exif.get('FocalLength')
        if focal and hasattr(focal, 'numerator'):
            focal = float(focal)
        print(f"  focal_length_mm: {focal}")
        print(f"  focal_length_35mm: {exif.get('FocalLengthIn35mmFilm', 'N/A')}")
        fnumber = exif.get('FNumber')
        if fnumber and hasattr(fnumber, 'numerator'):
            fnumber = float(fnumber)
        print(f"  f_number: {fnumber}")
        print(f"  iso: {exif.get('ISOSpeedRatings', 'N/A')}")
        exp = exif.get('ExposureTime')
        if exp and hasattr(exp, 'numerator'):
            exp = f"1/{int(1/float(exp))}" if float(exp) < 1 else str(float(exp))
        print(f"  exposure_time: {exp}")
        print(f"  orientation: {exif.get('Orientation', 1)}")
        print(f"  pixel_x_dim: {exif.get('ExifImageWidth', exif.get('ImageWidth', 'N/A'))}")
        print(f"  pixel_y_dim: {exif.get('ExifImageHeight', exif.get('ImageLength', 'N/A'))}")
        print(f"  datetime_original: {exif.get('DateTimeOriginal', exif.get('DateTime', 'N/A'))}")
        print(f"  gps_present: {'GPSInfo' in exif}")
        print(f"  exif_source: embedded")
    else:
        print(f"  exif_source: none")
    
    # C. Decode + Orientation Trace
    orient_val = metadata.orientation
    orient_map = {1: 'none', 3: 'rotate180', 6: 'rotate90_cw', 8: 'rotate270_cw'}
    orient_applied = orient_map.get(orient_val, f'val_{orient_val}')
    
    print(f"[FINGERPRINT] C. Decode/Orient Trace:")
    print(f"  decoded_w: {original_size[0]}")
    print(f"  decoded_h: {original_size[1]}")
    print(f"  orientation_applied: {orient_applied}")
    print(f"  post_orient_w: {post_orient_size[0]}")
    print(f"  post_orient_h: {post_orient_size[1]}")
    
    # D. Resize/Preprocess Trace
    resize_applied = post_orient_size[0] != final_size[0]
    print(f"[FINGERPRINT] D. Resize/Preprocess Trace:")
    print(f"  resize_policy: max_width_{TARGET_WIDTH}")
    print(f"  target_w: {TARGET_WIDTH}")
    print(f"  resample_method: LANCZOS")
    print(f"  final_w: {final_size[0]}")
    print(f"  final_h: {final_size[1]}")
    print(f"  output_quality: 90 (JPEG)")
    print(f"  preproc_sha256: {preproc_hash}")
    print(f"[FINGERPRINT] ==========================================\n")



def _calculate_blur_score(img) -> float:
    """Laplacian variance for blur detection."""
    try:
        import numpy as np
        gray = img.convert("L")
        arr = np.array(gray, dtype=np.float64)
        # Laplacian kernel approximation
        laplacian = (
            arr[:-2, 1:-1] + arr[2:, 1:-1] + 
            arr[1:-1, :-2] + arr[1:-1, 2:] - 
            4 * arr[1:-1, 1:-1]
        )
        return float(np.var(laplacian))
    except Exception:
        return 0.0


def _calculate_brightness(img) -> float:
    """Mean pixel intensity."""
    try:
        import numpy as np
        gray = img.convert("L")
        return float(np.mean(np.array(gray)))
    except Exception:
        return 128.0


def _calculate_ingestion_score(
    blur_score: float,
    brightness: float,
    exif_present: bool
) -> int:
    """
    Calculate quality score (0-100).
    Deductions:
    - Blur below threshold: -40
    - Brightness out of range: -30
    - No EXIF: -20
    """
    score = 100
    
    if blur_score < BLUR_THRESHOLD:
        score -= 40
    
    if brightness < BRIGHTNESS_MIN or brightness > BRIGHTNESS_MAX:
        score -= 30
    
    if not exif_present:
        score -= 20
    
    return max(0, score)


def _resize_to_target(img, target_width: int = TARGET_WIDTH):
    """Resize image to target width, preserving aspect ratio."""
    w, h = img.size
    if w <= target_width:
        return img
    ratio = target_width / w
    new_h = int(h * ratio)
    return img.resize((target_width, new_h), resample=3)  # LANCZOS


def _normalize_orientation(img, orientation: int):
    """Apply EXIF orientation correction."""
    from PIL import ImageOps
    try:
        return ImageOps.exif_transpose(img)
    except Exception:
        return img


def _to_data_uri(img, format: str = "JPEG") -> str:
    """Convert PIL Image to base64 data URI."""
    # Convert RGBA to RGB for JPEG compatibility
    if img.mode == "RGBA":
        background = Image.new("RGB", img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[3])  # 3 is alpha channel
        img = background
    elif img.mode != "RGB":
        img = img.convert("RGB")
        
    buffer = BytesIO()
    img.save(buffer, format=format, quality=90)
    b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
    mime = "image/jpeg" if format == "JPEG" else "image/png"
    return f"data:{mime};base64,{b64}"


def ingest_frame(image_path: str, frontend_exif: Optional[dict] = None) -> tuple[Optional[IngestedFrame], Optional[FrameMetadata]]:
    """
    Process a single image through Stage 1.
    Returns (IngestedFrame, None) on success, (None, FrameMetadata) on rejection.
    """
    from PIL import Image
    
    path = Path(image_path)
    raw_bytes = path.read_bytes()
    image_id = _generate_image_id(raw_bytes)
    file_hash = hashlib.sha256(raw_bytes).hexdigest()
    
    img = Image.open(BytesIO(raw_bytes))
    
    # Capture original decoded size BEFORE orientation
    original_size = img.size
    
    # Extract EXIF before any transforms
    exif = _extract_exif(img)
    orientation = exif.get("Orientation", 1)
    focal_length = exif.get("FocalLength")
    if focal_length and hasattr(focal_length, "numerator"):
        focal_length = float(focal_length)
    device_model = exif.get("Model")
    exif_present = bool(exif)
    
    # Normalize orientation
    img = _normalize_orientation(img, orientation)
    post_orient_size = img.size  # After orientation correction
    orientation_applied = (original_size != post_orient_size) or orientation != 1
    
    # Calculate quality metrics on original
    blur_score = _calculate_blur_score(img)
    brightness = _calculate_brightness(img)
    ingestion_score = _calculate_ingestion_score(blur_score, brightness, exif_present)
    
    # Build metadata with extended fields
    metadata = FrameMetadata(
        image_id=image_id,
        original_path=str(path),
        width=img.width,
        height=img.height,
        focal_length_mm=focal_length,
        device_model=device_model,
        orientation=orientation,
        blur_score=blur_score,
        brightness=brightness,
        exif_present=exif_present,
        ingestion_score=ingestion_score,
        # Extended tracking fields
        file_name=path.name,
        file_size_bytes=len(raw_bytes),
        file_hash=file_hash,
        camera_make=exif.get("Make"),
        focal_length_35mm=exif.get("FocalLengthIn35mmFilm"),
        image_width_exif=exif.get("ExifImageWidth", exif.get("ImageWidth")),
        image_height_exif=exif.get("ExifImageHeight", exif.get("ImageLength")),
        original_width=original_size[0],
        original_height=original_size[1],
        orientation_applied=orientation_applied,
    )
    
    # Decision gate
    if ingestion_score < INGESTION_SCORE_REJECT:
        reasons = []
        if blur_score < BLUR_THRESHOLD:
            reasons.append("too_blurry")
        if brightness < BRIGHTNESS_MIN:
            reasons.append("too_dark")
        if brightness > BRIGHTNESS_MAX:
            reasons.append("too_bright")
        metadata.rejected = True
        metadata.rejection_reason = "+".join(reasons) if reasons else "low_quality"
        return None, metadata
    
    # Resolution lock: resize to 1024px width
    img_resized = _resize_to_target(img, TARGET_WIDTH)
    final_size = img_resized.size
    metadata.resize_applied = (post_orient_size != final_size)
    metadata.final_width = final_size[0]
    metadata.final_height = final_size[1]
    metadata.width = img_resized.width
    metadata.height = img_resized.height
    
    # Convert to bytes and data URI
    # Ensure RGB mode for JPEG compatibility
    if img_resized.mode == "RGBA":
        from PIL import Image
        background = Image.new("RGB", img_resized.size, (255, 255, 255))
        background.paste(img_resized, mask=img_resized.split()[3])
        img_resized = background
    elif img_resized.mode != "RGB":
        img_resized = img_resized.convert("RGB")
    
    # Compute preproc pixel hash (the "smoking gun")
    preproc_hash = _compute_pixel_hash(img_resized)
    
    # v6.6.0: Store in metadata for Lane B cache lookup
    metadata.preproc_sha256 = preproc_hash
    
    # Log comprehensive fingerprint
    _log_ingestion_fingerprint(
        frame_id=image_id,
        file_name=path.name,
        raw_bytes=raw_bytes,
        exif=exif,
        metadata=metadata,
        original_size=original_size,
        post_orient_size=post_orient_size,
        final_size=final_size,
        preproc_hash=preproc_hash
    )
        
    buffer = BytesIO()
    img_resized.save(buffer, format="JPEG", quality=90)
    image_data = buffer.getvalue()
    data_uri = _to_data_uri(img_resized)
    
    # v6.7.0: Build CalibrationBundle with production intrinsics
    calibration_bundle = None
    try:
        from .bundle_builder import build_calibration_bundle
        calibration_bundle = build_calibration_bundle(
            raw_bytes=raw_bytes,
            model_width=final_size[0],
            model_height=final_size[1],
            frontend_exif=frontend_exif,  # v6.7.1: Use frontend EXIF
            frame_id=image_id
        )
    except Exception as e:
        print(f"[INGESTION] CalibrationBundle build failed: {e}")
    
    frame = IngestedFrame(
        metadata=metadata,
        image_data=image_data,
        data_uri=data_uri,
        calibration_bundle=calibration_bundle,
    )
    
    return frame, None


def run_ingestion(image_paths: list[str], exif_data: Optional[list[dict]] = None) -> IngestionResult:
    """
    Stage 1 Entry Point: Process all images through ingestion.
    
    Args:
        image_paths: List of absolute paths to images
        exif_data: Optional list of frontend-extracted EXIF dicts
        
    Returns:
        IngestionResult with validated frames and rejection info
    """
    result = IngestionResult()
    
    # === HASH-BASED EXIF MATCHING (stable, not index-based) ===
    # v6.7.2: Server adds serverSha256 to each entry (authoritative key)
    hash_to_exif = {}
    if exif_data:
        for exif_entry in exif_data:
            # v6.7.2: serverSha256 is set by modal_app.py (server-computed, authoritative)
            server_hash = exif_entry.get('serverSha256')
            if server_hash:
                hash_to_exif[server_hash] = exif_entry
                print(f"[EXIF_MATCH] Registered (server): {server_hash[:16]}... → {exif_entry.get('make')} {exif_entry.get('model')}")
            else:
                # Fallback for legacy clients: try compressedSha256
                compressed_hash = exif_entry.get('compressedSha256')
                if compressed_hash:
                    hash_to_exif[compressed_hash] = exif_entry
                    print(f"[EXIF_MATCH] Registered (client): {compressed_hash[:16]}... → {exif_entry.get('make')} {exif_entry.get('model')}")
    
    # Sort by content hash for deterministic ordering (Rule 139)
    path_hash_pairs = []
    for path in image_paths:
        try:
            raw = Path(path).read_bytes()
            h = hashlib.sha256(raw).hexdigest()
            path_hash_pairs.append((h, path))
        except Exception:
            continue
    
    path_hash_pairs.sort(key=lambda x: x[0])
    
    # Process each frame WITH HASH-BASED EXIF MATCHING
    exif_count = 0
    for file_hash, path in path_hash_pairs:
        try:
            # Match EXIF by hash (stable, not index-based)
            frontend_exif = hash_to_exif.get(file_hash, {})
            if frontend_exif:
                print(f"[EXIF_MATCH] Matched: {file_hash[:16]}... → {frontend_exif.get('make')} {frontend_exif.get('model')}")
            else:
                print(f"[EXIF_MATCH] No match for: {file_hash[:16]}... (hash_to_exif has {len(hash_to_exif)} entries)")
            frame, rejected_meta = ingest_frame(path, frontend_exif=frontend_exif)
            if frame:
                result.frames.append(frame)
                if frame.metadata.exif_present:
                    exif_count += 1
            elif rejected_meta:
                result.rejected_frames.append(rejected_meta)
        except Exception as e:
            # Create rejection metadata for failed loads
            result.rejected_frames.append(FrameMetadata(
                image_id="LOAD_FAILED",
                original_path=path,
                width=0,
                height=0,
                rejected=True,
                rejection_reason=f"load_error:{str(e)[:50]}",
            ))
    
    # Set uncalibrated mode if no EXIF anywhere
    if exif_count == 0 and result.frames:
        result.uncalibrated_mode = True
    
    return result
