"""
v4.0 Volume Engine (Step 10)

Three-estimator ensemble for robust volume computation:
- V_bulk: Bulk volume from pile coverage with dynamic K
- V_catalog: Discrete items + quantified countables with weighted subtraction
- V_occ: Remainder-based occupancy volume
"""

from typing import List
from .constants import (
    CATALOG_VOLUMES, 
    DEFAULT_VOLUME,
    PILE_LABELS,
    PRICING_TIERS
)
from .utils import vlog


# ==============================================================================
# PILE CONSTITUENT CLASSIFICATION
# ==============================================================================

# Items that are "pile constituents" - low subtraction weight
PILE_CONSTITUENTS = {
    # Soft bulk
    "bags", "trash bag", "garbage bag", "clothing",
    # Fragment bulk
    "cardboard", "boxes", "paper", "debris",
    # Stack bulk  
    "bins", "totes", "plastic storage tote",
    # Yard bulk
    "branches", "leaves", "yard waste", "brush"
}

# Truly discrete items - high subtraction weight
DISCRETE_ITEMS = {
    "couch", "sofa", "mattress", "refrigerator", "freezer",
    "washer", "dryer", "tv", "piano", "pool table", "hot tub",
    "table", "desk", "dresser", "chair"
}

# Countable items - use quantity estimation
COUNTABLE_ITEMS = {
    "bags": 0.02,      # Typical mask area ratio per bag
    "boxes": 0.025,    # Typical mask area ratio per box
    "totes": 0.03,     # Typical mask area ratio per tote
    "tires": 0.015,    # Typical mask area ratio per tire
    "chairs": 0.04,    # Typical mask area ratio per chair
}


def get_subtraction_weight(label: str) -> float:
    """
    Get weighted subtraction factor for an item.
    Low (0.1-0.4) for pile constituents, high (0.8-1.0) for discrete.
    """
    label_lower = label.lower()
    
    if label_lower in PILE_CONSTITUENTS or any(p in label_lower for p in PILE_CONSTITUENTS):
        return 0.2  # Low subtraction - don't erase pile
    elif label_lower in DISCRETE_ITEMS or any(d in label_lower for d in DISCRETE_ITEMS):
        return 0.9  # High subtraction - truly discrete
    else:
        return 0.5  # Default moderate subtraction


def get_catalog_volume(canonical_label: str, size_bucket: str) -> float:
    """Look up volume from catalog."""
    key = (canonical_label.lower(), size_bucket.lower())
    return CATALOG_VOLUMES.get(key, DEFAULT_VOLUME)


# ==============================================================================
# V_BULK: Bulk Volume from Pile Coverage
# ==============================================================================

def compute_v_bulk(pile_ratio: float, avg_bbox_ratio: float) -> dict:
    """
    Compute V_bulk: Bulk volume from pile coverage.
    Uses dynamic K based on scene scale.
    
    Args:
        pile_ratio: Average pile mask coverage (0-1)
        avg_bbox_ratio: Average bbox size of detected items (scene scale signal)
        
    Returns:
        Dict with bulk volume estimate
    """
    # Dynamic K based on scene scale
    # Smaller avg bbox = camera is farther = larger scene = higher K
    if avg_bbox_ratio < 0.02:
        K = 15  # Far shot, large scene
    elif avg_bbox_ratio < 0.05:
        K = 12  # Medium distance
    else:
        K = 8   # Close-up, small scene
    
    # V_bulk = pile_ratio * K
    v_bulk = pile_ratio * K
    
    return {
        "total": round(v_bulk, 2),
        "pile_ratio": pile_ratio,
        "K": K,
        "scene_scale": "far" if avg_bbox_ratio < 0.02 else ("medium" if avg_bbox_ratio < 0.05 else "close")
    }


# ==============================================================================
# V_CATALOG: Discrete Items + Quantified Countables
# ==============================================================================

