"""
v4.0 Volume Engine (Step 10)

Two-lane volume computation:
- Lane A: Occupancy from remainder coverage
- Lane B: Catalog sum from discrete items
"""

from typing import List
from .constants import (
    CATALOG_VOLUMES, 
    DEFAULT_VOLUME,
    HEAVY_ITEMS,
    EWASTE_ITEMS,
    TWO_PERSON_ITEMS,
    PRICING_TIERS
)
from .utils import vlog


def get_catalog_volume(canonical_label: str, size_bucket: str) -> float:
    """
    Look up volume from catalog.
    
    Args:
        canonical_label: Standardized item label
        size_bucket: Size classification (small, medium, large, xlarge)
        
    Returns:
        Volume in cubic yards
    """
    key = (canonical_label.lower(), size_bucket.lower())
    return CATALOG_VOLUMES.get(key, DEFAULT_VOLUME)


def compute_lane_b_catalog(fused_items: List[dict]) -> dict:
    """
    Compute Lane B: Catalog volume from discrete items.
    
    Args:
        fused_items: List of fused, classified items
        
    Returns:
        Dict with total volume and per-item breakdown
    """
    total_volume = 0.0
    item_volumes = []
    
    for item in fused_items:
        label = item.get("canonical_label", "unknown")
        size = item.get("size_bucket", "medium")
        category = item.get("category", "furniture")
        
        # Get base volume
        base_vol = get_catalog_volume(label, size)
        
        # Apply category multipliers
        if category == "appliance":
            base_vol *= 1.2
        elif category == "hazmat":
            base_vol *= 1.3
        
        total_volume += base_vol
        item_volumes.append({
            "label": label,
            "size": size,
            "volume": round(base_vol, 2),
            "proposal_id": item.get("proposal_id", "")
        })
    
    return {
        "total": round(total_volume, 2),
        "items": item_volumes,
        "count": len(item_volumes)
    }


def compute_lane_a_occupancy(remainder_stats: dict) -> dict:
    """
    Compute Lane A: Occupancy volume from remainder coverage.
    
    Uses scene priors to convert area coverage to volume:
    - Estimated visible area per image
    - Height prior for pile
    - Fill factor for compaction
    
    Args:
        remainder_stats: Aggregate remainder statistics
        
    Returns:
        Dict with occupancy volume and calculation breakdown
    """
    avg_remainder_ratio = remainder_stats.get("avg_remainder_ratio", 0)
    
    # Scene priors
    VISIBLE_SQFT_PER_IMAGE = 50  # Approximate visible floor area
    HEIGHT_PRIOR_FT = 2.5        # Average pile height
    FILL_FACTOR = 0.55           # Compaction factor
    
    # Calculate volume
    # remainder_ratio * visible_area = covered sqft
    # covered_sqft * height * fill_factor = cubic feet
    # cubic feet / 27 = cubic yards
    
    covered_sqft = avg_remainder_ratio * VISIBLE_SQFT_PER_IMAGE
    cubic_feet = covered_sqft * HEIGHT_PRIOR_FT * FILL_FACTOR
    cubic_yards = cubic_feet / 27
    
    return {
        "total": round(cubic_yards, 2),
        "remainder_ratio": avg_remainder_ratio,
        "covered_sqft": round(covered_sqft, 2),
        "height_prior": HEIGHT_PRIOR_FT,
        "fill_factor": FILL_FACTOR
    }


def compute_two_lane_volume(
    fused_items: List[dict],
    remainder_stats: dict
) -> dict:
    """
    Compute final two-lane volume.
    
    Args:
        fused_items: List of fused, classified items
        remainder_stats: Aggregate remainder statistics
        
    Returns:
        Complete volume breakdown with final result
    """
    vlog(f"📊 Computing two-lane volume...")
    
    # Lane B: Catalog
    lane_b = compute_lane_b_catalog(fused_items)
    vlog(f"   Lane B (Catalog): {lane_b['total']} yd³ ({lane_b['count']} items)")
    
    # Lane A: Occupancy
    lane_a = compute_lane_a_occupancy(remainder_stats)
    vlog(f"   Lane A (Occupancy): {lane_a['total']} yd³ (remainder={lane_a['remainder_ratio']*100:.1f}%)")
    
    # Final: max of both lanes
    final_volume = max(lane_a["total"], lane_b["total"])
    dominant = "Catalog" if lane_b["total"] >= lane_a["total"] else "Occupancy"
    
    # Apply minimum floor
    MIN_VOLUME = 0.5
    if final_volume < MIN_VOLUME:
        vlog(f"   ⚠️ Volume below minimum, applying floor: {MIN_VOLUME} yd³")
        final_volume = MIN_VOLUME
    
    # Calculate coverage metrics
    items_with_masks = sum(1 for i in fused_items if i.get("has_mask", False))
    mask_coverage_pct = (items_with_masks / len(fused_items) * 100) if fused_items else 0
    
    result = {
        "lane_a_occupancy": lane_a["total"],
        "lane_b_catalog": lane_b["total"],
        "final_volume": round(final_volume, 2),
        "dominant": dominant,
        "item_count": len(fused_items),
        "items_with_masks": items_with_masks,
        "mask_coverage_pct": round(mask_coverage_pct, 1),
        "remainder_ratio": lane_a["remainder_ratio"],
        "lane_a_details": lane_a,
        "lane_b_details": lane_b
    }
    
    vlog(f"   📦 Final: {result['final_volume']} yd³ (dominant={dominant})")
    
    return result


def compute_pricing(volume: float) -> dict:
    """
    Compute pricing based on volume tier.
    
    Args:
        volume: Final volume in cubic yards
        
    Returns:
        Pricing dict with tier, base price, range
    """
    # Find applicable tier
    tier = PRICING_TIERS[-1]  # Default to highest
    for t in PRICING_TIERS:
        if volume <= t["max_vol"]:
            tier = t
            break
    
    base_price = tier["base_price"]
    
    # Calculate range (base to base + 20%)
    low_price = base_price
    high_price = int(base_price * 1.2)
    
    return {
        "tier": tier["name"],
        "base_price": base_price,
        "low_price": low_price,
        "high_price": high_price,
        "volume": round(volume, 2)
    }
