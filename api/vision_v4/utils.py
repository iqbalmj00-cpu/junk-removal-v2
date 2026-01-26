"""
v4.0 Utility Functions

Shared helpers for the vision pipeline.
"""

import base64
import hashlib
import io
import uuid
from typing import Optional, Tuple


def generate_image_id(index: int) -> str:
    """Generate unique image ID."""
    return f"img_{index}_{uuid.uuid4().hex[:8]}"


def generate_proposal_id(image_id: str, bbox: list, label: str) -> str:
    """
    Generate unique proposal ID from image, bbox, and label.
    This is the PRIMARY KEY used throughout the pipeline.
    """
    bbox_str = f"{bbox[0]:.1f}_{bbox[1]:.1f}_{bbox[2]:.1f}_{bbox[3]:.1f}"
    key = f"{image_id}_{bbox_str}_{label}"
    return hashlib.md5(key.encode()).hexdigest()[:12]


def base64_to_bytes(b64_string: str) -> bytes:
    """Convert base64 string to bytes."""
    # Handle data URI prefix if present
    if "," in b64_string:
        b64_string = b64_string.split(",", 1)[1]
    return base64.b64decode(b64_string)


def bytes_to_base64(data: bytes) -> str:
    """Convert bytes to base64 string."""
    return base64.b64encode(data).decode("utf-8")


def base64_to_replicate_file(b64_string: str) -> str:
    """
    Convert base64 image to format Replicate models accept.
    Returns a data URI string (most robust approach).
    """
    # Strip data URI prefix if already present
    if "," in b64_string:
        # Already has prefix, return as-is or reconstruct
        parts = b64_string.split(",", 1)
        if parts[0].startswith("data:"):
            return b64_string
        b64_string = parts[1]
    
    # Return as data URI - works with all Replicate models
    return f"data:image/jpeg;base64,{b64_string}"


def load_image_from_base64(b64_string: str):
    """Load PIL Image from base64 string."""
    from PIL import Image, ImageOps  # Lazy import
    
    img_bytes = base64_to_bytes(b64_string)
    img = Image.open(io.BytesIO(img_bytes))
    # Normalize orientation from EXIF
    img = ImageOps.exif_transpose(img)
    return img


def get_image_metadata(img) -> dict:
    """Extract metadata from PIL Image."""
    return {
        "width": img.width,
        "height": img.height,
        "aspect": img.width / img.height,
        "mode": img.mode,
        "area": img.width * img.height,
    }


def compute_iou(bbox1: list, bbox2: list) -> float:
    """
    Compute Intersection over Union between two bounding boxes.
    Boxes are in format [x0, y0, x1, y1].
    """
    x0_1, y0_1, x1_1, y1_1 = bbox1
    x0_2, y0_2, x1_2, y1_2 = bbox2
    
    # Intersection
    xi0 = max(x0_1, x0_2)
    yi0 = max(y0_1, y0_2)
    xi1 = min(x1_1, x1_2)
    yi1 = min(y1_1, y1_2)
    
    if xi1 <= xi0 or yi1 <= yi0:
        return 0.0
    
    inter_area = (xi1 - xi0) * (yi1 - yi0)
    
    # Union
    area1 = (x1_1 - x0_1) * (y1_1 - y0_1)
    area2 = (x1_2 - x0_2) * (y1_2 - y0_2)
    union_area = area1 + area2 - inter_area
    
    if union_area <= 0:
        return 0.0
    
    return inter_area / union_area


def bbox_area(bbox: list) -> float:
    """Calculate area of bounding box."""
    return (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])


def bbox_area_ratio(bbox: list, image_width: int, image_height: int) -> float:
    """Calculate bbox area as ratio of image area."""
    bbox_a = bbox_area(bbox)
    image_a = image_width * image_height
    return bbox_a / image_a if image_a > 0 else 0.0


def normalize_bbox_center(bbox: list, image_width: int, image_height: int) -> Tuple[float, float]:
    """
    Get normalized center coordinates (0-1 range) for bbox.
    Used for cross-image fusion matching.
    """
    center_x = (bbox[0] + bbox[2]) / 2
    center_y = (bbox[1] + bbox[3]) / 2
    return (center_x / image_width, center_y / image_height)


def vlog(message: str):
    """Verbose logging for debugging."""
    print(f"[v4] {message}")
