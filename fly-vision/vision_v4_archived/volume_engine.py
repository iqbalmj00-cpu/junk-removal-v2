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
    PRICING_TIERS,
    # P0.3 + P1: Bulky discrete lane
    BULKY_DISCRETE_CLASSES,
    BULKY_DISCRETE_VOLUMES,
    BULKY_MASK_PILE_RATIO,
    BULKY_BBOX_PILE_RATIO,
    BULKY_GATE_REMAINDER_MIN,
    BULKY_GATE_FALLBACK_RATE_MIN,
    # Fix 1: Countable exclusion
    COUNTABLE_CLASSES,
    # Fix 2: Best-view estimator
    BEST_VIEW_SPREAD_MIN,
    BEST_VIEW_MAX_PILE_CAP,
    BEST_VIEW_MIN_ITEMS_COV,
    # Ownership pipeline (Gap 1-4)
    AREA_LARGE,
    AREA_COUNTABLE_SUBTRACT,
    SUBTRACTION_MAX_RATIO,
    HEIGHT_FACTOR_MIN,
    VISION_QUALITY_FALLBACK_MAX,
)
from .ledger import VolumeLedger
from .utils import vlog
from .mask_ops import USE_UNION_MASKS, compute_subtracted_area_per_image


# ==============================================================================
# CONSTANTS
# ==============================================================================

# Bulk multiplier and cap
K_BULK = 12       # pile_ratio * K_BULK = bulk volume
K_MAX = 10        # Max bulk volume per image (prevents outliers)

# K-Scaling thresholds (gated adjustment)
K_SCALE_PILE_MIN = 0.30     # Pile ratio must be >= 30%
K_SCALE_ITEMS_MAX = 0.25    # Items coverage must be <= 25% (loosened to catch bbox fallback cases)
K_SCALE_REMAINDER_MIN = 0.12 # Remainder must be >= 12%
K_SCALE_MIN = 0.92          # Min scale factor
K_SCALE_MAX = 1.08          # Max scale factor

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
# OWNERSHIP PIPELINE (Steps 1-3 + Change D)
# ==============================================================================

