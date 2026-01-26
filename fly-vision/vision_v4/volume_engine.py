"""
v4.0 Volume Engine (Step 10) - REWRITE

Lane A = Bulk baseline from pile coverage (not remainder)
Lane B = Discrete big items + Countable bulk quantities

Key changes:
- Use median(pile_ratio) * K for bulk baseline
- Count quantities for boxes/bags/totes instead of fusing to 2 items
- No double-counting: bulk-first policy
"""

from typing import List
from statistics import median
from .constants import (
    CATALOG_VOLUMES, 
    DEFAULT_VOLUME,
    PRICING_TIERS
)
from .utils import vlog


# ==============================================================================
# CONSTANTS
# ==============================================================================

# Bulk multiplier and cap
K_BULK = 12       # pile_ratio * K_BULK = bulk volume
K_MAX = 10        # Max bulk volume per image (prevents outliers)

# Quantity caps for countable bulk
QTY_CAP = {
    "boxes": 30,
    "bags": 25,
    "totes": 12,
    "tires": 20,
}

# Discrete big items (counted individually via catalog)
DISCRETE_ITEMS = {
    "couch", "sofa", "mattress", "refrigerator", "freezer",
    "washer", "dryer", "tv", "piano", "pool table", "hot tub",
    "table", "desk", "dresser", "chair", "speaker", "subwoofer",
    "exercise equipment", "treadmill", "scooter", "motorcycle"
}

# Countable bulk items (counted by quantity estimation)
COUNTABLE_BULK = {
    "bags", "boxes", "totes", "tires"
}

# Typical mask area ratio per item (for quantity estimation)
TYPICAL_MASK_AREA = {
    "boxes": 0.025,
    "bags": 0.02,
    "totes": 0.03,
    "tires": 0.015,
}


# ==============================================================================
# LANE A: BULK BASELINE FROM PILE COVERAGE
# ==============================================================================

def compute_lane_a_bulk(pile_masks: dict) -> dict:
    """
    Lane A = Bulk baseline from pile coverage using MEDIAN.
    
    Formula: median(clamp(pile_ratio_i * K, 0, K_max))
    
    This is NOT remainder-based. It's direct pile coverage → volume.
    """
    if not pile_masks:
        return {"total": 0.0, "pile_ratios": [], "per_image": {}}
    
    per_image_bulk = {}
    pile_ratios = []
    
    for image_id, pile_result in pile_masks.items():
        pile_ratio = pile_result.get("pile_area_ratio", 0)
        pile_ratios.append(pile_ratio)
        
        # Compute bulk volume for this image
        bulk_yd = min(pile_ratio * K_BULK, K_MAX)  # Clamp to K_max
        per_image_bulk[image_id] = {
            "pile_ratio": pile_ratio,
            "bulk_yd": round(bulk_yd, 2)
        }
    
    # Use MEDIAN across images (beats outliers)
    median_pile_ratio = median(pile_ratios) if pile_ratios else 0
    bulk_volume = min(median_pile_ratio * K_BULK, K_MAX)
    
    return {
        "total": round(bulk_volume, 2),
        "median_pile_ratio": round(median_pile_ratio, 4),
        "pile_ratios": pile_ratios,
        "K": K_BULK,
        "K_max": K_MAX,
        "per_image": per_image_bulk
    }


# ==============================================================================
# LANE B: DISCRETE ITEMS + COUNTABLE BULK QUANTITIES
# ==============================================================================

def get_catalog_volume(canonical_label: str, size_bucket: str) -> float:
    """Look up volume from catalog."""
    key = (canonical_label.lower(), size_bucket.lower())
    return CATALOG_VOLUMES.get(key, DEFAULT_VOLUME)


def compute_discrete_items_volume(fused_items: List[dict]) -> dict:
    """
    Compute volume for truly discrete big items.
    Uses catalog lookup, no quantity estimation.
    """
    total_volume = 0.0
    items = []
    
    for item in fused_items:
        label = item.get("canonical_label", "unknown").lower()
        
        # Only count discrete items here
        if label not in DISCRETE_ITEMS and not any(d in label for d in DISCRETE_ITEMS):
            continue
        
        size = item.get("size_bucket", "medium")
        vol = get_catalog_volume(label, size)
        
        # Apply category multipliers
        category = item.get("category", "furniture")
        if category == "appliance":
            vol *= 1.15
        elif category == "hazmat":
            vol *= 1.25
        
        total_volume += vol
        items.append({
            "label": label,
            "size": size,
            "volume": round(vol, 2)
        })
    
    return {
        "total": round(total_volume, 2),
        "items": items,
        "count": len(items)
    }


