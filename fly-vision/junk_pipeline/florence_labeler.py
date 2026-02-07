"""
Florence-2 Box Labeling Engine

Crops each DINO candidate box and sends it to Florence-2 (via Replicate)
for independent captioning. Returns accurate descriptions that Qwen uses
to make better accept/reject decisions.

Architecture:
  DINO (recall) → Florence-2 (label) → Qwen (decide) → SAM2 (segment)
"""

import io
import base64
from PIL import Image
from typing import List

# =============================================================================
# CONFIGURATION
# =============================================================================

FLORENCE_MODEL = "lucataco/florence-2-large:da53547e17d45b9cfb48174b2f18af8b83ca020fa76db62136bf9c6616762595"
CROP_PAD_RATIO = 0.10  # Expand each box by 10% for context

# Keywords for grass-only detection
_GRASS_KEYWORDS = {"grass", "lawn", "field", "grassland", "meadow"}
_JUNK_KEYWORDS = {
    "pile", "trash", "debris", "bags", "wood", "junk", "logs", "boxes",
    "cardboard", "lumber", "pallets", "leaves", "stalks", "branches",
    "garbage", "waste", "sand", "bricks", "furniture", "mattress",
}


def _is_grass_only(description: str) -> bool:
    """
    Check if a Florence-2 caption describes ONLY grass/field with no junk.
    
    Returns True for:
      "a field of grass"                          → grass is main subject
      "a person standing in front of a field of grass"  → grass is main subject
    Returns False for:
      "cardboard boxes on a grass covered field"  → junk IS present
      "a pile of trash sitting on top of a grass covered field"  → junk IS present
    """
    desc_lower = description.lower()
    has_grass = any(kw in desc_lower for kw in _GRASS_KEYWORDS)
    has_junk = any(kw in desc_lower for kw in _JUNK_KEYWORDS)
    return has_grass and not has_junk


# =============================================================================
# HELPERS
# =============================================================================

def _crop_box(image: Image.Image, box: list, pad_ratio: float = CROP_PAD_RATIO) -> Image.Image:
    """
    Crop a region from the image with padding for context.
    
    Args:
        image: Full PIL image
        box: [x1, y1, x2, y2] coordinates
        pad_ratio: Fraction of box size to add as padding
        
    Returns:
        Cropped PIL image
    """
    x1, y1, x2, y2 = box
    w = x2 - x1
    h = y2 - y1
    
    # Add padding
    pad_x = w * pad_ratio
    pad_y = h * pad_ratio
    
    # Clamp to image bounds
    cx1 = max(0, int(x1 - pad_x))
    cy1 = max(0, int(y1 - pad_y))
    cx2 = min(image.width, int(x2 + pad_x))
    cy2 = min(image.height, int(y2 + pad_y))
    
    return image.crop((cx1, cy1, cx2, cy2))


def _pil_to_data_uri(img: Image.Image, max_dim: int = 512) -> str:
    """Convert PIL image crop to data URI for Replicate."""
    # Resize if needed (crops are small, keep it efficient)
    if max(img.size) > max_dim:
        ratio = max_dim / max(img.size)
        new_size = (int(img.width * ratio), int(img.height * ratio))
        img = img.resize(new_size, Image.LANCZOS)
    
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=85)
    b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/jpeg;base64,{b64}"


# =============================================================================
# MAIN FUNCTION
# =============================================================================

def label_boxes(
    image_pil: Image.Image,
    candidate_boxes: List[dict],
) -> List[dict]:
    """
    Label each DINO candidate box using Florence-2 captioning.
    
    Crops each box region from the full image, sends it to Florence-2
    via Replicate for a short caption, and adds the description to each box.
    
    Args:
        image_pil: Full PIL image (original resolution)
        candidate_boxes: List of {box: [x1,y1,x2,y2], label: str, confidence: float}
        
    Returns:
        Same list with added 'florence_description' field per box
    """
    import replicate
    
    if not candidate_boxes:
        return candidate_boxes
    
    print(f"[FLORENCE] Labeling {len(candidate_boxes)} box crops...")
    
    for i, box_info in enumerate(candidate_boxes):
        try:
            # Crop the box region with padding
            crop = _crop_box(image_pil, box_info['box'])
            crop_uri = _pil_to_data_uri(crop)
            
            # Call Florence-2 Caption task
            output = replicate.run(
                FLORENCE_MODEL,
                input={
                    "image": crop_uri,
                    "task_input": "Caption",
                }
            )
            
            # Parse output — Florence-2 returns {"text": "...", "img": null}
            if isinstance(output, dict):
                description = output.get("text", "").strip()
            elif isinstance(output, str):
                description = output.strip()
            else:
                description = str(output).strip()
            
            # Clean up Florence-2's output format: often returns {"<CAPTION>": "text"}
            if description.startswith("{") and "<CAPTION>" in description:
                import json
                try:
                    parsed = json.loads(description.replace("'", '"'))
                    description = parsed.get("<CAPTION>", description)
                except:
                    pass
            
            box_info['florence_description'] = description
            grass_only = _is_grass_only(description)
            box_info['florence_grass_only'] = grass_only
            flag = " [GRASS_ONLY → auto-reject]" if grass_only else ""
            print(f"[FLORENCE] Box {i+1}: \"{description}\"{flag}")
            
        except Exception as e:
            print(f"[FLORENCE] Box {i+1} error: {e}")
            box_info['florence_description'] = "description unavailable"
            box_info['florence_grass_only'] = False
    
    return candidate_boxes
