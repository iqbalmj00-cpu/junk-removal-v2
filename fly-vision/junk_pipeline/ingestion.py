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


@dataclass 
class IngestedFrame:
    """A validated, normalized frame ready for perception."""
    metadata: FrameMetadata
    image_data: bytes  # Resized to 1024px width
    data_uri: str  # Base64 data URI for Replicate
    
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


def ingest_frame(image_path: str) -> tuple[Optional[IngestedFrame], Optional[FrameMetadata]]:
    """
    Process a single image through Stage 1.
    Returns (IngestedFrame, None) on success, (None, FrameMetadata) on rejection.
    """
    from PIL import Image
    
    path = Path(image_path)
    raw_bytes = path.read_bytes()
    image_id = _generate_image_id(raw_bytes)
    
    img = Image.open(BytesIO(raw_bytes))
    
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
    
    # Calculate quality metrics on original
    blur_score = _calculate_blur_score(img)
    brightness = _calculate_brightness(img)
    ingestion_score = _calculate_ingestion_score(blur_score, brightness, exif_present)
    
    # Build metadata
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
        
    buffer = BytesIO()
    img_resized.save(buffer, format="JPEG", quality=90)
    image_data = buffer.getvalue()
    data_uri = _to_data_uri(img_resized)
    
    frame = IngestedFrame(
        metadata=metadata,
        image_data=image_data,
        data_uri=data_uri,
    )
    
    return frame, None


def run_ingestion(image_paths: list[str]) -> IngestionResult:
    """
    Stage 1 Entry Point: Process all images through ingestion.
    
    Args:
        image_paths: List of absolute paths to images
        
    Returns:
        IngestionResult with validated frames and rejection info
    """
    result = IngestionResult()
    
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
    sorted_paths = [p for _, p in path_hash_pairs]
    
    # Process each frame
    exif_count = 0
    for path in sorted_paths:
        try:
            frame, rejected_meta = ingest_frame(path)
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