def compute_countable_bulk_volume(fused_items: List[dict]) -> dict:
    """
    Compute volume for countable bulk items using STABLE QUANTITY ESTIMATION.
    
    Stability fixes:
    1. Freeze vol_per to "medium" (deterministic)
    2. Cap qty to 3×detected+4 (prevents explosion)
    3. Use median per-view estimation with floor of 1
    """
    from statistics import median as stat_median
    
    # Group items by countable class AND by image
    class_areas_by_image = {cls: {} for cls in COUNTABLE_BULK}
    
    for item in fused_items:
        label = item.get("canonical_label", "unknown").lower()
        area_ratio = item.get("mask_area_ratio", 0)
        image_id = item.get("image_id", "unknown")
        
        for cls in COUNTABLE_BULK:
            if cls in label or label == cls:
                if image_id not in class_areas_by_image[cls]:
                    class_areas_by_image[cls][image_id] = []
                class_areas_by_image[cls][image_id].append(area_ratio)
                break
    
    # Estimate quantities and volumes
    quantities = {}
    volumes = {}
    details = []
    
    for cls, areas_by_image in class_areas_by_image.items():
        if not areas_by_image:
            continue
        
        typical_area = TYPICAL_MASK_AREA.get(cls, 0.025)
        
        # FIX 3: Compute qty per view, then take MEDIAN
        per_view_qty = []
        total_detected = 0
        
        for image_id, areas in areas_by_image.items():
            view_area = sum(areas)
            view_qty = view_area / typical_area if typical_area > 0 else len(areas)
            per_view_qty.append(max(1, view_qty))  # Floor of 1 per view
            total_detected += len(areas)
        
        # Use median across views (not sum)
        raw_qty = stat_median(per_view_qty) if per_view_qty else 1
        
        # FIX 2: Cap to 3×detected+4 (conservative)
        detected_cap = total_detected * 3 + 4
        qty = max(1, min(round(raw_qty), QTY_CAP.get(cls, 20), detected_cap))
        
        # Ensure at least detected count
        qty = max(qty, min(total_detected, detected_cap))
        
        # FIX 1: Freeze vol_per to "medium" (deterministic)
        vol_per = get_catalog_volume(cls, "medium")
        total_vol = qty * vol_per
        
        quantities[cls] = qty
        volumes[cls] = round(total_vol, 2)
        
        details.append({
            "class": cls,
            "detected_count": total_detected,
            "estimated_qty": qty,
            "per_view_qty": [round(q, 1) for q in per_view_qty],
            "detected_cap": detected_cap,
            "vol_per": vol_per,
            "total_volume": round(total_vol, 2)
        })
        
        vlog(f"   📦 {cls}: detected={total_detected}, qty={qty} (cap={detected_cap}), vol={total_vol:.2f} yd³")
    
    total_volume = sum(volumes.values())
    
    return {
        "total": round(total_volume, 2),
        "quantities": quantities,
        "volumes": volumes,
        "details": details
    }


def compute_lane_b(fused_items: List[dict]) -> dict:
    """
    Lane B = Discrete big items + Countable bulk quantities.
    """
    discrete = compute_discrete_items_volume(fused_items)
    countable = compute_countable_bulk_volume(fused_items)
    
    total = discrete["total"] + countable["total"]
    
    return {
        "total": round(total, 2),
        "discrete_total": discrete["total"],
        "countable_total": countable["total"],
        "discrete_items": discrete["items"],
        "discrete_count": discrete["count"],
        "countable_details": countable["details"],
        "quantities": countable["quantities"]
    }


# ==============================================================================
# FINAL ARBITRATION
# ==============================================================================