def compute_ownership_and_subtraction(
    fused_items: List[dict], 
    pile_area: float,
    K: float = K_BULK,
    fallback_rate: float = 0.0,  # P2: Vision quality gate
    pile_masks: dict = None  # Change D: For union mask subtraction
) -> dict:
    """
    Step 1-3: Compute accounted_volume_final and enforce pixel ownership.
    
    P0: Countables are exempt from Policy A (owned_by_countable_pool)
    P1: Policy A reassigns volume, doesn't add (subtracts from bulk)
    P2: Vision quality gate (raises threshold when fallback > 0.40)
    Change D: Union mask subtraction (per-image, not percentage sum)
    
    Returns dict with ownership results for ledger.
    """
    subtraction_area = 0.0
    uncertain_blob_volume = 0.0
    uncertain_blob_count = 0
    countable_subtracted = 0.0
    overlap_risk_volume = 0.0  # Change C: Track non-subtracted items with real volume
    per_image_residual = {}  # Change D: Per-image residual tracking
    
    for item in fused_items:
        label = item.get("canonical_label", item.get("raw_label", "unknown")).lower()
        area = item.get("mask_area_ratio", item.get("bbox_area_ratio", 0))
        has_mask = item.get("has_mask", False)
        
        # Get volume from catalog/countable
        catalog_vol = item.get("catalog_volume", 0)
        countable_vol = item.get("countable_volume_credited", 0)
        
        # Compute accounted_volume_final (AFTER all caps)
        accounted = catalog_vol + countable_vol
        item["accounted_volume_final"] = accounted
        
        # Determine lane
        is_discrete = label in DISCRETE_ITEMS or catalog_vol > 0
        is_countable = any(c in label for c in COUNTABLE_BULK)
        
        # Change E: Every item MUST have an explicit owner_lane
        if is_countable:
            item["owner_lane"] = "COUNTABLE"
            item["owned_by_countable_pool"] = True
        elif is_discrete:
            item["owner_lane"] = "DISCRETE"
        else:
            item["owner_lane"] = None  # Candidate for Policy A
        
        # PIXEL OWNERSHIP RULE - Mark items for subtraction
        # Change D: Actual subtraction computed below via union masks
        if accounted > 0:
            if is_discrete:
                if area >= AREA_LARGE:
                    item["ownership"] = "DISCRETE_SUBTRACTED"
                    item["should_subtract_pixels"] = True
                else:
                    item["ownership"] = "DISCRETE_NOT_SUBTRACTED"
                    item["should_subtract_pixels"] = False
                    overlap_risk_volume += accounted
                    vlog(f"   ⚠️ Overlap risk: {label} vol={accounted:.2f} yd³ (area={area:.2%} too small to subtract)")
            
            elif is_countable:
                if area >= AREA_COUNTABLE_SUBTRACT:
                    item["ownership"] = "COUNTABLE_SUBTRACTED"
                    item["should_subtract_pixels"] = True
                    countable_subtracted += area  # Track for reporting
                else:
                    item["ownership"] = "COUNTABLE_NOT_SUBTRACTED"
                    item["should_subtract_pixels"] = False
                    overlap_risk_volume += accounted
        
        elif is_countable:
            item["ownership"] = "COUNTABLE_POOL_OWNED"
            item["should_subtract_pixels"] = area >= AREA_COUNTABLE_SUBTRACT
            if item["should_subtract_pixels"]:
                countable_subtracted += area
        
        else:
            # Candidate for Policy A
            policy_a_threshold = AREA_LARGE
            if fallback_rate > VISION_QUALITY_FALLBACK_MAX:
                policy_a_threshold = 0.10
            
            if area >= policy_a_threshold and item["owner_lane"] is None:
                fallback_vol = area * K * HEIGHT_FACTOR_MIN
                item["accounted_volume_final"] = fallback_vol
                item["uncertain_blob"] = True
                item["ownership"] = "UNCERTAIN_BLOB"
                item["owner_lane"] = "UNCERTAIN_BLOB"
                item["should_subtract_pixels"] = True  # Change D: include in union
                uncertain_blob_volume += fallback_vol
                uncertain_blob_count += 1
                vlog(f"   ⚠️ Policy A: {label} area={area:.2%} → {fallback_vol:.2f} yd³")
            else:
                item["ownership"] = "BULK_OWNED"
                item["owner_lane"] = "BULK"
                item["should_subtract_pixels"] = False
    
    # Change D: Union mask subtraction (replaces percentage sum)
    if USE_UNION_MASKS and pile_masks:
        mask_cache = {}  # Request-scoped cache
        per_image_stats = compute_subtracted_area_per_image(
            fused_items, pile_masks, mask_cache
        )
        
        # Aggregate residuals across images (median for stability)
        residual_ratios = [
            stats["residual_ratio"] for stats in per_image_stats.values()
            if not stats.get("fallback", False)
        ]
        
        if residual_ratios:
            bulk_residual_pct = median(residual_ratios)
            subtraction_area = pile_area - bulk_residual_pct
            vlog(f"   📐 Union subtraction: median_residual={bulk_residual_pct:.1%} from {len(residual_ratios)} images")
        else:
            # Fallback to percentage-based if no masks available
            subtraction_area = sum(
                item.get("mask_area_ratio", item.get("bbox_area_ratio", 0)) * 0.4
                for item in fused_items if item.get("should_subtract_pixels")
            )
            vlog(f"   ⚠️ Union fallback: percentage-based subtraction={subtraction_area:.1%}")
        
        per_image_residual = per_image_stats
    else:
        # Legacy: percentage-based subtraction
        for item in fused_items:
            if item.get("should_subtract_pixels"):
                area = item.get("mask_area_ratio", item.get("bbox_area_ratio", 0))
                has_mask = item.get("has_mask", False)
                sub_area = area if has_mask else area * 0.4
                subtraction_area += sub_area
    
    # Clamp subtraction (safety net, should rarely trigger with union masks)
    max_subtraction = pile_area * SUBTRACTION_MAX_RATIO
    if subtraction_area > max_subtraction:
        vlog(f"   ⚠️ Subtraction clamped: {subtraction_area:.2%} → {max_subtraction:.2%}")
        subtraction_area = max_subtraction
    
    return {
        "items": fused_items,
        "subtraction_area": subtraction_area,
        "uncertain_blob_volume": uncertain_blob_volume,
        "uncertain_blob_count": uncertain_blob_count,
        "countable_subtracted": countable_subtracted,
        "overlap_risk_volume": overlap_risk_volume,
        "per_image_residual": per_image_residual  # Change D: For debugging
    }


# ==============================================================================
# ITEMIZED LOGGING (Debug each fused item)
# ==============================================================================

def log_itemized_breakdown(fused_items: List[dict], lane_b: dict) -> None:
    """
    Log detailed breakdown of each fused item for debugging variance.
    
    This is the key to understanding why discrete volume changes between runs.
    """
    import json
    
    vlog(f"   📋 Itemized breakdown ({len(fused_items)} fused items):")
    
    # Build lookup for discrete items that contributed volume
    discrete_labels = {item["label"] for item in lane_b.get("discrete_items", [])}
    countable_classes = set(lane_b.get("quantities", {}).keys())
    
    for item in fused_items:
        label = item.get("canonical_label", item.get("raw_label", "unknown")).lower()
        conf = item.get("classifier_confidence", item.get("score", 0))
        image_id = item.get("image_id", "?")[:8]
        mask_source = "seg" if item.get("has_mask") else "bbox"
        area = item.get("mask_area_ratio", 0)
        lane = item.get("lane", "unknown")
        lane_reason = item.get("lane_reason", "default")
        
        # Determine volume contribution
        if label in discrete_labels:
            vol_used = next((i["volume"] for i in lane_b["discrete_items"] if i["label"] == label), 0)
            vol_lane = "discrete"
        elif any(c in label for c in countable_classes):
            vol_used = 0  # Countable uses aggregate qty
            vol_lane = "countable"
        else:
            vol_used = 0
            vol_lane = "none"
        
        vlog(f"      • {label}: {vol_used}yd³ | conf={conf:.2f} | {mask_source} | area={area:.3f} | lane={lane} | src={image_id}")


# ==============================================================================
# K-SCALING HELPERS (Smooth, gated adjustment)
# ==============================================================================

