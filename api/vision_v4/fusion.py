"""
v4.0 Cross-Image Fusion (Step 8)

Deduplicates items appearing in multiple images.
Uses canonical_label + normalized position for matching.
Keeps best representation (highest confidence, best mask).
"""

from typing import List
from .utils import normalize_bbox_center, vlog


def fuse_across_images(classified_items: List[dict], images: List[dict]) -> List[dict]:
    """
    Deduplicate items appearing in multiple images.
    
    Uses a "track key" based on:
    - canonical_label
    - normalized bbox center (bucketed for position matching)
    
    Args:
        classified_items: List of classified proposal dicts
        images: List of image dicts for dimension lookup
        
    Returns:
        Deduplicated list of fused items
    """
    if not classified_items:
        return []
    
    vlog(f"🔗 Fusing {len(classified_items)} items across {len(images)} images...")
    
    # Build image dimension lookup
    image_dims = {img["image_id"]: (img["width"], img["height"]) for img in images}
    
    # Fusion map: track_key -> best item
    fused = {}
    
    for item in classified_items:
        # Get image dimensions
        dims = image_dims.get(item["image_id"], (1, 1))
        img_w, img_h = dims
        
        # Normalize bbox center to 0-1 range
        norm_x, norm_y = normalize_bbox_center(item["bbox"], img_w, img_h)
        
        # Create track key: label + position bucket (5x5 grid)
        # This groups items with same label in similar positions
        pos_bucket_x = int(norm_x * 5)
        pos_bucket_y = int(norm_y * 5)
        track_key = f"{item['canonical_label']}_{pos_bucket_x}_{pos_bucket_y}"
        
        if track_key not in fused:
            # First occurrence of this item
            fused[track_key] = item
        else:
            # Item already seen - keep better representation
            existing = fused[track_key]
            should_replace = False
            
            # Prefer item with mask
            if item.get("has_mask") and not existing.get("has_mask"):
                should_replace = True
            # Prefer higher classifier confidence
            elif item.get("classifier_confidence", 0) > existing.get("classifier_confidence", 0):
                should_replace = True
            # Prefer higher YOLO score
            elif item.get("score", 0) > existing.get("score", 0):
                should_replace = True
            
            if should_replace:
                fused[track_key] = item
    
    fused_items = list(fused.values())
    
    # Log fusion results
    reduction = len(classified_items) - len(fused_items)
    if reduction > 0:
        vlog(f"   ✅ Fused: {len(classified_items)} → {len(fused_items)} ({reduction} duplicates removed)")
    else:
        vlog(f"   ✅ No duplicates found, {len(fused_items)} unique items")
    
    # Log fused items
    for item in fused_items:
        vlog(f"      • {item['canonical_label']} ({item['image_id'][:8]}...) conf={item.get('classifier_confidence', 0):.2f}")
    
    return fused_items
