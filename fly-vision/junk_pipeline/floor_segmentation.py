"""
Floor Segmentation Module - SegFormer via HuggingFace Inference API

Provides semantic floor/ground segmentation using:
- nvidia/segformer-b1-finetuned-ade-512-512 (indoor/general scenes)
- nvidia/segformer-b5-finetuned-cityscapes-1024-1024 (outdoor/driveway)

Returns floor mask aligned to working image resolution.
"""

import os
import base64
import requests
import numpy as np
from dataclasses import dataclass, field
from PIL import Image
from io import BytesIO
from typing import Optional


# ============================================================================
# FLOOR-LIKE LABELS PER DATASET
# ============================================================================

# ADE20K dataset (150 classes) - indoor/general scenes
ADE20K_FLOOR_LABELS = {
    "floor",
    "road",
    "path",
    "sidewalk",
    "ground",
    "pavement",
    "earth",
    "carpet",
    "rug",
}

# Cityscapes dataset - outdoor/driving scenes
CITYSCAPES_FLOOR_LABELS = {
    "road",
    "sidewalk",
    "terrain",
    "ground",
}


@dataclass
class FloorSegResult:
    """Result from floor segmentation."""
    floor_mask: Optional[np.ndarray] = None  # bool (H, W)
    floor_area_pct: float = 0.0
    top_labels: list = field(default_factory=list)  # [(label, score), ...]
    model_id: str = ""
    confidence: float = 0.0
    error: Optional[str] = None


def _encode_image_to_jpeg(pil_image: Image.Image, quality: int = 90) -> bytes:
    """Encode PIL image to JPEG bytes."""
    if pil_image.mode != "RGB":
        pil_image = pil_image.convert("RGB")
    buffer = BytesIO()
    pil_image.save(buffer, format="JPEG", quality=quality)
    return buffer.getvalue()


def _decode_base64_mask(mask_b64: str, target_size: tuple) -> np.ndarray:
    """Decode base64-encoded mask and resize to target size."""
    mask_bytes = base64.b64decode(mask_b64)
    mask_img = Image.open(BytesIO(mask_bytes))
    
    # Resize to target size (H, W)
    target_h, target_w = target_size
    if mask_img.size != (target_w, target_h):
        mask_img = mask_img.resize((target_w, target_h), Image.NEAREST)
    
    return np.array(mask_img) > 0


def run_segformer(
    working_pil: Image.Image,
    model_id: str = "nvidia/segformer-b1-finetuned-ade-512-512",
    floor_labels: set = None,
    hf_token: Optional[str] = None
) -> FloorSegResult:
    """
    Run SegFormer segmentation and extract floor mask.
    
    Args:
        working_pil: PIL Image at working resolution
        model_id: HuggingFace model ID
        floor_labels: Set of labels to treat as floor
        hf_token: HuggingFace API token (defaults to HF_TOKEN env var)
    
    Returns:
        FloorSegResult with floor mask and diagnostics
    """
    result = FloorSegResult(model_id=model_id)
    
    # Get token
    token = hf_token or os.environ.get("HF_TOKEN")
    if not token:
        result.error = "No HF_TOKEN found"
        return result
    
    # Determine floor labels based on model
    if floor_labels is None:
        if "cityscapes" in model_id.lower():
            floor_labels = CITYSCAPES_FLOOR_LABELS
        else:
            floor_labels = ADE20K_FLOOR_LABELS
    
    # Encode image
    image_bytes = _encode_image_to_jpeg(working_pil)
    
    # Call HF Inference API
    api_url = f"https://router.huggingface.co/hf-inference/models/{model_id}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "image/jpeg",
    }
    
    try:
        response = requests.post(api_url, headers=headers, data=image_bytes, timeout=30)
        
        if response.status_code != 200:
            result.error = f"API error {response.status_code}: {response.text[:100]}"
            return result
        
        segments = response.json()
        
    except requests.exceptions.Timeout:
        result.error = "API timeout"
        return result
    except Exception as e:
        result.error = f"Request failed: {str(e)[:100]}"
        return result
    
    # Process segments
    target_size = (working_pil.height, working_pil.width)
    combined_mask = np.zeros(target_size, dtype=bool)
    
    label_scores = []
    floor_confidence = 0.0
    
    for segment in segments:
        label = segment.get("label", "").lower()
        score = segment.get("score", 0.0)
        mask_b64 = segment.get("mask")
        
        label_scores.append((label, score))
        
        if label in floor_labels and mask_b64:
            try:
                seg_mask = _decode_base64_mask(mask_b64, target_size)
                combined_mask |= seg_mask
                floor_confidence += score
            except Exception as e:
                print(f"[FloorSeg] Mask decode error for {label}: {e}")
    
    # Sort labels by score
    label_scores.sort(key=lambda x: x[1], reverse=True)
    result.top_labels = label_scores[:10]
    
    # Calculate floor area
    result.floor_mask = combined_mask
    result.floor_area_pct = 100.0 * np.mean(combined_mask)
    result.confidence = min(1.0, floor_confidence)
    
    return result


def run_floor_segmentation(
    working_pil: Image.Image,
    scene_type: str = "unknown",
    hf_token: Optional[str] = None
) -> FloorSegResult:
    """
    Run floor segmentation with model selection based on scene type.
    
    Args:
        working_pil: PIL Image at working resolution
        scene_type: Scene type from BLIP classification (e.g., "driveway", "garage")
        hf_token: HuggingFace API token
    
    Returns:
        FloorSegResult with floor mask
    """
    # Select model based on scene type
    outdoor_keywords = {"driveway", "parking", "lot", "outdoor", "yard", "street"}
    
    if any(kw in scene_type.lower() for kw in outdoor_keywords):
        model_id = "nvidia/segformer-b5-finetuned-cityscapes-1024-1024"
        print(f"[FloorSeg] Using Cityscapes model for scene: {scene_type}")
    else:
        model_id = "nvidia/segformer-b1-finetuned-ade-512-512"
        print(f"[FloorSeg] Using ADE20K model for scene: {scene_type}")
    
    result = run_segformer(working_pil, model_id=model_id, hf_token=hf_token)
    
    # Log diagnostics
    if result.error:
        print(f"[FloorSeg] Error: {result.error}")
    else:
        print(f"[FloorSeg] Floor area: {result.floor_area_pct:.1f}%, "
              f"confidence: {result.confidence:.2f}")
        if result.top_labels:
            labels_str = ", ".join(f"{l}:{s:.2f}" for l, s in result.top_labels[:5])
            print(f"[FloorSeg] Top labels: {labels_str}")
    
    return result