def k_scale_from_coverage(median_pile_ratio: float) -> float:
    """
    Smoothly map pile_ratio in [0.20, 0.50] to scale in [0.92, 1.08].
    
    This provides a "nudgy" ±8% adjustment based on how much of the
    frame is covered by pile - higher coverage = scale up K slightly.
    """
    lo, hi = 0.20, 0.50
    x = (median_pile_ratio - lo) / (hi - lo)
    x = max(0.0, min(1.0, x))
    return K_SCALE_MIN + (K_SCALE_MAX - K_SCALE_MIN) * x  # 0.92 → 1.08


def should_adjust_k(
    median_pile_ratio: float, 
    median_items_cov: float, 
    remainder: float
) -> bool:
    """
    Gate K-scaling to only trigger when ALL signals indicate "missing mass":
    
    1. Pile coverage is high (>= 30%) - lots of stuff in frame
    2. Item coverage is low (<= 18%) - segmentation didn't explain it
    3. Remainder is high (>= 12%) - significant unexplained area
    
    This pattern screams: "Pile mask sees a lot, but items didn't cover it."
    Test 1 should NOT trigger this (items explained the coverage).
    """
    return (
        median_pile_ratio >= K_SCALE_PILE_MIN and
        median_items_cov <= K_SCALE_ITEMS_MAX and
        remainder >= K_SCALE_REMAINDER_MIN
    )


# ==============================================================================
# P1: BULKY DISCRETE SAFETY NET (Gated fallback for dead-zone)
# ==============================================================================

def is_bulky_discrete_candidate(item: dict, median_pile_ratio: float) -> bool:
    """
    P1.2: Check if an item is a bulky discrete candidate.
    
    Uses PILE-RELATIVE geometry (not frame-relative!) to be camera-distance invariant.
    
    An item is a candidate if:
    - NOT a countable class (bags/boxes/totes), AND
    - (Category matches BULKY_DISCRETE_CLASSES, OR geometry match)
    """
    if median_pile_ratio <= 0:
        return False
    
    # Normalize label (strip, lower, handle synonyms)
    raw_label = item.get("canonical_label", item.get("raw_label", ""))
    label = raw_label.strip().lower().replace("trashbag", "trash bag")
    
    # Fix 1: Never consider countables as bulky candidates
    if label in COUNTABLE_CLASSES:
        return False
    
    mask_ratio = item.get("mask_area_ratio", 0)
    bbox_ratio = item.get("bbox_area_ratio", mask_ratio)  # fallback to mask
    
    # Pile-relative ratios
    pile_relative_mask = mask_ratio / median_pile_ratio if median_pile_ratio > 0 else 0
    pile_relative_bbox = bbox_ratio / median_pile_ratio if median_pile_ratio > 0 else 0
    
    # Category match
    category_match = label in BULKY_DISCRETE_CLASSES
    
    # Geometry match (pile-relative)
    geometry_match = (
        pile_relative_mask >= BULKY_MASK_PILE_RATIO or 
        pile_relative_bbox >= BULKY_BBOX_PILE_RATIO
    )
    
    return category_match or geometry_match


def should_apply_bulky_lane(
    bulky_count: int,
    remainder: float,
    fallback_rate: float,
    countable_was_capped: bool
) -> bool:
    """
    P1.3: Multi-signal gate for applying bulky lane.
    
    Only triggers when ALL signals indicate "missing mass":
    1. At least 1 bulky candidate detected
    2. High remainder (>= 10%) - unexplained pile area
    3. EITHER high bbox fallback rate (>= 40%) OR countables were capped
    
    This protects Test 1 (already-correct cases).
    """
    return (
        bulky_count >= 1 and
        remainder >= BULKY_GATE_REMAINDER_MIN and
        (fallback_rate >= BULKY_GATE_FALLBACK_RATE_MIN or countable_was_capped)
    )


def compute_bulky_discrete_volume(candidates: List[dict]) -> tuple:
    """
    P1.4: Apply bulky priors when catalog returns 0.
    
    Returns: (total_volume, priors_applied_set)
    """
    total = 0.0
    priors_applied = set()
    details = []
    
    for item in candidates:
        label = item.get("canonical_label", item.get("raw_label", "")).lower()
        size_bucket = item.get("size_bucket", "medium")
        
        # Check if catalog already gives volume
        catalog_vol = CATALOG_VOLUMES.get((label, size_bucket), 0)
        if catalog_vol == 0:
            catalog_vol = CATALOG_VOLUMES.get((label, "medium"), 0)
        
        if catalog_vol > 0:
            # Catalog handles it - no bulky prior needed
            continue
        
        # Apply bulky prior if available
        if label in BULKY_DISCRETE_VOLUMES:
            prior_vol = BULKY_DISCRETE_VOLUMES[label]
            total += prior_vol
            priors_applied.add(label)
            details.append(f"{label}={prior_vol}")
            vlog(f"   📦 Bulky prior: {label} → {prior_vol} yd³")
    
    if priors_applied:
        vlog(f"   📊 Bulky lane total: {total:.2f} yd³ ({', '.join(details)})")
    
    return total, priors_applied


# ==============================================================================
# LANE A: BULK BASELINE FROM PILE COVERAGE (WITH SUBTRACTION)
# ==============================================================================

