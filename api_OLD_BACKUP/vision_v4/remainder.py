"""
v4.0 Remainder Computation (Step 9)

Computes remainder mask coverage (pile - discrete items).
Used for Lane A occupancy volume calculation.
"""

from typing import List
from .utils import vlog


def compute_remainder_stats(
    pile_masks: dict,
    fused_items: List[dict],
    images: List[dict]
) -> dict:
    """
    Compute remainder coverage for each image.
    
    Remainder = pile_mask - union(discrete_item_masks)
    
    Since we don't have actual pixel masks in this implementation,
    we estimate remainder as:
    remainder_ratio = pile_area_ratio - sum(item_area_ratios)
    
    Args:
        pile_masks: Dict mapping image_id -> pile segmentation result
        fused_items: List of fused discrete items
        images: List of image dicts
        
    Returns:
        Dict with per-image and aggregate remainder stats
    """
    vlog(f"📐 Computing remainder coverage...")
    
    remainder_stats = {}
    total_pile_ratio = 0.0
    total_item_ratio = 0.0
    
    for image in images:
        image_id = image["image_id"]
        
        # Get pile coverage for this image
        pile_result = pile_masks.get(image_id, {})
        pile_ratio = pile_result.get("pile_area_ratio", 0)
        
        # Sum item coverage for this image
        image_items = [i for i in fused_items if i["image_id"] == image_id]
        items_ratio = sum(i.get("mask_area_ratio", 0) for i in image_items)
        
        # Remainder = pile - items (clamped to 0)
        remainder_ratio = max(0, pile_ratio - items_ratio)
        
        remainder_stats[image_id] = {
            "pile_ratio": pile_ratio,
            "items_ratio": items_ratio,
            "remainder_ratio": remainder_ratio,
            "item_count": len(image_items)
        }
        
        total_pile_ratio += pile_ratio
        total_item_ratio += items_ratio
    
    # Aggregate stats
    num_images = len(images) if images else 1
    avg_pile_ratio = total_pile_ratio / num_images
    avg_items_ratio = total_item_ratio / num_images
    avg_remainder_ratio = max(0, avg_pile_ratio - avg_items_ratio)
    
    aggregate = {
        "avg_pile_ratio": round(avg_pile_ratio, 4),
        "avg_items_ratio": round(avg_items_ratio, 4),
        "avg_remainder_ratio": round(avg_remainder_ratio, 4),
        "total_item_count": len(fused_items),
        "per_image": remainder_stats
    }
    
    vlog(f"   - Avg pile coverage: {avg_pile_ratio*100:.1f}%")
    vlog(f"   - Avg items coverage: {avg_items_ratio*100:.1f}%")
    vlog(f"   - Avg remainder: {avg_remainder_ratio*100:.1f}%")
    
    return aggregate