def compute_v_catalog(fused_items: List[dict]) -> dict:
    """
    Compute V_catalog: Catalog volume from discrete items.
    Applies category-specific volumes.
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


# ==============================================================================
# V_OCC: Remainder-Based Occupancy
# ==============================================================================

def compute_v_occ(remainder_stats: dict, fused_items: List[dict]) -> dict:
    """
    Compute V_occ: Occupancy from remainder with weighted subtraction.
    Pile constituents have low subtraction weight.
    """
    avg_pile_ratio = remainder_stats.get("avg_pile_ratio", 0)
    
    # Weighted subtraction for items
    weighted_item_coverage = 0.0
    for item in fused_items:
        label = item.get("canonical_label", "")
        area_ratio = item.get("mask_area_ratio", 0)
        weight = get_subtraction_weight(label)
        weighted_item_coverage += area_ratio * weight
    
    # Effective remainder with weighted subtraction
    effective_remainder = max(0, avg_pile_ratio - weighted_item_coverage)
    
    # Scene priors
    VISIBLE_SQFT_PER_IMAGE = 50
    FILL_FACTOR = 0.55
    
    # Dynamic height based on pile size
    if avg_pile_ratio > 0.40:
        HEIGHT_PRIOR_FT = 3.5
    elif avg_pile_ratio > 0.25:
        HEIGHT_PRIOR_FT = 3.0
    else:
        HEIGHT_PRIOR_FT = 2.5
    
    # Calculate volume
    covered_sqft = effective_remainder * VISIBLE_SQFT_PER_IMAGE
    cubic_feet = covered_sqft * HEIGHT_PRIOR_FT * FILL_FACTOR
    cubic_yards = cubic_feet / 27
    
    return {
        "total": round(cubic_yards, 2),
        "pile_ratio": avg_pile_ratio,
        "weighted_item_coverage": round(weighted_item_coverage, 4),
        "effective_remainder": round(effective_remainder, 4),
        "height_prior": HEIGHT_PRIOR_FT
    }


# ==============================================================================
# ENSEMBLE: Intelligent Combination
# ==============================================================================

def compute_three_lane_volume(
    fused_items: List[dict],
    remainder_stats: dict,
    pile_masks: dict = None
) -> dict:
    """
    Three-estimator ensemble for robust volume computation.
    
    Intelligently combines:
    - V_bulk: Pile coverage-based (good for messy piles)
    - V_catalog: Discrete items (good for distinct items)
    - V_occ: Weighted remainder (balanced approach)
    """
    vlog(f"📊 Computing three-estimator volume...")
    
    # Get scene signals
    avg_pile_ratio = remainder_stats.get("avg_pile_ratio", 0)
    avg_items_ratio = remainder_stats.get("avg_items_ratio", 0)
    
    # Calculate average bbox ratio for scene scale
    avg_bbox_ratio = 0.03  # Default
    if fused_items:
        bbox_ratios = [i.get("mask_area_ratio", 0.03) for i in fused_items]
        avg_bbox_ratio = sum(bbox_ratios) / len(bbox_ratios)
    
    # Check for pile-like labels in items
    has_pile_labels = any(
        i.get("raw_label", "").lower() in PILE_LABELS or 
        i.get("canonical_label", "").lower() in PILE_LABELS
        for i in fused_items
    )
    
    # Compute all three estimates
    v_bulk = compute_v_bulk(avg_pile_ratio, avg_bbox_ratio)
    v_catalog = compute_v_catalog(fused_items)
    v_occ = compute_v_occ(remainder_stats, fused_items)
    
    vlog(f"   V_bulk: {v_bulk['total']} yd³ (K={v_bulk['K']}, pile={avg_pile_ratio*100:.1f}%)")
    vlog(f"   V_catalog: {v_catalog['total']} yd³ ({v_catalog['count']} items)")
    vlog(f"   V_occ: {v_occ['total']} yd³ (remainder={v_occ['effective_remainder']*100:.1f}%)")
    
    # Calculate constituent share (what fraction of Lane B is pile-internal items)
    constituent_volume = 0.0
    discrete_volume = 0.0
    for item in v_catalog["items"]:
        label = item.get("label", "")
        vol = item.get("volume", 0)
        if label.lower() in PILE_CONSTITUENTS or any(p in label.lower() for p in PILE_CONSTITUENTS):
            constituent_volume += vol
        else:
            discrete_volume += vol
    
    total_catalog = v_catalog["total"]
    constituent_share = constituent_volume / total_catalog if total_catalog > 0 else 0
    
    vlog(f"   Constituent: {constituent_volume:.2f} yd³ ({constituent_share*100:.0f}% of catalog)")
    
    # Scene signals for arbitration
    pile_is_strong = avg_pile_ratio > 0.20
    high_constituent = constituent_share > 0.50
    discrete_is_clear = len(fused_items) >= 5 and discrete_volume > 1.5
    
    # Conditional arbitration
    if pile_is_strong and high_constituent:
        # Pile dominates, Lane B is mostly pile-internal → prefer Lane A + discrete only
        # Downweight Lane B (only count discrete items at full value)
        lane_b_adjusted = discrete_volume + (constituent_volume * 0.3)  # 30% of constituents
        final_volume = max(v_bulk["total"], lane_b_adjusted)
        # Add remainder adjustment
        remainder_adjust = min(v_occ["total"] * 0.4, 1.5)
        final_volume += remainder_adjust
        dominant = "Bulk+Discrete"
        vlog(f"   📦 Pile-dominant: bulk vs adjusted_catalog ({lane_b_adjusted:.2f}) + remainder")
    
    elif pile_is_strong:
        # Pile is strong but items are mostly discrete → trust higher of bulk vs catalog
        final_volume = max(v_bulk["total"], v_catalog["total"])
        remainder_adjust = min(v_occ["total"] * 0.3, 1.0)
        final_volume += remainder_adjust
        dominant = "Bulk+Catalog"
        vlog(f"   📦 Pile mode: max(bulk,catalog) + remainder_adj")
    
    elif discrete_is_clear:
        # Clear discrete items, low pile → trust catalog
        final_volume = v_catalog["total"]
        dominant = "Catalog"
        vlog(f"   📦 Discrete mode: catalog only")
    
    else:
        # Sparse/unclear → take max of all three
        final_volume = max(v_bulk["total"], v_catalog["total"], v_occ["total"])
        dominant = "Ensemble-Max"
        vlog(f"   📦 Sparse mode: max of all three")
    
    # Apply minimum floor
    MIN_VOLUME = 0.5
    if final_volume < MIN_VOLUME:
        vlog(f"   ⚠️ Below minimum, applying floor: {MIN_VOLUME} yd³")
        final_volume = MIN_VOLUME
    
    # Coverage metrics
    items_with_masks = sum(1 for i in fused_items if i.get("has_mask", False))
    mask_coverage_pct = (items_with_masks / len(fused_items) * 100) if fused_items else 0
    
    result = {
        "v_bulk": v_bulk["total"],
        "v_catalog": v_catalog["total"],
        "v_occ": v_occ["total"],
        "lane_a_occupancy": v_occ["total"],  # Backward compat
        "lane_b_catalog": v_catalog["total"],  # Backward compat
        "final_volume": round(final_volume, 2),
        "dominant": dominant,
        "pile_is_strong": pile_is_strong,
        "item_count": len(fused_items),
        "items_with_masks": items_with_masks,
        "mask_coverage_pct": round(mask_coverage_pct, 1),
        "remainder_ratio": v_occ["effective_remainder"],
        "scene_scale": v_bulk["scene_scale"],
        "v_bulk_details": v_bulk,
        "v_catalog_details": v_catalog,
        "v_occ_details": v_occ
    }
    
    vlog(f"   📦 Final: {result['final_volume']} yd³ (dominant={dominant})")
    
    return result


# Alias for backward compatibility
def compute_two_lane_volume(fused_items: List[dict], remainder_stats: dict) -> dict:
    """Backward-compatible wrapper for compute_three_lane_volume."""
    return compute_three_lane_volume(fused_items, remainder_stats)


def compute_pricing(volume: float) -> dict:
    """Compute pricing based on volume tier."""
    tier = PRICING_TIERS[-1]
    for t in PRICING_TIERS:
        if volume <= t["max_vol"]:
            tier = t
            break
    
    base_price = tier["base_price"]
    low_price = base_price
    high_price = int(base_price * 1.2)
    
    return {
        "tier": tier["name"],
        "base_price": base_price,
        "low_price": low_price,
        "high_price": high_price,
        "volume": round(volume, 2)
    }