# Threshold for "large segmented discrete" items to subtract from pile
LARGE_DISCRETE_THRESHOLD = 0.05  # 5% of image


def compute_large_discrete_per_image(
    fused_items: List[dict],
    bulky_priors_applied: set = None
) -> dict:
    """
    Compute total area of large segmented discrete items per image.
    
    P0.3 CORE INVARIANT:
    Only subtract an item if item_volume_accounted == True.
    
    item_volume_accounted is True if:
    - Item has catalog volume, OR
    - Item gets bulky prior volume, OR  
    - Item is countable with credited volume
    
    This closes the "dead-zone" where items were subtracted but 0-volume.
    """
    if bulky_priors_applied is None:
        bulky_priors_applied = set()
    
    large_discrete_by_image = {}
    subtraction_log = []  # P3: Debug logging
    
    for item in fused_items:
        image_id = item.get("image_id", "unknown")
        lane = item.get("lane", "")
        has_mask = item.get("has_mask", False)
        area = item.get("mask_area_ratio", 0)
        label = item.get("canonical_label", item.get("raw_label", "")).strip().lower().replace("trashbag", "trash bag")
        size_bucket = item.get("size_bucket", "medium")
        
        # Skip non-discrete or too-small items
        if lane != "DISCRETE_ITEM" or not has_mask or area < LARGE_DISCRETE_THRESHOLD:
            continue
        
        # P0.3: Check if item_volume_accounted
        has_catalog_vol = (label, size_bucket) in CATALOG_VOLUMES or (label, "medium") in CATALOG_VOLUMES
        has_bulky_prior = label in bulky_priors_applied
        has_countable_credit = item.get("countable_volume_credited", 0) > 0
        
        item_volume_accounted = has_catalog_vol or has_bulky_prior or has_countable_credit
        
        if item_volume_accounted:
            # Safe to subtract - volume is accounted elsewhere
            if image_id not in large_discrete_by_image:
                large_discrete_by_image[image_id] = 0
            large_discrete_by_image[image_id] += area
            subtraction_log.append(f"{label}: YES (catalog={has_catalog_vol}, bulky={has_bulky_prior})")
        else:
            # DO NOT SUBTRACT - would create dead-zone
            subtraction_log.append(f"{label}: NO (not accounted, keeping in bulk)")
            vlog(f"   ⚠️ Not subtracting {label} (area={area*100:.1f}%) - no volume accounted")
    
    # Log subtraction decisions
    if subtraction_log:
        vlog(f"   📋 Subtraction decisions: {len([s for s in subtraction_log if 'YES' in s])}/{len(subtraction_log)} items subtracted")
    
    return large_discrete_by_image