def compute_volume(
    fused_items: List[dict],
    pile_masks: dict,
    remainder_stats: dict = None
) -> dict:
    """
    Final volume computation with proper arbitration.
    
    If pile exists (median_pile_ratio >= 0.18):
        final = laneA_bulk + discrete_items + min(countable, laneA_bulk * 0.6)
    Else:
        final = discrete_items + countable (pure catalog mode)
    """
    vlog(f"📊 Computing volume (bulk-first policy)...")
    
    # Lane A: Bulk baseline from pile coverage
    lane_a = compute_lane_a_bulk(pile_masks)
    vlog(f"   Lane A (Bulk): {lane_a['total']} yd³ (median_pile={lane_a['median_pile_ratio']*100:.1f}%, K={K_BULK})")
    
    # Lane B: Discrete + Countable
    lane_b = compute_lane_b(fused_items)
    vlog(f"   Lane B (Discrete): {lane_b['discrete_total']} yd³ ({lane_b['discrete_count']} items)")
    vlog(f"   Lane B (Countable): {lane_b['countable_total']} yd³")
    
    # Arbitration
    pile_exists = lane_a["median_pile_ratio"] >= 0.18
    
    if pile_exists:
        # Pile mode: bulk + discrete + capped countable
        countable_cap = lane_a["total"] * 0.6
        countable_contribution = min(lane_b["countable_total"], countable_cap)
        
        final_volume = lane_a["total"] + lane_b["discrete_total"] + countable_contribution
        dominant = "Bulk+Hybrid"
        
        vlog(f"   📦 Pile mode: bulk({lane_a['total']}) + discrete({lane_b['discrete_total']}) + countable_capped({countable_contribution:.2f})")
    else:
        # Catalog mode: discrete + countable
        final_volume = lane_b["discrete_total"] + lane_b["countable_total"]
        dominant = "Catalog"
        countable_contribution = lane_b["countable_total"]
        
        vlog(f"   📦 Catalog mode: discrete + countable")
    
    # Apply minimum floor
    MIN_VOLUME = 0.5
    if final_volume < MIN_VOLUME:
        vlog(f"   ⚠️ Below minimum, applying floor: {MIN_VOLUME} yd³")
        final_volume = MIN_VOLUME
    
    # Coverage metrics
    items_with_masks = sum(1 for i in fused_items if i.get("has_mask", False))
    mask_coverage_pct = (items_with_masks / len(fused_items) * 100) if fused_items else 0
    
    result = {
        "final_volume": round(final_volume, 2),
        "dominant": dominant,
        "pile_exists": pile_exists,
        
        # Lane A details
        "lane_a_bulk": lane_a["total"],
        "lane_a_occupancy": lane_a["total"],  # Backward compat
        "median_pile_ratio": lane_a["median_pile_ratio"],
        
        # Lane B details
        "lane_b_catalog": lane_b["total"],  # Backward compat
        "lane_b_discrete": lane_b["discrete_total"],
        "lane_b_countable": lane_b["countable_total"],
        "countable_contribution": round(countable_contribution, 2),
        "quantities": lane_b["quantities"],
        
        # Metrics
        "item_count": len(fused_items),
        "items_with_masks": items_with_masks,
        "mask_coverage_pct": round(mask_coverage_pct, 1),
        
        # Full details
        "lane_a_details": lane_a,
        "lane_b_details": lane_b
    }
    
    vlog(f"   📦 Final: {result['final_volume']} yd³ (dominant={dominant})")
    
    return result


# Backward-compatible aliases
def compute_two_lane_volume(fused_items: List[dict], remainder_stats: dict) -> dict:
    """Backward-compatible wrapper."""
    # Extract pile_masks from remainder_stats if available
    pile_masks = remainder_stats.get("per_image", {})
    if not pile_masks:
        # Fake pile_masks from remainder_stats
        pile_masks = {"img_0": {"pile_area_ratio": remainder_stats.get("avg_pile_ratio", 0)}}
    return compute_volume(fused_items, pile_masks, remainder_stats)


def compute_three_lane_volume(fused_items: List[dict], remainder_stats: dict, pile_masks: dict = None) -> dict:
    """Backward-compatible wrapper."""
    if pile_masks is None:
        pile_masks = remainder_stats.get("per_image", {})
    return compute_volume(fused_items, pile_masks, remainder_stats)


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
