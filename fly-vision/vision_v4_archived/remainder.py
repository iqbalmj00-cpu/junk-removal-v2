"""
v4.0 Remainder Computation (Step 9)

Computes remainder mask coverage (pile - discrete items).
Used for Lane A occupancy volume calculation.
"""

from typing import List
from statistics import median
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
        Dict with per-image and aggregate remainder stats (avg + median)
    """
    vlog(f"📐 Computing remainder coverage...")
    
    remainder_stats = {}
    total_pile_ratio = 0.0
    total_item_ratio = 0.0
    
    # Collect per-image ratios for median calculation
    pile_ratios_list = []
    items_ratios_list = []
    remainder_ratios_list = []
    
    for image in images:
        image_id = image["image_id"]
        
        # Get pile coverage for this image
        pile_result = pile_masks.get(image_id, {})
        pile_ratio = pile_result.get("pile_area_ratio", 0)
        pile_ratios_list.append(pile_ratio)
        
        # Sum item coverage for this image
        # Phase 5: Bbox safety - use conservative area_min for subtraction
        # - Mask items: use actual mask_area_ratio
        # - Bbox fallback: use bbox_area * 0.4 (conservative inner area)
        BBOX_AREA_FACTOR = 0.4  # Conservative: assume 40% of bbox is actual item
        image_items = [i for i in fused_items if i["image_id"] == image_id]
        items_ratio = sum(
            i.get("mask_area_ratio", 0) if i.get("has_mask") 
            else i.get("bbox_area_ratio", 0) * BBOX_AREA_FACTOR
            for i in image_items
        )
        items_ratios_list.append(items_ratio)
        
        # Remainder = pile - items (clamped to 0)
        remainder_ratio = max(0, pile_ratio - items_ratio)
        remainder_ratios_list.append(remainder_ratio)
        
        remainder_stats[image_id] = {
            "pile_ratio": pile_ratio,
            "items_ratio": items_ratio,
            "remainder_ratio": remainder_ratio,
            "item_count": len(image_items)
        }
        
        total_pile_ratio += pile_ratio
        total_item_ratio += items_ratio
    
    # Aggregate stats (averages for backward compat)
    num_images = len(images) if images else 1
    avg_pile_ratio = total_pile_ratio / num_images
    avg_items_ratio = total_item_ratio / num_images
    avg_remainder_ratio = max(0, avg_pile_ratio - avg_items_ratio)
    
    # FIX #6: Compute true medians for stable K-scaling
    median_pile_ratio = median(pile_ratios_list) if pile_ratios_list else 0
    median_items_ratio = median(items_ratios_list) if items_ratios_list else 0
    median_remainder_ratio = median(remainder_ratios_list) if remainder_ratios_list else 0
    
    aggregate = {
        # Averages (backward compat)
        "avg_pile_ratio": round(avg_pile_ratio, 4),
        "avg_items_ratio": round(avg_items_ratio, 4),
        "avg_remainder_ratio": round(avg_remainder_ratio, 4),
        # Medians (for K-scaling)
        "median_pile_ratio": round(median_pile_ratio, 4),
        "median_items_ratio": round(median_items_ratio, 4),
        "median_remainder_ratio": round(median_remainder_ratio, 4),
        # Counts
        "total_item_count": len(fused_items),
        "per_image": remainder_stats
    }
    
    vlog(f"   - Avg pile coverage: {avg_pile_ratio*100:.1f}%")
    vlog(f"   - Avg items coverage: {avg_items_ratio*100:.1f}%")
    vlog(f"   - Avg remainder: {avg_remainder_ratio*100:.1f}%")
    vlog(f"   - Median pile: {median_pile_ratio*100:.1f}% | items: {median_items_ratio*100:.1f}% | remainder: {median_remainder_ratio*100:.1f}%")
    
    return aggregate