def compute_lane_a_bulk(
    pile_masks: dict, 
    fused_items: List[dict] = None,
    median_items_coverage: float = 0.0,
    remainder: float = 0.0,
    bulky_priors_applied: set = None
) -> dict:
    """
    Lane A = Bulk baseline from RESIDUAL pile coverage using MEDIAN.
    
    Key changes:
    1. Subtract large segmented discrete items per-image to prevent double-counting
       P0.3: Only subtract items whose volume is accounted (catalog, bulky, countable)
    2. Apply K-scaling (±8%) when gated by multi-signal "missing mass" detection
    
    Formula: median(clamp(residual_ratio_i * K_effective, 0, K_max))
    where residual_ratio_i = pile_ratio_i - large_discrete_ratio_i
    """
    if not pile_masks:
        return {"total": 0.0, "pile_ratios": [], "residual_ratios": [], "per_image": {},
                "K_effective": K_BULK, "k_scaled": False}
    
    # Compute large discrete subtraction per image
    # P0.3: Pass bulky_priors_applied so we know which items are accounted
    large_discrete_by_image = compute_large_discrete_per_image(
        fused_items or [], 
        bulky_priors_applied or set()
    )
    
    per_image_bulk = {}
    pile_ratios = []
    residual_ratios = []
    
    for image_id, pile_result in pile_masks.items():
        pile_ratio = pile_result.get("pile_area_ratio", 0)
        pile_ratios.append(pile_ratio)
        
        # SUBTRACTION: Remove large discrete items from pile coverage
        large_discrete_ratio = large_discrete_by_image.get(image_id, 0)
        residual_ratio = max(0, pile_ratio - large_discrete_ratio)
        residual_ratios.append(residual_ratio)
        
        # Compute bulk volume from RESIDUAL (not raw pile) - using base K for per-image
        bulk_yd = min(residual_ratio * K_BULK, K_MAX)
        
        per_image_bulk[image_id] = {
            "pile_ratio": round(pile_ratio, 4),
            "large_discrete_ratio": round(large_discrete_ratio, 4),
            "residual_ratio": round(residual_ratio, 4),
            "bulk_yd": round(bulk_yd, 2)
        }
    
    # Use MEDIAN of RESIDUAL ratios (not raw pile)
    median_pile_ratio = median(pile_ratios) if pile_ratios else 0
    median_residual_ratio = median(residual_ratios) if residual_ratios else 0
    
    # Fix 2: Best-view residual estimator
    # When pile ratios have high spread, use top-2 mean instead of median
    max_pile_ratio = max(pile_ratios) if pile_ratios else 0
    max_residual_ratio = max(residual_ratios) if residual_ratios else 0
    spread = max_residual_ratio / median_residual_ratio if median_residual_ratio > 0 else 1
    
    # Gate conditions for best-view
    spread_ok = spread >= BEST_VIEW_SPREAD_MIN
    pile_cap_ok = max_pile_ratio <= BEST_VIEW_MAX_PILE_CAP
    # Note: item coverage check would need per-image data, simplified for now
    
    # P3: Mode lock - use STABLE criteria based on pile coverage consistency
    # If pile ratios are consistent (low CoV), median is reliable → don't use best-view
    # If pile ratios vary significantly (high CoV), best-view may help → use best-view
    pile_std = (sum((p - median_pile_ratio)**2 for p in pile_ratios) / len(pile_ratios))**0.5 if pile_ratios else 0
    pile_cov = pile_std / median_pile_ratio if median_pile_ratio > 0 else 0  # Coefficient of variation
    
    # P3: Lock mode based on consistency
    # High CoV (>0.25) = inconsistent views → use best-view
    # Low CoV (<=0.25) = consistent views → use median (more stable)
    PILE_COV_THRESHOLD = 0.25
    coverage_consistent = pile_cov <= PILE_COV_THRESHOLD
    
    # P3: Final mode selection - consistent coverage prefers median, inconsistent prefers best-view
    use_best_view = spread_ok and pile_cap_ok and len(residual_ratios) >= 2 and not coverage_consistent
    
    vlog(f"   📐 P3 mode lock: CoV={pile_cov:.2f}, consistent={coverage_consistent} → best_view={use_best_view}")
    
    if use_best_view:
        # Use top-2 mean (more stable than p75 for small N)
        res_sorted = sorted(residual_ratios)
        top2_mean = (res_sorted[-1] + res_sorted[-2]) / 2
        residual_for_bulk = top2_mean
        vlog(f"   📐 Best-view: spread={spread:.2f}, top2_mean={top2_mean*100:.1f}% (median was {median_residual_ratio*100:.1f}%)")
    else:
        residual_for_bulk = median_residual_ratio
        if spread >= BEST_VIEW_SPREAD_MIN and coverage_consistent:
            vlog(f"   📐 Best-view SKIPPED: spread={spread:.2f} OK, but coverage consistent (CoV={pile_cov:.2f})")
    
    # K-Scaling gate: only adjust when "missing mass" is detected
    # FIX #1: Use median_pile_ratio (not residual) for gating/scaling
    K_effective = K_BULK
    k_scaled = False
    if should_adjust_k(median_pile_ratio, median_items_coverage, remainder):
        K_effective = K_BULK * k_scale_from_coverage(median_pile_ratio)
        k_scaled = True
        vlog(f"   📈 K-scaling: {K_BULK} → {K_effective:.2f} (pile={median_pile_ratio*100:.0f}%, items={median_items_coverage*100:.0f}%, rem={remainder*100:.0f}%)")
    
    bulk_volume = min(residual_for_bulk * K_effective, K_MAX)
    
    # Log subtraction for debugging
    vlog(f"   📐 Subtraction: raw_pile={median_pile_ratio*100:.1f}% → residual={residual_for_bulk*100:.1f}% (best_view={use_best_view})")
    if large_discrete_by_image:
        for img_id, ratio in large_discrete_by_image.items():
            vlog(f"      - {img_id[:8]}: subtracted {ratio*100:.1f}% large discrete")
    
    return {
        "total": round(bulk_volume, 2),
        "median_pile_ratio": round(median_pile_ratio, 4),
        "median_residual_ratio": round(median_residual_ratio, 4),
        "residual_for_bulk": round(residual_for_bulk, 4),  # Actual value used in computation
        "use_best_view": use_best_view,
        "max_residual_ratio": round(max_residual_ratio, 4),
        "spread": round(spread, 2),
        "pile_ratios": pile_ratios,
        "residual_ratios": residual_ratios,
        "K": K_BULK,
        "K_effective": round(K_effective, 2),
        "k_scaled": k_scaled,
        "K_max": K_MAX,
        "per_image": per_image_bulk,
        "large_discrete_by_image": large_discrete_by_image
    }


# ==============================================================================
# LANE B: DISCRETE ITEMS + COUNTABLE BULK QUANTITIES
# ==============================================================================

# Pile-mode caps: Safety net for discrete items (prevents outlier blowups)
# Applied when pile_mode=True to limit contribution from bulky detections
PILE_MODE_DISCRETE_CAPS = {
    "exercise equipment": 1.0,  # Max 1.0 yd³ total (even if detected multiple times)
    "scooter": 0.5,
    "treadmill": 1.5,
    "motorcycle": 1.5,
}


def get_catalog_volume(canonical_label: str, size_bucket: str) -> float:
    """Look up volume from catalog."""
    key = (canonical_label.lower(), size_bucket.lower())
    return CATALOG_VOLUMES.get(key, DEFAULT_VOLUME)


def compute_discrete_items_volume(fused_items: List[dict], pile_mode: bool = False) -> dict:
    """
    Compute volume for truly discrete big items.
    Uses catalog lookup, no quantity estimation.
    
    When pile_mode=True, applies caps to prevent outlier blowups.
    """
    total_volume = 0.0
    items = []
    
    # Track volume per label for capping
    volume_per_label = {}
    
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
        
        # Track cumulative volume per label
        if label not in volume_per_label:
            volume_per_label[label] = 0
        
        # Apply pile-mode caps if enabled
        if pile_mode and label in PILE_MODE_DISCRETE_CAPS:
            cap = PILE_MODE_DISCRETE_CAPS[label]
            remaining_cap = cap - volume_per_label[label]
            
            if remaining_cap <= 0:
                vlog(f"      ⚠️ {label}: capped (already at {cap} yd³)")
                continue  # Skip this item, already at cap
            
            if vol > remaining_cap:
                vlog(f"      ⚠️ {label}: capped {vol:.2f} → {remaining_cap:.2f} yd³")
                vol = remaining_cap
        
        volume_per_label[label] += vol
        total_volume += vol
        items.append({
            "label": label,
            "size": size,
            "volume": round(vol, 2),
            "capped": pile_mode and label in PILE_MODE_DISCRETE_CAPS
        })
    
    return {
        "total": round(total_volume, 2),
        "items": items,
        "count": len(items),
        "volume_per_label": volume_per_label
    }


def compute_countable_bulk_volume(fused_items: List[dict], pile_coverage: float = 0.0) -> dict:
    """
    Compute volume for countable bulk items using STABLE QUANTITY ESTIMATION.
    
    Stability fixes:
    1. Freeze vol_per to "medium" (deterministic)
    2. Cap qty to 3×detected+4 (prevents explosion)
    3. Use median per-view estimation with floor of 1
    
    Phase 3 enhancements:
    4. Pile coverage cap (scale-free): countables can't claim > 50% of pile
    5. Evidence-gated expansion: qty > detected only if multi-view confirmed
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
    
    # Phase 3: Scale-free pile coverage cap
    # Countables should not claim more than 50% of pile area
    COUNTABLE_PILE_COVERAGE_MAX = 0.50
    total_countable_area = sum(
        sum(sum(areas) for areas in cls_data.values())
        for cls_data in class_areas_by_image.values()
    )
    
    for cls, areas_by_image in class_areas_by_image.items():
        if not areas_by_image:
            continue
        
        typical_area = TYPICAL_MASK_AREA.get(cls, 0.025)
        
        # FIX 3: Compute qty per view, then take MEDIAN
        per_view_qty = []
        total_detected = 0
        view_count = len(areas_by_image)
        
        for image_id, areas in areas_by_image.items():
            view_area = sum(areas)
            view_qty = view_area / typical_area if typical_area > 0 else len(areas)
            per_view_qty.append(max(1, view_qty))  # Floor of 1 per view
            total_detected += len(areas)
        
        # Use median across views (not sum)
        raw_qty = stat_median(per_view_qty) if per_view_qty else 1
        
        # Phase 3: Evidence-gated expansion
        # Only allow qty > detected if multi-view confirmed (seen in >= 2 views)
        multi_view_confirmed = view_count >= 2
        if not multi_view_confirmed and raw_qty > total_detected:
            raw_qty = total_detected  # Can't expand without multi-view
            vlog(f"   ⚠️ {cls}: qty clamped to detected (single view)")
        
        # FIX 2: Cap to 3×detected+4 (conservative)
        detected_cap = total_detected * 3 + 4
        
        # Phase 3: Pile coverage cap
        if pile_coverage > 0:
            # Max countables based on pile coverage (scale-free)
            cls_area = sum(sum(areas) for areas in areas_by_image.values())
            max_from_coverage = (pile_coverage * COUNTABLE_PILE_COVERAGE_MAX) / typical_area
            coverage_cap = int(max_from_coverage)
        else:
            coverage_cap = 9999  # No pile = no coverage cap
        
        qty = max(1, min(round(raw_qty), QTY_CAP.get(cls, 20), detected_cap, coverage_cap))
        
        # Ensure at least detected count
        qty = max(qty, min(total_detected, detected_cap))
        
        # Track if capping occurred (for bulky gate)
        was_capped = round(raw_qty) > qty
        
        # FIX 1: Freeze vol_per to "medium" (deterministic)
        vol_per = get_catalog_volume(cls, "medium")
        total_vol = qty * vol_per
        
        quantities[cls] = qty
        volumes[cls] = round(total_vol, 2)
        
        details.append({
            "class": cls,
            "detected_count": total_detected,
            "estimated_qty": qty,
            "raw_qty": round(raw_qty, 1),
            "per_view_qty": [round(q, 1) for q in per_view_qty],
            "detected_cap": detected_cap,
            "vol_per": vol_per,
            "total_volume": round(total_vol, 2),
            "capped": was_capped
        })
        
        vlog(f"   📦 {cls}: detected={total_detected}, qty={qty} (cap={detected_cap}), vol={total_vol:.2f} yd³")
    
    total_volume = sum(volumes.values())
    
    return {
        "total": round(total_volume, 2),
        "quantities": quantities,
        "volumes": volumes,
        "details": details
    }


def compute_lane_b(fused_items: List[dict], pile_mode: bool = False, pile_coverage: float = 0.0) -> dict:
    """
    Lane B = Discrete big items + Countable bulk quantities.
    
    When pile_mode=True, applies caps to prevent outlier blowups.
    pile_coverage is passed to countable for scale-free caps (Phase 3).
    """
    discrete = compute_discrete_items_volume(fused_items, pile_mode=pile_mode)
    countable = compute_countable_bulk_volume(fused_items, pile_coverage=pile_coverage)
    
    total = discrete["total"] + countable["total"]
    
    return {
        "total": round(total, 2),
        "discrete_total": discrete["total"],
        "countable_total": countable["total"],
        "discrete_items": discrete["items"],
        "discrete_count": discrete["count"],
        "countable_details": countable["details"],
        "quantities": countable["quantities"],
        "volume_per_label": discrete.get("volume_per_label", {})
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
    
    K-scaling is applied in Lane A when "missing mass" is detected:
    - High pile coverage + low item coverage + high remainder
    
    P1: Bulky lane is added when:
    - Bulky candidates detected AND remainder high AND (fallback high OR countable capped)
    """
    vlog(f"📊 Computing volume (bulk-first policy)...")
    
    # Extract K-scaling gate signals from remainder_stats
    # FIX #4: Remove broken fallback branch; use medians for stability
    if remainder_stats:
        median_items_cov = remainder_stats.get("median_items_ratio", 0)
        remainder = remainder_stats.get("median_remainder_ratio", 0)
    else:
        # No remainder_stats = can't gate properly, disable K-scaling
        median_items_cov = 0
        remainder = 0
    
    # P1: Detect bulky discrete candidates EARLY (before lane A)
    # Need median_pile_ratio from pile_masks first
    pile_ratios = [pm.get("pile_area_ratio", 0) for pm in pile_masks.values()]
    median_pile_ratio = median(pile_ratios) if pile_ratios else 0
    
    bulky_candidates = [
        item for item in fused_items 
        if is_bulky_discrete_candidate(item, median_pile_ratio)
    ]
    bulky_count = len(bulky_candidates)
    
    if bulky_candidates:
        vlog(f"   🏋️ Bulky candidates: {bulky_count} ({', '.join(set(c.get('canonical_label', '?') for c in bulky_candidates))})")
    
    # P1: Compute bulky volume (returns priors_applied for subtraction rule)
    bulky_volume, bulky_priors_applied = compute_bulky_discrete_volume(bulky_candidates)
    
    # Lane A: Bulk baseline from RESIDUAL pile coverage (after subtracting large discrete)
    # P0.3: Pass bulky_priors_applied so subtraction knows which items are accounted
    lane_a = compute_lane_a_bulk(pile_masks, fused_items, median_items_cov, remainder, bulky_priors_applied)
    k_info = f" [K={lane_a.get('K_effective', K_BULK)}, scaled={lane_a.get('k_scaled', False)}]" if lane_a.get('k_scaled') else ""
    vlog(f"   Lane A (Bulk): {lane_a['total']} yd³ (residual={lane_a.get('median_residual_ratio', 0)*100:.1f}%{k_info})")
    
    # Determine pile mode BEFORE computing lane B (for caps)
    pile_exists = lane_a["median_pile_ratio"] >= 0.18
    
    # Lane B: Discrete + Countable (with pile-mode caps if applicable)
    lane_b = compute_lane_b(fused_items, pile_mode=pile_exists, pile_coverage=median_pile_ratio)
    vlog(f"   Lane B (Discrete): {lane_b['discrete_total']} yd³ ({lane_b['discrete_count']} items)")
    vlog(f"   Lane B (Countable): {lane_b['countable_total']} yd³")
    
    # P1.3: Compute gate signals for bulky lane
    items_with_masks = sum(1 for i in fused_items if i.get("has_mask", False))
    fallback_rate = 1 - (items_with_masks / len(fused_items)) if fused_items else 0
    
    # P1.3: Check if countable was capped (cleaner signal than threshold)
    countable_details = lane_b.get("countable_details", {})
    countable_was_capped = any(d.get("capped", False) for d in countable_details) if countable_details else False
    
    # P1.3: Apply bulky lane gate
    apply_bulky = should_apply_bulky_lane(bulky_count, remainder, fallback_rate, countable_was_capped)
    bulky_contribution = bulky_volume if apply_bulky else 0
    
    if apply_bulky:
        vlog(f"   🚨 Bulky gate PASSED: count={bulky_count}, rem={remainder*100:.0f}%, fallback={fallback_rate*100:.0f}%, capped={countable_was_capped}")
    elif bulky_count > 0:
        vlog(f"   ✅ Bulky gate SKIPPED: count={bulky_count}, rem={remainder*100:.0f}%, fallback={fallback_rate*100:.0f}%, capped={countable_was_capped}")
    
    # Arbitration
    if pile_exists:
        # Pile mode: bulk + discrete + capped countable + bulky lane
        countable_cap = lane_a["total"] * 0.6
        countable_contribution = min(lane_b["countable_total"], countable_cap)
        
        final_volume = lane_a["total"] + lane_b["discrete_total"] + countable_contribution + bulky_contribution
        dominant = "Bulk+Hybrid"
        
        vlog(f"   📦 Pile mode: bulk({lane_a['total']}) + discrete({lane_b['discrete_total']}) + countable_capped({countable_contribution:.2f}) + bulky({bulky_contribution:.2f})")
    else:
        # Catalog mode: discrete + countable + bulky lane
        final_volume = lane_b["discrete_total"] + lane_b["countable_total"] + bulky_contribution
        dominant = "Catalog"
        countable_contribution = lane_b["countable_total"]
        
        vlog(f"   📦 Catalog mode: discrete + countable + bulky({bulky_contribution:.2f})")
    
    # Apply minimum floor
    MIN_VOLUME = 0.5
    if final_volume < MIN_VOLUME:
        vlog(f"   ⚠️ Below minimum, applying floor: {MIN_VOLUME} yd³")
        final_volume = MIN_VOLUME
    
    # Coverage metrics
    mask_coverage_pct = (items_with_masks / len(fused_items) * 100) if fused_items else 0
    
    # Step 1-3: Compute ownership and subtraction (AFTER all lanes)
    # Change D: Pass pile_masks for union-based subtraction
    ownership = compute_ownership_and_subtraction(
        fused_items, 
        pile_area=median_pile_ratio,
        K=lane_a.get("K_effective", K_BULK),
        fallback_rate=fallback_rate,  # P2: Pass vision quality signal
        pile_masks=pile_masks  # Change D: For union mask subtraction
    )
    
    # P1: Policy A does NOT add to final_volume
    # The blob volume is REASSIGNED from bulk (subtracted area), not added
    # uncertain_blob_volume is tracked separately in ledger for auditability
    if ownership["uncertain_blob_volume"] > 0:
        vlog(f"   📊 Policy A reassigned: {ownership['uncertain_blob_volume']:.2f} yd³ ({ownership['uncertain_blob_count']} uncertain blobs) — NOT additive")
    
    # Phase 1: Build Volume Ledger for formal accounting
    ledger = VolumeLedger(
        # Bulk lane
        bulk_raw=lane_a.get("residual_for_bulk", lane_a.get("median_residual_ratio", 0)) * lane_a.get("K_effective", K_BULK),
        bulk_subtracted=ownership["subtraction_area"] * lane_a.get("K_effective", K_BULK),
        bulk_residual=lane_a["total"],
        
        # Discrete lane
        discrete_volume=lane_b["discrete_total"],
        discrete_items=[f"{d['label']}:{d['volume']}" for d in lane_b.get("discrete_details", [])],
        
        # Countable lane
        countable_volume=lane_b["countable_total"],
        countable_classes=lane_b.get("quantities", {}),
        countable_subtracted=ownership["countable_subtracted"],
        
        # Bulky priors
        bulky_prior_volume=bulky_contribution,
        bulky_priors_applied=bulky_priors_applied,
        
        # Uncertain blobs (Policy A)
        uncertain_blob_volume=ownership["uncertain_blob_volume"],
        uncertain_blob_count=ownership["uncertain_blob_count"],
        
        # Final
        final_volume=final_volume,
        
        # Area accounting
        pile_area=median_pile_ratio,
        subtracted_area=ownership["subtraction_area"],
        remainder_area=median_pile_ratio - ownership["subtraction_area"],
        bulk_residual_pct=lane_a.get("residual_for_bulk", median_pile_ratio - ownership["subtraction_area"]),  # P5: Single source
        
        # Change C: Overlap risk tracking
        overlap_risk_volume=ownership["overlap_risk_volume"],
    )
    
    # Check for unowned blobs (items with area > AREA_LARGE but no ownership)
    # P4: FREEZE ownership — detect and mark before ledger construction
    unowned_blob_count = 0
    for item in fused_items:
        if item.get("ownership") == "BULK_OWNED" and item.get("mask_area_ratio", 0) >= AREA_LARGE * 0.8:
            # Near-threshold unowned blobs (potential dead-zone)
            # P4: Mark as frozen — ownership cannot change after this point
            item["ownership_frozen"] = True
            item["ownership_reason"] = "large_bulk_owned"
            unowned_blob_count += 1
            ledger.unowned_blobs.append({
                "label": item.get("canonical_label", "?"),
                "area": item.get("mask_area_ratio", 0),
                "ownership": item.get("ownership", "?")
            })
    
    if unowned_blob_count > 0:
        vlog(f"   📐 P4 ownership frozen: {unowned_blob_count} large unowned blobs")
    
    # Run invariant checks (shadow mode - log but don't block)
    ledger.check_invariants()
    if ledger.violations:
        vlog(f"   ⚠️ LEDGER VIOLATIONS: {ledger.violations}")
    else:
        vlog(f"   ✅ Ledger balanced")
    

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
        
        # P1: Bulky lane details
        "bulky_contribution": round(bulky_contribution, 2),
        "bulky_count": bulky_count,
        "bulky_gate_passed": apply_bulky,
        
        # Metrics
        "item_count": len(fused_items),
        "items_with_masks": items_with_masks,
        "mask_coverage_pct": round(mask_coverage_pct, 1),
        "fallback_rate": round(fallback_rate, 3),
        
        # Full details
        "lane_a_details": lane_a,
        "lane_b_details": lane_b,
        
        # Phase 1: Volume Ledger (formal accounting)
        "volume_ledger": ledger.to_dict()
    }
    
    # ITEMIZED LOGGING: Debug each fused item
    log_itemized_breakdown(fused_items, lane_b)
    
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
