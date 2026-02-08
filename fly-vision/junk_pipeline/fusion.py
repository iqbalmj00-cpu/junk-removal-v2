"""
Stage 6: Multi-View Fusion (Production-Safe Weighted Median)
Goal: One reliable number from multiple noisy partial views.

Primary method: Weighted trimmed mean (stable, protects from outliers)
Diagnostic: Sum/weighted_sum (logged to detect partial-complement behavior)
"""

from dataclasses import dataclass, field
from typing import Optional
import numpy as np

from .volumetrics import VolumetricResult, DiscreteItem


@dataclass
class ViewQuality:
    """Quality metrics for a single view."""
    frame_id: str
    floor_quality: str  # "good", "noisy", "failed"
    depth_confidence: float
    volume_cy: float
    floor_flatness_p95: float = 0.20
    inlier_ratio: float = 0.0
    is_valid: bool = True
    rejection_reason: Optional[str] = None


@dataclass
class FusionResult:
    """Result of multi-view fusion."""
    final_volume_cy: float
    uncertainty_min_cy: float
    uncertainty_max_cy: float
    valid_frames: list[str] = field(default_factory=list)
    rejected_frames: list[str] = field(default_factory=list)
    rejection_reasons: dict = field(default_factory=dict)
    viewpoint_diversity: str = "unknown"  # "good", "low"
    fusion_method: str = "unknown"  # "weighted_trimmed_mean", "max_fallback"
    fused_discrete_items: list[DiscreteItem] = field(default_factory=list)
    # Diagnostic signals
    sum_valid_cy: float = 0.0  # Simple sum of valid frame volumes
    sum_weighted_cy: float = 0.0  # Weighted sum


# Catastrophic drop thresholds
CATASTROPHIC_INLIER_RATIO = 0.10  # Drop if inlier_ratio < 10%
CATASTROPHIC_YFL95_CEILING = 0.50  # Drop if floor flatness > 50cm
CATASTROPHIC_DEPTH_VALID_PCT = 0.50  # Drop if < 50% valid depth

# Quality weights
WEIGHT_GOOD = 1.0
WEIGHT_NOISY = 0.75
WEIGHT_FAILED = 0.4  # Non-catastrophic failed frames

# Physical cap
MAX_PILE_VOLUME_CY = 20.0  # Truck capacity

# =============================================================================
# v8.3 FEATURE FLAGS
# =============================================================================
FLOOR_FUSION_SOFTCONF = True  # Phase 4: soft floor confidence


def _compute_floor_confidence(inlier_ratio: float, yfl95: float, is_multi_surface: bool) -> float:
    """
    v8.3: Compute continuous 0-1 floor plane confidence.
    
    Used to scale fusion weight instead of binary exclusion.
    
    Args:
        inlier_ratio: RANSAC inlier ratio (0-1)
        yfl95: Floor flatness P95 in meters
        is_multi_surface: True if multi-surface scene detected
    
    Returns:
        Confidence score 0.1-1.0 (never fully excluded)
    """
    # Base from inlier ratio (0.9 = ideal)
    conf = min(1.0, inlier_ratio / 0.9)
    
    # Steeper penalty for yfl95 > 0.12m (unreliable baseline)
    if yfl95 > 0.12:
        penalty = min(0.7, (yfl95 - 0.12) / 0.15)
        conf *= (1.0 - penalty)
    elif yfl95 > 0.08:
        conf *= 0.85
    
    # Multi-surface detected = expected noise, don't over-penalize
    if is_multi_surface:
        conf = max(conf, 0.4)
    
    return max(0.1, conf)


# =============================================================================
# ROLE-BASED QUALIFICATION GATES (Action A)
# =============================================================================
# A frame must pass ALL relevant gates to be considered for a role.
# This prevents "one great metric hiding one terrible metric."

# Geometry Gates (apply to both footprint and height roles)
GATE_INLIER_RATIO_MIN = 0.60      # RANSAC must explain 60%+ of floor candidates
GATE_YFL95_MAX = 0.15             # Floor must be flat within 15cm at P95
GATE_TILT_DEG_MAX = 25.0          # Ground plane tilt must be under 25°

# Fix 2: Adaptive YFL95 thresholds by scene (stricter for height donor role)
GATE_INLIER_RATIO_FOR_HEIGHT = 0.90   # Height donors need high confidence floor
GATE_YFL95_BY_SCENE = {
    "indoor": 0.05,              # Strict for flat indoor floors
    "indoor_floor": 0.05,
    "outdoor_driveway": 0.07,    # Moderate for concrete/asphalt
    "parking_lot": 0.07,
    "outdoor_grass": 0.10,       # Relaxed for rough outdoor surfaces
    "outdoor_terrain": 0.10,
    "unknown": 0.08,             # Default moderate
}
GATE_YFL95_DEFAULT = 0.08  # Fallback threshold

# Segmentation Gates (apply to footprint role only)
GATE_MASK_COVERAGE_MAX = 0.50     # Mask can't be >50% of image
GATE_GROUND_OVERLAP_MAX = 0.20    # Max 20% of mask can be at ground level

# Depth/Height Gates (apply to height role only)
GATE_HEIGHT_MIN_M = 0.30          # Must detect at least 30cm height (Y_junk_max)

# Fix 1: Evidence envelope cap
ENVELOPE_CAP_MULTIPLIER = 1.15    # Cross-fusion capped at max_frame × 1.15

# Fix 5: Donor eligibility for cross-fusion
DONOR_WEIGHT_MIN = 0.70           # Both donors must have weight >= 0.70

# v8.7: Single-frame influence cap (governor)
# Prevents any single frame's volume from exceeding 65% of the final output
# Works with ENVELOPE_CAP_MULTIPLIER to bound outlier influence
MAX_SINGLE_FRAME_INFLUENCE = 0.65

# Fix 3: Router voting threshold (used in orchestrator)
ROUTER_INLIER_THRESHOLD = 0.75    # Frames need 75%+ inlier for routing vote

# Cross-fusion shape factor constants
DENSITY_FACTORS = {
    "solid": 0.95,   # Stacked boxes, bagged material, furniture
    "loose": 0.75,   # Mixed debris bags piled together
    "sparse": 0.50,  # Scattered loose junk, random items with gaps
}
SHAPE_FACTOR_DEFAULT = 0.85  # Fallback when no router data

# =============================================================================
# v6.4.0 FUSION QUALITY CONSTANTS
# =============================================================================

# S1: Union-blend for complementary views
COMPLEMENT_RATIO_THRESHOLD = 2.5   # Trigger when sum/median > 2.5
UNION_CAP_MULTIPLIER = 1.35        # V_union = min(V_sum, V_ref * 1.35)
BLEND_BASE_WEIGHT = 0.65           # V_final = 0.65*V_base + 0.35*V_union
BLEND_UNION_WEIGHT = 0.35

# S2: Weight normalization
WEIGHT_FLOOR = 0.05                # Minimum weight to avoid zeroing

# S3: Mask leakage penalty
BORDER_TOUCH_HEAVY = 0.30          # Heavy penalty threshold
BORDER_TOUCH_MODERATE = 0.15       # Moderate penalty threshold
SKIRT_RATIO_THRESHOLD = 0.40       # Skirt penalty (only with border-touch)
LEAKAGE_FACTOR_FLOOR = 0.35        # Minimum leakage factor

# =============================================================================
# v6.4.1 EVIDENCE WEIGHT DECOUPLING
# =============================================================================

# Dynamic evidence floor (scales with inlier quality)
EVIDENCE_FLOOR_INLIER_MIN = 0.65      # Minimum inlier for floor eligibility
EVIDENCE_FLOOR_BASE = 0.22            # Floor at inlier=0.65
EVIDENCE_FLOOR_MAX = 0.32             # Floor at inlier=0.90
EVIDENCE_FLOOR_PLANE_MAX = 20.0       # Max plane angle for floor eligibility
EVIDENCE_FLOOR_YFL95_MAX = 0.08       # Max floor noise for floor eligibility

# Two-tier partial view detection
SEM_REMOVED_SEVERE = 0.75             # Severe partial threshold
SEM_MASK_COV_MIN_SEVERE = 0.25
SEM_REMOVED_MODERATE = 0.65           # Moderate partial threshold
SEM_MASK_COV_MIN_MODERATE = 0.20

# Trusted-max criteria (for union cap)
TRUSTED_MAX_WEIGHT_MIN = 0.25         # Minimum evidence weight
TRUSTED_MAX_MASK_COV_MAX = 0.55       # Max mask coverage (leak signal)
TRUSTED_MAX_SKIRT_MAX = 0.40          # Max skirt ratio
TRUSTED_MAX_PLANE_ANGLE_MAX = 20.0    # Max plane angle
TRUSTED_MAX_SEM_REMOVED_MAX = 0.60    # v6.8.0: Max semantic removal for V_ref (was 0.75)
UNION_CAP_MULTIPLIER_TRUSTED = 1.15   # Smaller multiplier for trusted-max

# =============================================================================
# v6.5 MEASUREMENT EVIDENCE SCORE (MES) SYSTEM
# =============================================================================

# Component aggregation weights (sum to 1.0)
MES_WEIGHT_GEOMETRY = 0.35
MES_WEIGHT_COMPLETENESS = 0.25
MES_WEIGHT_HEIGHT = 0.25
MES_WEIGHT_SEMANTIC = 0.15

# Noise-ratio thresholds (yfl95 / height_p95)
NOISE_RATIO_EXCELLENT = 0.15       # No penalty
NOISE_RATIO_ACCEPTABLE = 0.25      # Eligible, no penalty
NOISE_RATIO_DEGRADED = 0.40        # Eligible but downweighted
NOISE_RATIO_EXCLUDE = 0.40         # Hard exclude

# Height outlier detection
HEIGHT_OUTLIER_MULTIPLIER = 1.6    # Frame height > 1.6× second highest = suspicious

# Trusted-max MES threshold
TRUSTED_MAX_MES_MIN = 0.45         # Minimum MES for trusted-max eligibility

# Smoothstep bounds for evidence concentration
EC_SMOOTHSTEP_LOW = 0.60
EC_SMOOTHSTEP_HIGH = 0.80


@dataclass
class MeasurementEvidenceScore:
    """v6.5: Per-frame measurement quality score with component breakdown."""
    frame_id: str
    raw_score: float = 0.0           # [0, 1] composite (weighted mean)
    
    # Component scores (each clamped to [0.05, 1.0])
    geometry_score: float = 0.0      # inlier, noise_ratio, plane angle
    completeness_score: float = 0.0  # mask coverage, border-touch, floor visibility
    height_score: float = 0.0        # height vs job consensus
    semantic_score: float = 0.0      # semantic removal damage
    
    # Tracking fields
    hard_excluded: bool = False
    exclusion_reason: Optional[str] = None
    noise_ratio: float = 0.0         # yfl95 / height_p95
    height_p95_m: float = 0.0
    
    # For logging
    inlier_ratio: float = 0.0
    yfl95: float = 0.0
    plane_angle_deg: float = 0.0
    border_touch_ratio: float = 0.0
    semantic_removed_pct: float = 0.0


def _smoothstep(x: float, edge0: float, edge1: float) -> float:
    """Smooth Hermite interpolation between edge0 and edge1."""
    t = max(0.0, min(1.0, (x - edge0) / (edge1 - edge0)))
    return t * t * (3 - 2 * t)


def _compute_mes_geometry_score(
    inlier_ratio: float,
    yfl95: float,
    height_p95: float,
    plane_angle_deg: float,
    second_highest_height: float = 0.0,
    # v8.5.3: Support-plane bypass
    support_plane_selected: bool = False,
    sr_yfl95: float = 0.20
) -> tuple[float, float, bool, Optional[str]]:
    """
    v6.5: Compute geometry component of MES.
    
    Returns: (geometry_score, noise_ratio, hard_excluded, exclusion_reason)
    """
    # v8.5.3: Use sr_yfl95 for noise ratio when support plane is selected
    effective_yfl95 = sr_yfl95 if support_plane_selected else yfl95
    noise_ratio = effective_yfl95 / max(height_p95, 0.30)
    
    # v6.8.0 Fix C: Soft yfl95 band for borderline frames
    # Hard exclusion at 0.30 (relaxed in v8.2.2 from 0.25), soft penalty from 0.20-0.30
    GATE2_YFL95_SOFT_THRESHOLD = 0.20  # Start of penalty band
    GATE2_YFL95_HARD_EXCLUSION = 0.30  # v8.2.2: Relaxed from 0.25
    SR_YFL95_THRESHOLD = 0.15          # v8.5.3: Threshold for support-plane branch
    YFL95_SOFT_PENALTY = 0.30          # Weight multiplier for borderline frames
    
    # v8.5.3: Support-plane bypass for yfl95 hard exclusion
    if support_plane_selected:
        # When support plane is valid, use sr_yfl95 instead of global yfl95
        if sr_yfl95 <= SR_YFL95_THRESHOLD:
            # Support plane is valid - bypass global yfl95 gate entirely
            # Global yfl95 will still affect weight as penalty
            pass  # Continue to compute score
        else:
            # Support plane selected but sr_yfl95 is high - still exclude
            return 0.0, noise_ratio, True, f"sr_yfl95={sr_yfl95:.3f}>{SR_YFL95_THRESHOLD}"
    elif yfl95 > GATE2_YFL95_HARD_EXCLUSION:
        # Legacy branch: no support plane, use global yfl95
        return 0.0, noise_ratio, True, f"floor_quality_failed: yfl95={yfl95:.3f}>{GATE2_YFL95_HARD_EXCLUSION}"
    elif yfl95 > GATE2_YFL95_SOFT_THRESHOLD:
        # Soft penalty band - frame contributes but with reduced weight
        # Will be applied later in weight calculation
        pass  # Continue to compute score, penalty applied in weight stage
    
    # Existing noise ratio check
    if noise_ratio > NOISE_RATIO_EXCLUDE:
        return 0.0, noise_ratio, True, f"noise_ratio={noise_ratio:.2f}>0.40"
    
    # Height outlier guard
    outlier_penalty = 1.0
    if second_highest_height > 0 and height_p95 > HEIGHT_OUTLIER_MULTIPLIER * second_highest_height:
        outlier_penalty = 0.7  # Suspicious - cap contribution
    
    # Noise penalty tiers
    if noise_ratio <= NOISE_RATIO_ACCEPTABLE:
        noise_penalty = 1.0
    elif noise_ratio <= NOISE_RATIO_DEGRADED:
        # Linear decay from 1.0 at 0.25 to 0.0 at 0.40
        noise_penalty = 1.0 - (noise_ratio - NOISE_RATIO_ACCEPTABLE) / (NOISE_RATIO_DEGRADED - NOISE_RATIO_ACCEPTABLE)
    else:
        noise_penalty = 0.0
    
    # Angle factor: <12° = full, >25° = 0
    angle_factor = max(0.0, min(1.0, (25.0 - plane_angle_deg) / 13.0))
    
    # Inlier factor
    inlier_factor = min(1.0, inlier_ratio / 0.90)
    
    geometry_score = inlier_factor * noise_penalty * angle_factor * outlier_penalty
    
    return geometry_score, noise_ratio, False, None


def _compute_mes_completeness_score(
    mask_coverage: float,
    border_touch_ratio: float,
    floor_visible: bool,
    ground_overlap_ratio: float = 0.0
) -> float:
    """v6.5: Compute completeness component of MES."""
    # Border touch penalty
    if border_touch_ratio > BORDER_TOUCH_HEAVY:
        border_factor = 0.4
    elif border_touch_ratio > BORDER_TOUCH_MODERATE:
        border_factor = 0.7
    else:
        border_factor = 1.0
    
    # Floor visibility
    floor_factor = 1.0 if floor_visible else 0.6
    
    # Mask leakage (high coverage + high ground overlap)
    if mask_coverage > 0.50 and ground_overlap_ratio > 0.20:
        leak_factor = 0.5
    elif mask_coverage > 0.65:
        leak_factor = 0.7
    else:
        leak_factor = 1.0
    
    return border_factor * floor_factor * leak_factor


def _compute_mes_height_score(
    frame_height_p95: float,
    job_height_consensus: float
) -> float:
    """v6.5: Compute height component of MES relative to job consensus."""
    if job_height_consensus <= 0:
        return 0.5  # Unknown consensus - neutral
    
    # Relative error
    error = abs(frame_height_p95 - job_height_consensus) / job_height_consensus
    
    # Smooth penalty for deviation
    if error <= 0.15:
        return 1.0
    elif error <= 0.40:
        return 1.0 - (error - 0.15) * 2  # Linear decay
    else:
        return 0.5  # Floor - don't crush completely


def _compute_mes_semantic_score(semantic_removed_pct: float) -> float:
    """
    v6.6.0: Compute semantic component of MES with steeper penalty.
    
    Changed from v6.5:
    - Steeper penalty for 50%+ removal
    - Floor at 0.10 (was 0.30) for heavily damaged frames
    """
    if semantic_removed_pct < 0.50:
        # Mild removal: linear decay
        return max(0.50, 1.0 - semantic_removed_pct)
    else:
        # Severe removal (50%+): steeper decay
        # At 50%: 0.50, at 75%: 0.125, at 100%: ~0
        penalty = 0.50 - (semantic_removed_pct - 0.50) * 1.5
        return max(0.10, penalty)


def _compute_job_height_consensus(role_qualifications: list) -> float:
    """
    v6.5.2: Robust height consensus with quality filtering and outlier pruning.
    
    Step 2 of stability fix:
    - Define high-quality set (strict thresholds)
    - Drop heights < 50% of max within good set
    - Use weighted median for final consensus
    """
    # Strict thresholds for height voting eligibility
    HC_INLIER_MIN = 0.85  # Stricter than V_ref
    HC_YFL95_MAX = 0.12   # Stricter: floor noise < 12cm (legacy, when no support plane)
    HC_SEM_REMOVED_MAX = 0.60  # Not catastrophically damaged
    HC_HEIGHT_MIN = 0.20  # Minimum height to consider
    
    # v8.5.2: Support-plane thresholds (replace yfl95 when support_plane_selected=True)
    HC_SR_INLIER_MIN = 0.70   # Require 70% inlier ratio in support ROI
    HC_SR_YFL95_MAX = 0.15    # Support ROI residual < 15cm
    
    # Build high-quality set for height voting
    height_candidates = []
    all_heights = []
    
    for rq in role_qualifications:
        height = rq.height_p85_m
        if height <= 0:
            continue
        all_heights.append(height)
        
        if height <= HC_HEIGHT_MIN:
            continue
        
        # Strict quality requirements
        sem_removed = getattr(rq, 'semantic_removed_pct', 0.0)
        support_plane_selected = getattr(rq, 'support_plane_selected', False)
        sr_inlier_ratio = getattr(rq, 'sr_inlier_ratio', 0.0)
        sr_yfl95 = getattr(rq, 'sr_yfl95', 0.20)
        
        eligible = True
        reasons = []
        
        # v8.5.2: Use support-plane metrics when available, else fallback to yfl95
        if support_plane_selected:
            # Support plane branch: use sr_inlier_ratio and sr_yfl95
            if sr_inlier_ratio < HC_SR_INLIER_MIN:
                eligible = False
                reasons.append(f"sr_inlier={sr_inlier_ratio:.2f}<{HC_SR_INLIER_MIN}")
            
            if sr_yfl95 > HC_SR_YFL95_MAX:
                eligible = False
                reasons.append(f"sr_yfl95={sr_yfl95:.2f}>{HC_SR_YFL95_MAX}")
            
            # yfl95 becomes a confidence penalty, not eligibility gate
            # (handled via weight below)
        else:
            # Legacy branch: use global inlier_ratio and yfl95
            if rq.inlier_ratio < HC_INLIER_MIN:
                eligible = False
                reasons.append(f"inlier={rq.inlier_ratio:.2f}<{HC_INLIER_MIN}")
            
            if rq.yfl95 > HC_YFL95_MAX:
                eligible = False
                reasons.append(f"yfl95={rq.yfl95:.2f}>{HC_YFL95_MAX}")
        
        if sem_removed > HC_SEM_REMOVED_MAX:
            eligible = False
            reasons.append(f"sem={sem_removed:.0%}>{HC_SEM_REMOVED_MAX:.0%}")
        
        # v10.4: Intrinsics mismatch gating (>15% deviation excludes from height consensus)
        fx_ratio = getattr(rq, 'intrinsics_fx_ratio', None)
        fx_derived = getattr(rq, 'intrinsics_derived', False)
        if fx_ratio is not None and not fx_derived:  # Only penalize if bundle was not derived
            deviation = abs(fx_ratio - 1.0)
            if deviation > 0.15:
                eligible = False
                reasons.append(f"intrinsics_mismatch={deviation:.0%}>15%")
        
        # Weight based on geometry quality (use support plane metrics when available)
        if support_plane_selected:
            # Use sr_yfl95 for noise ratio, apply yfl95 as soft penalty
            noise_ratio = sr_yfl95 / max(height, 0.30)
            yfl95_penalty = max(0.5, 1.0 - (rq.yfl95 - 0.15) / 0.30)  # Penalty above 0.15m
            w = max(0.4, min(1.0, sr_inlier_ratio)) * max(0.0, min(1.0, 1 - noise_ratio / 0.20)) * yfl95_penalty
        else:
            noise_ratio = rq.yfl95 / max(height, 0.30)
            w = max(0.4, min(1.0, rq.inlier_ratio)) * max(0.0, min(1.0, 1 - noise_ratio / 0.20))
        
        height_candidates.append({
            'frame_id': rq.frame_id,
            'height': height,
            'weight': w,
            'inlier': rq.inlier_ratio,
            'yfl95': rq.yfl95,
            'sr_inlier': sr_inlier_ratio,
            'sr_yfl95': sr_yfl95,
            'support_plane': support_plane_selected,
            'sem_removed': sem_removed,
            'eligible': eligible,
            'reason': ', '.join(reasons) if reasons else 'ok'
        })
    
    # Log all candidates
    print(f"[HC_DEBUG] height_candidates = [")
    for c in height_candidates:
        status = "PASS" if c['eligible'] else f"FAIL({c['reason']})"
        sp_tag = "SP" if c['support_plane'] else "GP"
        print(f"  {{frame={c['frame_id'][:8]}, h={c['height']:.2f}m, {sp_tag}, sr={c['sr_inlier']:.2f}, sr_p95={c['sr_yfl95']:.2f}, {status}}}")
    print(f"]")
    
    # Filter to eligible only
    eligible = [(c['height'], c['weight'], c['frame_id']) for c in height_candidates if c['eligible']]
    
    # =================================================================
    # v6.6.0: Weighted robust consensus - no fallback discontinuity
    # =================================================================
    # If no strictly eligible frames, use ALL frames with quality weights
    # This eliminates the "0 eligible → max height" jump
    if not eligible:
        if not all_heights:
            print(f"[HeightConsensus] No heights available, using default 0.50m")
            return 0.50
        
        # Weighted consensus using ALL candidates (including non-eligible)
        # Weight by geometry quality even for non-eligible frames
        all_weighted = []
        for c in height_candidates:
            # Use reduced weight for non-eligible frames
            w = c['weight'] * (0.4 if not c['eligible'] else 1.0)
            all_weighted.append((c['height'], w, c['frame_id']))
        
        if all_weighted:
            consensus = _weighted_median([h for h, w, _ in all_weighted], [w for _, w, _ in all_weighted])
            print(f"[HeightConsensus] Weighted fallback (no strict-eligible): {consensus:.2f}m from {len(all_weighted)} frames")
            return consensus
        else:
            # Absolute fallback
            consensus = np.median(all_heights)
            print(f"[HeightConsensus] Median fallback: {consensus:.2f}m")
            return consensus
    
    # Step 2b: Adaptive height pruning (v6.5.2b)
    # Use stricter threshold with more candidates
    max_height_eligible = max(h for h, _, _ in eligible)
    n_candidates = len(eligible)
    
    if n_candidates >= 3:
        prune_ratio = 0.70  # Stricter: drop < 70% of max
    elif n_candidates == 2:
        prune_ratio = 0.60  # Less aggressive for 2 candidates
    else:
        prune_ratio = 0.0   # Single candidate, no pruning
    
    height_floor = prune_ratio * max_height_eligible
    
    before_prune = n_candidates
    eligible_pruned = [(h, w, fid) for h, w, fid in eligible if h >= height_floor]
    after_prune = len(eligible_pruned)
    
    print(f"[HC_DEBUG] height_consensus_before_prune={before_prune}, after_prune={after_prune}")
    print(f"[HC_DEBUG] max_height_eligible={max_height_eligible:.2f}m, prune_ratio={prune_ratio:.0%}, height_floor={height_floor:.2f}m")
    
    # Only prune if we have at least 2 frames remaining
    if len(eligible_pruned) >= 2:
        eligible = eligible_pruned
        if after_prune < before_prune:
            print(f"[HeightConsensus] Pruned {before_prune - after_prune} low-height frames (<{height_floor:.2f}m)")
    elif len(eligible_pruned) == 1 and n_candidates > 1:
        # Relaxed fallback: if pruning leaves 1, use it but log warning
        eligible = eligible_pruned
        print(f"[HeightConsensus] ⚠️ Pruning left only 1 frame - using it")
    else:
        print(f"[HeightConsensus] Skipped pruning (would leave <1 frame)")
    
    # Log final eligible frames
    for h, w, fid in eligible:
        print(f"[HeightConsensus] {fid[:8]}: height={h:.2f}m, weight={w:.2f}")
    
    # Weighted median
    consensus = _weighted_median([h for h, _, _ in eligible], [w for _, w, _ in eligible])
    n_donors = len(eligible)
    print(f"[HeightConsensus] Result: {consensus:.2f}m (from {n_donors} frames)")
    
    # v6.8.0: Low donor policy warning
    if n_donors < 2:
        print(f"[HeightConsensus] ⚠️ LOW_DONOR: only {n_donors} frame(s) → uncertainty should widen")
    
    return consensus




def _compute_height_consensus_leave_one_out(
    role_qualifications: list,
    exclude_frame_id: str
) -> float:
    """
    v6.5.1: Leave-one-out consensus to avoid circular penalty.
    
    Computes height consensus excluding the specified frame.
    """
    filtered = [rq for rq in role_qualifications if rq.frame_id != exclude_frame_id]
    if not filtered:
        return 0.50
    return _compute_job_height_consensus(filtered)


def _weighted_median(values: list, weights: list) -> float:
    """Compute weighted median."""
    if not values or not weights:
        return 0.0
    if len(values) == 1:
        return values[0]
    
    # Sort by value
    sorted_pairs = sorted(zip(values, weights), key=lambda x: x[0])
    cumsum = 0.0
    total = sum(weights)
    
    for v, w in sorted_pairs:
        cumsum += w
        if cumsum >= total / 2:
            return v
    
    return sorted_pairs[-1][0]


def _compute_mes(
    geometry_score: float,
    completeness_score: float,
    height_score: float,
    semantic_score: float
) -> float:
    """
    v6.5: Compute composite MES using weighted mean with clamped components.
    
    Weighted mean prevents single-component collapse.
    """
    # Clamp each component to [0.05, 1.0]
    g = max(0.05, min(1.0, geometry_score))
    c = max(0.05, min(1.0, completeness_score))
    h = max(0.05, min(1.0, height_score))
    s = max(0.05, min(1.0, semantic_score))
    
    # Weighted mean
    raw = (g * MES_WEIGHT_GEOMETRY) + (c * MES_WEIGHT_COMPLETENESS) + \
          (h * MES_WEIGHT_HEIGHT) + (s * MES_WEIGHT_SEMANTIC)
    
    # Extreme condition penalty (applied after, not multiplied in)
    if geometry_score < 0.15:
        raw *= 0.6  # Very bad geometry
    
    return max(0.05, min(1.0, raw))


def _compute_blend_weights_v65(mes_scores: list) -> tuple[float, float]:
    """
    v6.5: Compute blend weights using smooth evidence concentration.
    
    Returns: (base_weight, union_weight)
    """
    if len(mes_scores) < 2:
        return 0.65, 0.35  # Default
    
    sorted_scores = sorted([m.raw_score for m in mes_scores], reverse=True)
    
    # Evidence concentration
    ec = sorted_scores[0] / (sorted_scores[0] + sorted_scores[1])
    
    # Smooth mapping: union_weight rises gradually from 0.35 to 0.70
    union_weight = 0.35 + 0.35 * _smoothstep(ec, EC_SMOOTHSTEP_LOW, EC_SMOOTHSTEP_HIGH)
    union_weight = max(0.35, min(0.70, union_weight))
    
    # Safety: cap union_weight if top frame has issues
    top_mes = next(m for m in mes_scores if m.raw_score == sorted_scores[0])
    if top_mes.semantic_score < 0.4 or top_mes.completeness_score < 0.3:
        union_weight = min(union_weight, 0.45)
    
    base_weight = 1.0 - union_weight
    return base_weight, union_weight


# =============================================================================
# v7.2: FUSION GOVERNOR FUNCTIONS
# =============================================================================

def _compute_footprint_consistency_log_ratio(role_qualifications: list) -> dict[str, tuple[float, bool]]:
    """
    v7.2: Log-ratio footprint consistency using MAD for symmetric outlier detection.
    
    Returns:
        dict[frame_id -> (log_ratio, is_inlier)]
        
    Inlier = |log_ratio - median| < 2.5 * MAD
    """
    import numpy as np
    
    # Filter to frames with positive footprint
    valid_rqs = [rq for rq in role_qualifications if rq.footprint_m2 > 0.01]
    
    if len(valid_rqs) < 2:
        return {rq.frame_id: (0.0, True) for rq in role_qualifications}
    
    footprints = np.array([rq.footprint_m2 for rq in valid_rqs])
    log_fps = np.log(footprints)
    
    median_log = np.median(log_fps)
    deviations = np.abs(log_fps - median_log)
    mad = np.median(deviations)  # Median Absolute Deviation
    
    # Threshold: 2.5 * MAD (robust ~95% interval)
    threshold = 2.5 * max(mad, 0.05)  # Floor MAD at 0.05 to avoid tiny thresholds
    
    results = {}
    for rq, log_fp in zip(valid_rqs, log_fps):
        log_ratio = log_fp - median_log
        is_inlier = abs(log_ratio) <= threshold
        results[rq.frame_id] = (log_ratio, is_inlier)
        status = "INLIER" if is_inlier else "OUTLIER"
        print(f"[FP_LOG_RATIO] {rq.frame_id[:8]}: log_ratio={log_ratio:.3f}, {status} (thresh={threshold:.3f})")
    
    # Mark frames with no footprint as inliers (fail-open)
    for rq in role_qualifications:
        if rq.frame_id not in results:
            results[rq.frame_id] = (0.0, True)
    
    return results


def _compute_volume_plausibility(
    frame_volume: float,
    inlier_volumes: list[float]
) -> float:
    """
    v7.2: Huber-style continuous volume plausibility weighting.
    
    Smoothly downweights outliers instead of hard gating.
    
    Returns: weight multiplier 0.0-1.0
    """
    import numpy as np
    
    if len(inlier_volumes) < 2:
        return 1.0  # Not enough data, fail-open
    
    median_vol = np.median(inlier_volumes)
    if median_vol < 0.1:
        return 1.0  # Avoid division issues
    
    ratio = frame_volume / median_vol
    
    # Huber-style: linear penalty outside [0.5, 1.5]
    if 0.7 <= ratio <= 1.3:
        return 1.0  # Core zone: full weight
    elif 0.5 <= ratio <= 0.7:
        return 0.6 + (ratio - 0.5) * 2.0  # Ramp up from 0.6 to 1.0
    elif 1.3 <= ratio <= 1.5:
        return 1.0 - (ratio - 1.3) * 2.0  # Ramp down from 1.0 to 0.6
    elif 1.5 < ratio <= 2.0:
        return max(0.2, 0.6 - (ratio - 1.5) * 0.8)  # Further decay
    else:
        return 0.2  # Extreme outlier: floor weight


def _compute_frame_eligibility(
    frame_id: str,
    rq,  # RoleQualification
    geometry_result,  # GeometryResult
    mes=None,  # MeasurementEvidenceScore
    fp_consistency: dict = None,
    triage_result=None
) -> dict:
    """
    v7.2: Unified frame eligibility - single source of truth.
    
    Combines all eligibility gates into one function to prevent drift.
    
    Returns dict with:
        - eligible_vref: Can be V_ref anchor
        - eligible_footprint: Can donate footprint
        - eligible_height: Can donate height
        - weight_multiplier: 0.0-1.0 weighting factor
        - reason_codes: List of disqualification reasons
    """
    result = {
        "eligible_vref": True,
        "eligible_footprint": True,
        "eligible_height": True,
        "weight_multiplier": 1.0,
        "reason_codes": []
    }
    
    # Gate 1: Geometry eligibility (from geometry.py)
    if geometry_result and not geometry_result.eligible_for_footprint:
        result["eligible_footprint"] = False
        result["eligible_vref"] = False
        result["reason_codes"].append("geo_footprint_gate")
    
    if geometry_result and not geometry_result.eligible_for_height:
        result["eligible_height"] = False
        result["eligible_vref"] = False
        result["reason_codes"].append("geo_height_gate")
    
    # Gate 2: Footprint consistency
    if fp_consistency and frame_id in fp_consistency:
        _, is_inlier = fp_consistency[frame_id]
        if not is_inlier:
            result["eligible_vref"] = False
            result["eligible_footprint"] = False
            result["weight_multiplier"] *= 0.4
            result["reason_codes"].append("fp_outlier")
    
    # Gate 3: MES hard exclusion
    if mes and mes.hard_excluded:
        result["eligible_vref"] = False
        result["weight_multiplier"] *= 0.0
        result["reason_codes"].append(mes.exclusion_reason or "mes_excluded")
    
    # Gate 4: Geometry weight cap (D_skip, multi-surface)
    if geometry_result and geometry_result.fusion_weight_cap < 1.0:
        result["weight_multiplier"] = min(
            result["weight_multiplier"],
            geometry_result.fusion_weight_cap
        )
        if geometry_result.fusion_weight_cap <= 0.3:
            result["eligible_vref"] = False
            result["reason_codes"].append("weight_cap_low")
    
    # Gate 5: VLM triage (soft penalty)
    if triage_result and triage_result.triage_available:
        frame_roles = triage_result.frame_roles.get(frame_id)
        if frame_roles and not frame_roles.vref_ok:
            result["eligible_vref"] = False
            result["reason_codes"].append("triage_vref_blocked")
    
    # Gate 6: v8.3/8.4 Floor Confidence (soft thresholds, not binary exclusion)
    if FLOOR_FUSION_SOFTCONF and geometry_result:
        # Compute global floor confidence
        floor_conf = _compute_floor_confidence(
            inlier_ratio=geometry_result.ground_plane.inlier_ratio if geometry_result.ground_plane else 0.0,
            yfl95=geometry_result.floor_flatness_p95,
            is_multi_surface=geometry_result.is_multi_surface or geometry_result.is_multi_surface_hint
        )
        # Store floor_conf in geometry result for downstream use
        geometry_result.floor_conf = floor_conf
        
        # v8.4: Use local confidence for donor eligibility when available
        # Local confidence is pile-relative, more reliable for height/footprint
        floor_conf_local = geometry_result.floor_conf_local if hasattr(geometry_result, 'floor_conf_local') else floor_conf
        
        # Soft thresholds using LOCAL confidence
        # Height donor: local_conf >= 0.6 (pile support plane must be reliable)
        # Footprint donor: local_conf >= 0.4 (more permissive)
        if floor_conf_local < 0.4:
            result["eligible_footprint"] = False
            result["reason_codes"].append("floor_conf_local_low_fp")
        if floor_conf_local < 0.6:
            result["eligible_height"] = False
            result["reason_codes"].append("floor_conf_local_low_ht")
        
        # Scale weight by min(global, local) (honesty: if either is bad, widen band)
        combined_conf = min(floor_conf, floor_conf_local)
        result["weight_multiplier"] *= combined_conf
        
        print(f"[FLOOR_CONF] {frame_id[:8]}: global={floor_conf:.2f}, local={floor_conf_local:.2f}, "
              f"eligible_fp={result['eligible_footprint']}, eligible_ht={result['eligible_height']}")
    
    return result


def _compute_viewpoint_diversity(triage_result=None, num_frames: int = 0) -> float:
    """
    v7.2: Compute viewpoint diversity factor (0.5-1.0).
    
    Low diversity = all frames capture similar viewpoint = correlated failures.
    High diversity = frames from different angles = independent measurements.
    
    Returns: diversity factor to scale uncertainty
    """
    if num_frames < 2:
        return 0.7  # Single frame: moderate penalty
    
    if triage_result is None or not triage_result.triage_available:
        # No triage data: assume moderate diversity
        base = min(1.0, 0.5 + num_frames * 0.1)
        return base
    
    # Estimate diversity from frame signals
    # Different crop_risk + occlusion patterns suggest different viewpoints
    signals = list(triage_result.frame_signals.values())
    if len(signals) < 2:
        return 0.7
    
    crop_risks = [s.crop_risk for s in signals]
    occlusion_risks = [s.occlusion_risk for s in signals]
    
    import numpy as np
    crop_std = np.std(crop_risks) if len(crop_risks) > 1 else 0
    occlusion_std = np.std(occlusion_risks) if len(occlusion_risks) > 1 else 0
    
    # High variance in risks = diverse viewpoints
    diversity = 0.5 + crop_std * 0.5 + occlusion_std * 0.5
    return min(1.0, max(0.5, diversity))


def _compute_evidence_uncertainty(
    inlier_frames: list,
    final_volume: float,
    floor_quality_score: float = 0.7,
    mask_risk_avg: float = 0.0,
    viewpoint_diversity: float = 0.8,
    outlier_count: int = 0
) -> tuple[float, float]:
    """
    v7.2: Compute evidence-based uncertainty multipliers.
    
    Replaces fixed ±6% with dynamic bands (3-15%) based on:
    - Frame agreement (CV of inlier volumes)
    - Number of quality donors
    - Floor quality score
    - Mask risk average
    - Viewpoint diversity
    - Number of outliers excluded
    
    Returns:
        (uncertainty_low_mult, uncertainty_high_mult) as fractions (e.g., 0.05, 0.10)
    """
    import numpy as np
    
    # Base uncertainty: 6%
    base = 0.06
    
    # Factor 1: Frame agreement (CV of volumes)
    volumes = [f.frame_volume_cy for f in inlier_frames if hasattr(f, 'frame_volume_cy') and f.frame_volume_cy > 0]
    if len(volumes) >= 2:
        cv = np.std(volumes) / np.mean(volumes)
        if cv < 0.10:
            agreement_factor = 0.7  # Excellent agreement → tighten
        elif cv < 0.20:
            agreement_factor = 1.0  # Good agreement → baseline
        elif cv < 0.35:
            agreement_factor = 1.3  # Moderate disagreement → widen
        else:
            agreement_factor = 1.6  # Poor agreement → wide bands
    else:
        agreement_factor = 1.3  # Single frame: moderate widen
    
    # Factor 2: Number of quality donors
    n_donors = len(volumes)
    if n_donors >= 4:
        donor_factor = 0.85  # Many donors → tighter
    elif n_donors == 3:
        donor_factor = 1.0
    elif n_donors == 2:
        donor_factor = 1.2
    else:
        donor_factor = 1.4  # Few donors → wider
    
    # Factor 3: Floor quality
    floor_factor = 1.5 - 0.5 * floor_quality_score  # 1.0 at quality=1.0, 1.35 at quality=0.3
    
    # Factor 4: Mask risk
    mask_factor = 1.0 + mask_risk_avg * 0.5  # 1.0-1.5 range
    
    # Factor 5: Viewpoint diversity
    diversity_factor = 1.5 - 0.5 * viewpoint_diversity  # 1.0 at diversity=1.0, 1.25 at diversity=0.5
    
    # Factor 6: Outlier penalty
    outlier_factor = 1.0 + 0.1 * outlier_count
    
    # Combine factors
    combined = base * agreement_factor * donor_factor * floor_factor * mask_factor * diversity_factor * outlier_factor
    
    # Clamp to valid range (3-15%)
    uncertainty = min(0.15, max(0.03, combined))
    
    # Asymmetric: high side gets extra 20% for Huber-style conservatism
    uncertainty_low = uncertainty
    uncertainty_high = uncertainty * 1.2
    
    print(f"[Evidence_Uncertainty] base={base:.2f}, "
          f"agreement={agreement_factor:.2f}, donors={donor_factor:.2f}, "
          f"floor={floor_factor:.2f}, mask={mask_factor:.2f}, "
          f"diversity={diversity_factor:.2f}, outliers={outlier_factor:.2f}")
    print(f"[Evidence_Uncertainty] final=±{uncertainty:.1%} (low={uncertainty_low:.1%}, high={uncertainty_high:.1%})")
    
    return uncertainty_low, uncertainty_high


# =============================================================================
# v6.5.1: MES-BASED FUSION WEIGHTS
# =============================================================================

MES_WEIGHT_POWER = 2.0              # Power curve for dominance
MES_WEIGHT_FLOOR = 0.08             # Minimum weight for eligible frames
SEM_DAMAGE_SEVERE = 0.50            # v6.6.0: Lowered from 0.70 for earlier penalty
SEM_DAMAGE_PENALTY = 0.5            # v6.6.0: Steeper penalty (was 0.7)

# v6.6.0: Floor-gate borderline cap
FLOOR_BORDERLINE_THRESHOLD = 0.12   # < 12% clear = borderline
FLOOR_BORDERLINE_MES_CAP = 0.60     # Cap MES at 0.60 for borderline frames


def _compute_mes_fusion_weights(mes_scores: list, role_qualifications: list = None, triage_result = None, depth_sub_saved_lookup: dict = None) -> dict:
    """
    v6.5.2b: Compute normalized fusion weights from MES scores.
    
    Uses power curve so good frames dominate without being binary.
    Hard-excluded frames get weight floor only.
    
    NEW: Footprint sanity guard - downweight outlier footprints.
    v6.9.0: Triage weight multiplier - downweight frames with high VLM risk scores.
    v8.2.2: Skip FP_GUARD when geometry proves overlap isn't floor (depth_sub_saved_lookup).
    """
    if not mes_scores:
        return {}
    
    # v6.5.2b: Footprint sanity guard
    FP_HIGH_RATIO = 1.6  # > 1.6× median = likely overmasking
    FP_LOW_RATIO = 0.6   # < 0.6× median = likely under-segmentation
    FP_PENALTY = 0.5     # Penalty multiplier for outliers
    
    # Build footprint lookup from role_qualifications
    footprint_lookup = {}
    if role_qualifications:
        quality_footprints = []
        for rq in role_qualifications:
            fp_m2 = getattr(rq, 'footprint_m2', 0.0)
            if fp_m2 <= 0:
                # Fallback: compute from cells if available
                fp_cells = getattr(rq, 'footprint_cells', 0)
                fp_m2 = fp_cells * 0.01  # 10cm cells
            footprint_lookup[rq.frame_id] = fp_m2
            # Only include quality frames for median calculation
            if rq.inlier_ratio >= 0.75 and rq.yfl95 <= 0.15:
                quality_footprints.append(fp_m2)
        
        # Compute median footprint from quality frames
        if quality_footprints:
            quality_footprints.sort()
            n = len(quality_footprints)
            fp_median = quality_footprints[n // 2] if n % 2 == 1 else (quality_footprints[n // 2 - 1] + quality_footprints[n // 2]) / 2
        else:
            fp_median = 0.0
        
        if fp_median > 0:
            print(f"[FP_GUARD] fp_median={fp_median:.2f}m², range=[{FP_LOW_RATIO*fp_median:.2f}, {FP_HIGH_RATIO*fp_median:.2f}]")
    else:
        fp_median = 0.0
    
    weights = {}
    
    for mes in mes_scores:
        if mes.hard_excluded:
            # v6.8.0: Hard excluded gets weight=0 (cannot influence final estimate)
            # This enforces the contract: EXCLUDED status means diagnostic-only
            weights[mes.frame_id] = 0.0
            print(f"[MES-Weight] {mes.frame_id[:8]}: EXCLUDED (w=0.00, {mes.exclusion_reason})")
            continue
        
        # Base weight from MES with power curve
        w = max(0.0, min(1.0, mes.raw_score)) ** MES_WEIGHT_POWER
        
        # Semantic damage penalty for severely filtered frames
        if mes.semantic_removed_pct >= SEM_DAMAGE_SEVERE:
            # Extra penalty to prevent domination
            w *= SEM_DAMAGE_PENALTY
            print(f"[MES-Weight] {mes.frame_id[:8]}: sem_damage_penalty applied (removed={mes.semantic_removed_pct:.0%})")
        
        # v6.6.0: Floor-gate borderline MES cap
        # Look up bottom_clear_pct from role_qualifications if available
        rq = next((r for r in (role_qualifications or []) if r.frame_id == mes.frame_id), None)
        if rq:
            bottom_clear = getattr(rq, 'bottom_clear_pct', 1.0)
            if bottom_clear < FLOOR_BORDERLINE_THRESHOLD:
                w = min(w, FLOOR_BORDERLINE_MES_CAP)
                print(f"[MES-Weight] {mes.frame_id[:8]}: borderline_cap applied (clear={bottom_clear:.1%}<{FLOOR_BORDERLINE_THRESHOLD:.0%})")
        
        # v6.5.2b: Footprint sanity guard
        # v8.2.2: Skip overmasking penalty if geometry proves overlap isn't floor
        fp = footprint_lookup.get(mes.frame_id, 0.0)
        if fp_median > 0 and fp > 0:
            # Check if we should skip FP_GUARD for this frame
            saved_ratio = (depth_sub_saved_lookup or {}).get(mes.frame_id, 0.0)
            skip_fp_guard_high = saved_ratio > 0.7  # Geometry proves >70% overlap isn't floor
            
            if fp > FP_HIGH_RATIO * fp_median:
                if skip_fp_guard_high:
                    print(f"[FP_GUARD] {mes.frame_id[:8]}: SKIP overmasking (saved_ratio={saved_ratio:.2f}>0.7, geometry proves overlap isn't floor)")
                else:
                    w *= FP_PENALTY
                    print(f"[FP_GUARD] {mes.frame_id[:8]}: PENALIZED (fp={fp:.2f}>{FP_HIGH_RATIO*fp_median:.2f}, overmasking)")
            elif fp < FP_LOW_RATIO * fp_median:
                w *= FP_PENALTY
                print(f"[FP_GUARD] {mes.frame_id[:8]}: PENALIZED (fp={fp:.2f}<{FP_LOW_RATIO*fp_median:.2f}, under-seg)")
        
        # v6.8.0 Fix C: Soft penalty for borderline yfl95 frames (0.20-0.25)
        # These frames passed geometry but floor is noisy - contribute with reduced weight
        YFL95_SOFT_THRESHOLD = 0.20
        YFL95_HARD_THRESHOLD = 0.25
        YFL95_SOFT_PENALTY = 0.30  # Reduced contribution
        if rq and hasattr(rq, 'yfl95'):
            if YFL95_SOFT_THRESHOLD < rq.yfl95 <= YFL95_HARD_THRESHOLD:
                w *= YFL95_SOFT_PENALTY
                print(f"[MES-Weight] {mes.frame_id[:8]}: yfl95_soft_penalty applied (yfl95={rq.yfl95:.3f}, w×{YFL95_SOFT_PENALTY})")
        
        # v6.9.0: Apply triage weight multiplier (if triage available)
        # This uses VLM-detected risks to soft-penalize frames
        try:
            from .vlm_triage import compute_triage_weight
            w_triage = compute_triage_weight(mes.frame_id, triage_result)
            if w_triage < 1.0:
                w *= w_triage
                print(f"[MES-Weight] {mes.frame_id[:8]}: triage_penalty applied (w_triage={w_triage:.2f})")
        except ImportError:
            pass  # VLM triage not available
        
        weights[mes.frame_id] = max(w, MES_WEIGHT_FLOOR)
    
    # Normalize so weights sum to 1.0
    total = sum(weights.values())
    if total > 0:
        weights = {k: v / total for k, v in weights.items()}
    
    # Log weights
    for fid, w in weights.items():
        print(f"[MES-Weight] {fid[:8]}: w={w:.3f}")
    
    return weights




def _log_mes(mes: MeasurementEvidenceScore, job_consensus: float = 0.0):
    """v6.5: Log MES breakdown for debugging."""
    status = "EXCLUDED" if mes.hard_excluded else "ELIGIBLE"
    reason = f" ({mes.exclusion_reason})" if mes.exclusion_reason else ""
    
    print(f"[MES] {mes.frame_id[:8]}:")
    print(f"  - geometry={mes.geometry_score:.2f} (inlier={mes.inlier_ratio:.2f}, "
          f"noise_ratio={mes.noise_ratio:.2f}, angle={mes.plane_angle_deg:.1f}°)")
    print(f"  - completeness={mes.completeness_score:.2f} (border={mes.border_touch_ratio:.2f})")
    print(f"  - height={mes.height_score:.2f} (p95={mes.height_p95_m:.2f}m, consensus={job_consensus:.2f}m)")
    print(f"  - semantic={mes.semantic_score:.2f} (removed={mes.semantic_removed_pct:.0%})")
    print(f"  - raw_score={mes.raw_score:.2f} → {status}{reason}")


def get_shape_factor(
    pile_type: str = "household",
    pile_density: str = "loose",
    density_confidence: str = "medium",
    pile_touches_background: bool = False,
    veg_overlap_high: bool = False
) -> float:
    """
    Compute shape factor with guardrails.
    
    Args:
        pile_type: Type of pile (household, yard_waste, construction, mixed)
        pile_density: Density classification (solid, loose, sparse)
        density_confidence: Confidence in density call (high, medium, low)
        pile_touches_background: Whether pile merges with background
        veg_overlap_high: Whether vegetation overlap is high
        
    Returns:
        Shape factor between 0.55 and 0.95
    """
    # GUARDRAIL 1: Yard waste uses fixed 0.65 (leaves/debris have lots of air)
    if pile_type == "yard_waste":
        return 0.65
    
    # Base factor from density
    factor = DENSITY_FACTORS.get(pile_density, SHAPE_FACTOR_DEFAULT)
    
    # GUARDRAIL 2: Confidence damping
    if density_confidence == "low":
        factor = SHAPE_FACTOR_DEFAULT  # Force to 0.85
    elif density_confidence == "medium":
        # Blend toward default: factor = default + (factor - default) * 0.5
        factor = SHAPE_FACTOR_DEFAULT + (factor - SHAPE_FACTOR_DEFAULT) * 0.5
    # high confidence: use full factor
    
    # GUARDRAIL 3: Background/veg risk → cap at 0.85
    if pile_touches_background or veg_overlap_high:
        factor = min(factor, 0.85)
    
    # Hard clamp to valid range
    factor = max(0.55, min(0.95, factor))
    
    return factor

@dataclass
class RoleQualification:
    """Per-frame qualification for footprint and height donor roles."""
    frame_id: str
    
    # Gate results
    passes_geometry_gate: bool = False
    passes_seg_gate: bool = False      # For footprint role
    passes_height_gate: bool = False   # For height role
    
    # Role qualification (derived from gates)
    qualified_footprint: bool = False   # Can donate footprint
    qualified_height: bool = False      # Can donate height
    
    # Extracted attributes
    footprint_m2: float = 0.0
    height_p85_m: float = 0.0
    height_p95_m: float = 0.0             # v10.7: P95 height for geometry noise ratio
    mean_height_m: float = 0.0
    floor_area_pct: float = 0.0
    
    # Quality metrics (for clean frame selection)
    ground_overlap_ratio: float = 0.0   # Lower is cleaner
    mask_coverage: float = 0.0          # Lower is usually cleaner
    
    # Fix 4: Additional quality metrics for continuous weighting
    inlier_ratio: float = 0.0           # RANSAC inlier ratio
    yfl95: float = 0.0                  # Floor flatness P95
    plane_angle_deg: float = 0.0        # Ground plane tilt angle
    
    # Gate failure reasons
    geometry_fail_reason: Optional[str] = None
    seg_fail_reason: Optional[str] = None
    height_fail_reason: Optional[str] = None
    
    # Soft scores (for ranking among qualified frames)
    footprint_score: float = 0.0
    height_score: float = 0.0
    continuous_weight: float = 1.0       # Computed weight for this frame
    
    # v6.4.1: Additional tracking fields
    geometry_valid: bool = False          # RANSAC valid + spread_pass
    semantic_removed_pct: float = 0.0     # % of mask removed by semantic filter
    skirt_ratio: float = 0.0              # Fraction of near-floor cells
    border_touch_ratio: float = 0.0       # Fraction of mask touching border
    partial_view: bool = False            # Severe partial (exclude from trusted-max)
    partial_view_soft: bool = False       # Moderate partial (reduce weight)
    frame_volume_cy: float = 0.0          # Volume for this frame
    
    # v8.5.2: Support-plane metrics (replace yfl95 for donor eligibility when available)
    support_plane_selected: bool = False  # Was a support plane successfully selected?
    sr_inlier_ratio: float = 0.0          # Support ROI inlier ratio
    sr_yfl95: float = 0.20                # Support ROI residual P95 (meters)
    
    # v8.6: Guardrail quarantine flag
    donor_eligible: bool = True           # If False, frame is rescued but quarantined (cannot be V_ref or donor)
    
    # v10.4: Intrinsics mismatch gating (bundle_fx / depthpro_fx)
    intrinsics_fx_ratio: Optional[float] = None  # ratio or None if no bundle
    intrinsics_derived: bool = False       # True if bundle was derived/fallback


def _check_geometry_gate(
    inlier_ratio: float,
    yfl95: float,
    tilt_deg: float = 0.0,
    # v8.5.3: Support-plane bypass
    support_plane_selected: bool = False,
    sr_inlier_ratio: float = 0.0,
    sr_yfl95: float = 0.20
) -> tuple[bool, Optional[str]]:
    """
    Geometry gate: Check if floor plane is reliable.
    Must pass ALL conditions.
    
    v8.5.3: When support_plane_selected=True, uses sr_yfl95 instead of global yfl95.
    
    Returns: (passes, failure_reason)
    """
    # v8.5.3: Support-plane branch - use sr_inlier_ratio and sr_yfl95
    SR_INLIER_MIN = 0.70
    SR_YFL95_MAX = 0.15
    
    if support_plane_selected:
        # Support plane branch: use support-plane metrics
        if sr_inlier_ratio < SR_INLIER_MIN:
            return False, f"sr_inlier={sr_inlier_ratio:.2f}<{SR_INLIER_MIN}"
        if sr_yfl95 > SR_YFL95_MAX:
            return False, f"sr_yfl95={sr_yfl95:.2f}>{SR_YFL95_MAX}"
    else:
        # Legacy branch: use global metrics
        if inlier_ratio < GATE_INLIER_RATIO_MIN:
            return False, f"inlier_ratio={inlier_ratio:.2f}<{GATE_INLIER_RATIO_MIN}"
        if yfl95 > GATE_YFL95_MAX:
            return False, f"Yfl95={yfl95:.2f}>{GATE_YFL95_MAX}"
    
    if tilt_deg > GATE_TILT_DEG_MAX:
        return False, f"tilt={tilt_deg:.1f}°>{GATE_TILT_DEG_MAX}°"
    
    return True, None


def _check_seg_gate(
    mask_coverage: float,
    ground_overlap_ratio: float = 0.0
) -> tuple[bool, Optional[str]]:
    """
    Segmentation gate: Check if mask is not a leak.
    For footprint donor qualification.
    
    A mask_coverage > 50% is only allowed if ground_overlap is low
    (meaning it's a legitimately large pile, not a leak onto ground).
    
    Returns: (passes, failure_reason)
    """
    if mask_coverage > GATE_MASK_COVERAGE_MAX:
        # High coverage - check if it's a leak (includes ground)
        if ground_overlap_ratio > GATE_GROUND_OVERLAP_MAX:
            return False, f"mask_leak: coverage={mask_coverage:.1%}, ground_overlap={ground_overlap_ratio:.1%}"
        # High coverage but low ground overlap - might be legit large pile
        # Still flag but allow with warning
        print(f"[Gate] Warning: high mask coverage ({mask_coverage:.1%}) but low ground overlap - allowing")
    
    return True, None


def _check_height_gate(
    y_junk_max: float,
    inlier_ratio: float = 1.0,
    yfl95: float = 0.0,
    scene_type: str = "unknown",
    # v8.5.3: Support-plane bypass
    support_plane_selected: bool = False,
    sr_inlier_ratio: float = 0.0,
    sr_yfl95: float = 0.20
) -> tuple[bool, Optional[str]]:
    """
    Height gate: Check if height data is reliable for height donor role.
    Uses stricter thresholds than general geometry gate.
    
    Fix 2: Scene-aware YFL95 thresholds.
    v8.5.3: When support_plane_selected=True, uses sr_yfl95 instead of scene-specific yfl95.
    
    Returns: (passes, failure_reason)
    """
    # v8.5.3: Support-plane thresholds
    SR_INLIER_MIN = 0.70
    SR_YFL95_MAX = 0.15
    
    # Height must be meaningful
    if y_junk_max < GATE_HEIGHT_MIN_M:
        return False, f"height_compressed: Y_max={y_junk_max:.2f}m<{GATE_HEIGHT_MIN_M}m"
    
    # v8.5.3: Support-plane branch - use sr_inlier_ratio and sr_yfl95
    if support_plane_selected:
        if sr_inlier_ratio < SR_INLIER_MIN:
            return False, f"sr_inlier={sr_inlier_ratio:.2f}<{SR_INLIER_MIN}"
        if sr_yfl95 > SR_YFL95_MAX:
            return False, f"sr_yfl95={sr_yfl95:.2f}>{SR_YFL95_MAX}"
    else:
        # Legacy branch: use global metrics with scene-specific thresholds
        if inlier_ratio < GATE_INLIER_RATIO_FOR_HEIGHT:
            return False, f"height_inlier={inlier_ratio:.2f}<{GATE_INLIER_RATIO_FOR_HEIGHT}"
        
        yfl95_threshold = GATE_YFL95_BY_SCENE.get(scene_type, GATE_YFL95_DEFAULT)
        if yfl95 > yfl95_threshold:
            return False, f"height_yfl95={yfl95:.3f}>{yfl95_threshold} (scene={scene_type})"
    
    return True, None


def _get_continuous_weight(
    floor_quality: str,
    inlier_ratio: float,
    yfl95: float,
    plane_angle_deg: float,
    mask_coverage: float,
    ground_overlap_ratio: float,
    border_touch_ratio: float = 0.0,
    skirt_ratio: float = 0.0,
    geometry_valid: bool = True,       # v6.4.1: for floor eligibility
    apply_evidence_floor: bool = True  # v6.4.1: enable dynamic floor
) -> float:
    """
    Fix 4 + S3 + v6.4.1: Continuous weight based on multiple quality signals.
    
    Factors:
    - Base weight from floor_quality label
    - Inlier factor: higher is better (0.95+ = full weight)
    - Noise factor: lower is better (0.05 or less = full weight)
    - Angle factor: <12° = full, 12-20° = decaying, >20° = 0
    - Mask factor: high coverage + high ground overlap = leaky mask penalty
    - S3 Leakage factor: border-touch and skirt penalties
    - v6.4.1 Dynamic evidence floor: 0.22-0.32 for good+stable frames
    
    Returns: Weight in range [0.1, 1.0]
    """
    if floor_quality == "failed":
        return 0.1  # Near-zero for failed floors
    
    # Base weight from quality label
    base = 1.0 if floor_quality == "good" else 0.75
    
    # Inlier factor: 0.95+ gets full weight
    inlier_factor = min(1.0, inlier_ratio / 0.95)
    
    # Noise factor: lower is better (0.05 or less = full weight)
    noise_factor = max(0.5, 1.0 - (yfl95 / 0.10))
    
    # Angle factor: <12° = full weight, 12-20° = decaying, >20° = 0
    angle_factor = max(0.0, min(1.0, (20.0 - plane_angle_deg) / 8.0))
    
    # v8.7: CONTINUOUS MASK FACTOR (no step-function cliff)
    # Ramp: mask_coverage 0.40 → 0.65 linearly decays from 1.0 → 0.3
    # Also considers ground_overlap as a secondary factor
    def _linear_ramp(value, low, high, low_out=1.0, high_out=0.0):
        """Linear interpolation between two output values."""
        if value <= low: return low_out
        if value >= high: return high_out
        t = (value - low) / (high - low)
        return low_out + (high_out - low_out) * t
    
    # Mask coverage penalty: 0.40 safe, 0.65 heavily penalized
    mask_coverage_factor = _linear_ramp(mask_coverage, 0.40, 0.65, 1.0, 0.4)
    
    # Ground overlap penalty: 0.10 safe, 0.30 heavily penalized
    overlap_factor = _linear_ramp(ground_overlap_ratio, 0.10, 0.30, 1.0, 0.5)
    
    # Combined mask factor: use worse of the two (multiplicative would be too harsh)
    mask_factor = min(mask_coverage_factor, overlap_factor) * max(mask_coverage_factor, overlap_factor) ** 0.3
    mask_factor = max(0.3, mask_factor)  # Floor at 0.3
    
    # v8.7: CONTINUOUS LEAKAGE FACTOR (no step-function cliff)
    # Border-touch ramp: 0.02 safe, 0.10 heavily penalized
    border_ramp = _linear_ramp(border_touch_ratio, 0.02, 0.10, 1.0, 0.5)
    
    # Skirt ratio ramp: only applies when border-touch is elevated
    skirt_ramp = 1.0
    if border_touch_ratio > 0.03:  # Skirt only matters if some border contamination
        skirt_ramp = _linear_ramp(skirt_ratio, 0.05, 0.15, 1.0, 0.6)
    
    leakage_factor = border_ramp * skirt_ramp
    
    # S3: Floor at 0.35 to avoid nuking frames
    leakage_factor = max(leakage_factor, LEAKAGE_FACTOR_FLOOR)

    
    weight = base * inlier_factor * noise_factor * angle_factor * mask_factor * leakage_factor
    
    # v6.4.1: Dynamic evidence floor for good+stable frames
    floor_applied = False
    if apply_evidence_floor:
        leakage_severe = (
            border_touch_ratio > BORDER_TOUCH_HEAVY or
            (border_touch_ratio > BORDER_TOUCH_MODERATE and skirt_ratio > SKIRT_RATIO_THRESHOLD)
        )
        
        floor_eligible = (
            floor_quality == "good" and
            inlier_ratio >= EVIDENCE_FLOOR_INLIER_MIN and
            plane_angle_deg <= EVIDENCE_FLOOR_PLANE_MAX and
            yfl95 <= EVIDENCE_FLOOR_YFL95_MAX and
            geometry_valid and
            not leakage_severe
        )
        
        if floor_eligible and weight < EVIDENCE_FLOOR_MAX:
            # Dynamic floor: 0.22 at inlier=0.65, 0.32 at inlier=0.90
            t = min(1.0, max(0.0, (inlier_ratio - EVIDENCE_FLOOR_INLIER_MIN) / 0.25))
            dynamic_floor = EVIDENCE_FLOOR_BASE + (EVIDENCE_FLOOR_MAX - EVIDENCE_FLOOR_BASE) * t
            if weight < dynamic_floor:
                weight = dynamic_floor
                floor_applied = True
    
    # Clamp to valid range
    return max(0.1, min(1.0, weight))



def _compute_height_p85(grid_cells: list) -> float:
    """
    Compute P85 (85th percentile) of cell heights.
    More robust than mean - ignores low 'skirt' cells.
    """
    heights = [c.trimmed_height for c in grid_cells if c.trimmed_height > 0]
    if not heights:
        return 0.0
    return float(np.percentile(heights, 85))


def _compute_ground_overlap_ratio(
    grid_cells: list,
    floor_noise_m: float = 0.10
) -> float:
    """
    Compute what fraction of mask cells are at ground level.
    
    High ratio = mask likely leaked onto floor.
    Low ratio = mask is elevated (actual pile).
    """
    if not grid_cells:
        return 0.0
    
    total_cells = len(grid_cells)
    ground_level_cells = sum(1 for c in grid_cells if c.trimmed_height < floor_noise_m)
    
    return ground_level_cells / total_cells


# =============================================================================
# S1: UNION-BLEND FOR COMPLEMENTARY VIEWS
# =============================================================================

def _weighted_percentile(values: list[float], weights: list[float], pct: int) -> float:
    """
    Compute weighted percentile (50=median, 85=P85).
    
    Args:
        values: List of values
        weights: Corresponding weights
        pct: Percentile (0-100)
        
    Returns:
        Weighted percentile value
    """
    if not values or not weights:
        return 0.0
    
    # Sort by value
    sorted_pairs = sorted(zip(values, weights), key=lambda x: x[0])
    cumsum = np.cumsum([w for _, w in sorted_pairs])
    total = cumsum[-1]
    
    if total == 0:
        return sorted_pairs[len(sorted_pairs) // 2][0]  # Fallback to unweighted median
    
    target = total * (pct / 100.0)
    for i, (v, _) in enumerate(sorted_pairs):
        if cumsum[i] >= target:
            return v
    return sorted_pairs[-1][0]


def _weighted_trimmed_mean(volumes: list[float], weights: list[float], trim_pct: float = 0.1) -> float:
    """
    Compute weighted trimmed mean with normalized weights.
    
    S2: Uses normalized weights (sum to 1.0) for consistency.
    """
    if not volumes or not weights:
        return 0.0
    
    n = len(volumes)
    if n == 1:
        return volumes[0]
    
    # S2: Normalize weights with floor
    weights = [max(w, WEIGHT_FLOOR) for w in weights]
    total_w = sum(weights)
    if total_w > 0:
        weights = [w / total_w for w in weights]
    
    # Sort by volume
    sorted_pairs = sorted(zip(volumes, weights), key=lambda x: x[0])
    
    # Trim extremes (drop lowest and highest if enough samples)
    trim_count = max(0, int(n * trim_pct))
    if n > 2 and trim_count > 0:
        sorted_pairs = sorted_pairs[trim_count:-trim_count]
    
    # Weighted mean of remaining
    numerator = sum(v * w for v, w in sorted_pairs)
    denominator = sum(w for _, w in sorted_pairs)
    
    return numerator / denominator if denominator > 0 else 0.0


def _compute_union_blend(
    volumes: list[float],
    weights: list[float],
    trusted_max_volume: float = 0.0,     # v6.4.1: trusted-max for cap
    trusted_frame_id: Optional[str] = None,
    coverage_evidence: bool = False       # v10.5: require evidence of complementary views
) -> tuple[float, bool]:
    """
    S1 + v6.4.1 + v10.5: Compute union-blend when complementary views detected.
    
    v10.5: Now requires coverage_evidence=True to trigger, not just ratio.
    Overlapping views (coverage_evidence=False) use weighted_trimmed_mean.
    
    Returns: (volume, was_triggered). Always returns valid float.
    """
    # Always compute baseline (needed for return)
    V_base = _weighted_trimmed_mean(volumes, weights)
    
    if len(volumes) < 3:
        return V_base, False
    
    V_sum = sum(volumes)
    V_wmed = _weighted_percentile(volumes, weights, 50)  # Weighted median
    
    ratio = V_sum / V_wmed if V_wmed > 0 else 0
    
    # v10.5: Require BOTH ratio threshold AND coverage evidence
    ratio_met = ratio > COMPLEMENT_RATIO_THRESHOLD
    triggered = ratio_met and coverage_evidence
    
    if not triggered:
        if ratio_met and not coverage_evidence:
            print(f"[UnionBlend] NOT triggered: ratio={ratio:.1f}x but coverage_evidence=False (overlapping views)")
        return V_base, False
    
    # v6.4.1: Use trusted-max if available, else fall back to P85
    if trusted_max_volume > 0:
        V_ref = trusted_max_volume
        V_union = min(V_sum, V_ref * UNION_CAP_MULTIPLIER_TRUSTED)  # 1.15
        print(f"[UnionBlend] Using trusted-max V_ref={V_ref:.2f} "
              f"(frame={trusted_frame_id[:8] if trusted_frame_id else 'none'})")
    else:
        V_ref = _weighted_percentile(volumes, weights, 85)  # P85 fallback
        V_union = min(V_sum, V_ref * UNION_CAP_MULTIPLIER)  # 1.35
        print(f"[UnionBlend] Fallback to P85 V_ref={V_ref:.2f} (no trusted frame)")
    
    # Blend
    V_final = BLEND_BASE_WEIGHT * V_base + BLEND_UNION_WEIGHT * V_union
    
    # Evidence envelope clamp
    V_final = min(V_final, V_ref * ENVELOPE_CAP_MULTIPLIER)
    V_final = max(V_final, V_wmed * 0.85)
    
    print(f"[UnionBlend] ratio={ratio:.1f}x, V_base={V_base:.2f}, "
          f"V_union={V_union:.2f}, V_final={V_final:.2f}")
    
    return V_final, True


def _get_trusted_max_volume(
    role_qualifications: list,
    valid_frame_ids: set
) -> tuple[float, Optional[str]]:
    """
    v6.4.1: Find max volume among frames meeting tight trust criteria.
    
    Criteria:
    - geometry_valid = True
    - continuous_weight >= TRUSTED_MAX_WEIGHT_MIN
    - mask_coverage <= TRUSTED_MAX_MASK_COV_MAX
    - skirt_ratio <= TRUSTED_MAX_SKIRT_MAX
    - plane_angle_deg <= TRUSTED_MAX_PLANE_ANGLE_MAX
    - semantic_removed_pct <= TRUSTED_MAX_SEM_REMOVED_MAX
    - Not marked as severe partial_view
    
    Returns: (trusted_max_volume, trusted_frame_id) or (0.0, None) if none qualify
    """
    trusted_max = 0.0
    trusted_frame = None
    
    for rq in role_qualifications:
        if rq.frame_id not in valid_frame_ids:
            continue
        
        # Strict eligibility checks
        eligible = True
        reasons = []
        
        if not rq.geometry_valid:
            eligible = False
            reasons.append("geometry_invalid")
        if rq.continuous_weight < TRUSTED_MAX_WEIGHT_MIN:
            eligible = False
            reasons.append(f"weight={rq.continuous_weight:.2f}<{TRUSTED_MAX_WEIGHT_MIN}")
        if rq.mask_coverage > TRUSTED_MAX_MASK_COV_MAX:
            eligible = False
            reasons.append(f"mask_cov={rq.mask_coverage:.0%}>{TRUSTED_MAX_MASK_COV_MAX:.0%}")
        if rq.skirt_ratio > TRUSTED_MAX_SKIRT_MAX:
            eligible = False
            reasons.append(f"skirt={rq.skirt_ratio:.2f}>{TRUSTED_MAX_SKIRT_MAX}")
        if rq.plane_angle_deg > TRUSTED_MAX_PLANE_ANGLE_MAX:
            eligible = False
            reasons.append(f"angle={rq.plane_angle_deg:.1f}>{TRUSTED_MAX_PLANE_ANGLE_MAX}")
        if rq.semantic_removed_pct > TRUSTED_MAX_SEM_REMOVED_MAX:
            eligible = False
            reasons.append(f"sem_removed={rq.semantic_removed_pct:.0%}>{TRUSTED_MAX_SEM_REMOVED_MAX:.0%}")
        if rq.partial_view:
            eligible = False
            reasons.append("partial_view=severe")
        
        # v6.9.0: VLM Triage vref_ok gating (if triage available)
        if triage_result and triage_result.triage_available:
            frame_roles = triage_result.frame_roles.get(rq.frame_id)
            if frame_roles and not frame_roles.vref_ok:
                eligible = False
                reasons.append(f"triage_vref_blocked:{','.join(frame_roles.reason_codes[:2])}")
        
        if eligible:
            print(f"[TrustedMax] {rq.frame_id[:8]}: ELIGIBLE, vol={rq.frame_volume_cy:.2f}")
            if rq.frame_volume_cy > trusted_max:
                trusted_max = rq.frame_volume_cy
                trusted_frame = rq.frame_id
        else:
            print(f"[TrustedMax] {rq.frame_id[:8]}: NOT eligible ({', '.join(reasons[:2])})")
    
    return trusted_max, trusted_frame


def _get_trusted_max_volume_v65(
    mes_scores: list,
    role_qualifications: list,
    valid_frame_ids: set
) -> tuple[float, Optional[str]]:
    """
    v6.5.2: Find max volume among MES-qualified frames WITH floor quality gate.
    
    V_ref Quality Gate (Step 1 of stability fix):
    - MES-based eligibility
    - inlier_ratio >= 0.75 (geometry must be good)
    - Y_floor_p95 <= 0.15 (floor must be flat)
    - Not partial_view=severe
    
    v10.3 FIX B: Footprint-consensus gating
    - Only frames with footprint within [0.8×fp_median, 1.2×fp_median] can be V_ref
    - Prevents inflated frames from being selected
    
    Returns: (trusted_max_volume, trusted_frame_id) or (0.0, None) if none qualify
    """
    # V_ref gate thresholds (v6.5.2b: tightened per user feedback)
    VREF_INLIER_MIN = 0.50  # v8.2.2: Relaxed from 0.70 - reference frame
    VREF_YFL95_MAX = 0.30   # v8.2.2: Relaxed from 0.20 - match GATE2 hard exclusion
    
    # v10.3: Footprint consensus thresholds
    FP_CONSENSUS_LOW = 0.80   # Min ratio to median
    FP_CONSENSUS_HIGH = 1.20  # Max ratio to median
    
    trusted_max = 0.0
    trusted_frame = None
    v_ref_candidates = []  # For logging
    
    # Build lookup for MES scores
    mes_lookup = {m.frame_id: m for m in mes_scores}
    
    # v10.3: Compute footprint median for consensus check
    valid_footprints = []
    for rq in role_qualifications:
        if rq.frame_id in valid_frame_ids and rq.footprint_m2 > 0:
            valid_footprints.append(rq.footprint_m2)
    
    if valid_footprints:
        fp_median = np.median(valid_footprints)
        fp_low_threshold = fp_median * FP_CONSENSUS_LOW
        fp_high_threshold = fp_median * FP_CONSENSUS_HIGH
        print(f"[VRef_FP] Footprint consensus: median={fp_median:.2f}m², band=[{fp_low_threshold:.2f}, {fp_high_threshold:.2f}]")
    else:
        fp_median = 0.0
        fp_low_threshold = 0.0
        fp_high_threshold = float('inf')
    
    for rq in role_qualifications:
        if rq.frame_id not in valid_frame_ids:
            continue
        
        mes = mes_lookup.get(rq.frame_id)
        if not mes:
            print(f"[TrustedMax] {rq.frame_id[:8]}: NOT eligible (no MES)")
            continue
        
        eligible = True
        reasons = []
        
        # Unified MES-based eligibility
        if mes.hard_excluded:
            eligible = False
            reasons.append(mes.exclusion_reason or "hard_excluded")
        elif mes.raw_score < TRUSTED_MAX_MES_MIN:
            eligible = False
            reasons.append(f"mes={mes.raw_score:.2f}<{TRUSTED_MAX_MES_MIN}")
        
        # v6.5.2: V_ref Quality Gate - floor must be good
        if rq.inlier_ratio < VREF_INLIER_MIN:
            eligible = False
            reasons.append(f"inlier={rq.inlier_ratio:.2f}<{VREF_INLIER_MIN}")
        
        # v8.5.3: Support-plane bypass for yfl95 gate
        # When support plane is valid (sr_yfl95 <= 0.15), global yfl95 is noise not validity signal
        SR_YFL95_THRESHOLD = 0.15
        if rq.support_plane_selected and rq.sr_yfl95 <= SR_YFL95_THRESHOLD:
            pass  # Support plane is valid - bypass global yfl95 check
        elif rq.yfl95 > VREF_YFL95_MAX:
            eligible = False
            reasons.append(f"yfl95={rq.yfl95:.2f}>{VREF_YFL95_MAX}")
        
        # Keep partial_view exclusion (severe only)
        if rq.partial_view:
            eligible = False
            reasons.append("partial_view=severe")
        
        # v6.8.0 Fix B: Sem-damaged frames cannot be V_ref
        if rq.semantic_removed_pct > TRUSTED_MAX_SEM_REMOVED_MAX:
            eligible = False
            reasons.append(f"sem={rq.semantic_removed_pct:.0%}>{TRUSTED_MAX_SEM_REMOVED_MAX:.0%}")
            
        # v8.6: Guardrail quarantine check
        if not rq.donor_eligible:
            eligible = False
            reasons.append("donor_quarantined")
        
        # v10.3 FIX B: FOOTPRINT CONSENSUS CHECK
        # Only allow V_ref from frames within footprint consensus band
        if fp_median > 0 and rq.footprint_m2 > 0:
            fp_ratio = rq.footprint_m2 / fp_median
            if fp_ratio < FP_CONSENSUS_LOW:
                eligible = False
                reasons.append(f"fp_low={fp_ratio:.2f}<{FP_CONSENSUS_LOW}")
            elif fp_ratio > FP_CONSENSUS_HIGH:
                eligible = False
                reasons.append(f"fp_high={fp_ratio:.2f}>{FP_CONSENSUS_HIGH}")
        
        # v10.4: Intrinsics mismatch gating (>25% deviation excludes from V_ref)
        fx_ratio = getattr(rq, 'intrinsics_fx_ratio', None)
        fx_derived = getattr(rq, 'intrinsics_derived', False)
        if fx_ratio is not None and not fx_derived:  # Only penalize if bundle was not derived
            deviation = abs(fx_ratio - 1.0)
            if deviation > 0.25:
                eligible = False
                reasons.append(f"intrinsics_mismatch={deviation:.0%}>25%")
        
        # Log candidate for debugging
        v_ref_candidates.append({
            'frame_id': rq.frame_id[:8],
            'vol': rq.frame_volume_cy,
            'fp': rq.footprint_m2,
            'inlier': rq.inlier_ratio,
            'yfl95': rq.yfl95,
            'eligible': eligible,
            'reason': ', '.join(reasons[:2]) if reasons else 'ok'
        })
        
        if eligible:
            print(f"[TrustedMax] {rq.frame_id[:8]}: ELIGIBLE (mes={mes.raw_score:.2f}, fp={rq.footprint_m2:.2f}m²), vol={rq.frame_volume_cy:.2f}")
            if rq.frame_volume_cy > trusted_max:
                trusted_max = rq.frame_volume_cy
                trusted_frame = rq.frame_id
        else:
            print(f"[TrustedMax] {rq.frame_id[:8]}: NOT eligible ({', '.join(reasons[:2])})")
    
    # Log V_ref candidates summary
    print(f"[VRef_DEBUG] Candidates: {v_ref_candidates}")
    if trusted_frame:
        print(f"[VRef_DEBUG] Selected: {trusted_frame[:8]} (vol={trusted_max:.2f})")
    else:
        print(f"[VRef_DEBUG] No frame qualified for V_ref (will use fallback)")
    
    return trusted_max, trusted_frame





def _qualify_frame_for_roles(
    frame_id: str,
    volumetric_result,
    inlier_ratio: float,
    yfl95: float,
    mask_coverage: float,
    floor_area_pct: float = 0.0,
    tilt_deg: float = 0.0,
    scene_type: str = "unknown",
    floor_quality: str = "unknown",
    # v8.5.3: Support-plane metrics for gate bypass
    support_plane_selected: bool = False,
    sr_inlier_ratio: float = 0.0,
    sr_yfl95: float = 0.20,
    # v8.6: Guardrail quarantine
    donor_eligible: bool = True,
    # v10.4: Intrinsics mismatch gating
    intrinsics_fx_ratio: Optional[float] = None,
    intrinsics_derived: bool = False
) -> RoleQualification:
    """
    Qualify a frame for footprint and/or height donor roles.
    
    A frame can be qualified for:
    - Footprint: passes geometry + seg gates
    - Height: passes geometry + height gates (with stricter thresholds)
    - Both, one, or neither
    
    Also computes continuous weight for fusion weighting (Fix 4).
    """
    rq = RoleQualification(frame_id=frame_id)
    rq.floor_area_pct = floor_area_pct
    
    # Store quality metrics for continuous weighting (Fix 4)
    rq.inlier_ratio = inlier_ratio
    rq.yfl95 = yfl95
    rq.plane_angle_deg = tilt_deg
    
    # v10.4: Store intrinsics mismatch info
    rq.intrinsics_fx_ratio = intrinsics_fx_ratio
    rq.intrinsics_derived = intrinsics_derived
    
    # === v10.7: Use canonical metrics from volumetrics (authoritative source) ===
    # This replaces proxy calculations that diverged from what volumetrics actually integrated
    if volumetric_result and volumetric_result.height_field_valid:
        # Footprint and height from canonical metrics
        rq.footprint_m2 = volumetric_result.footprint_m2_selected
        rq.height_p85_m = volumetric_result.height_p85_footprint
        rq.height_p95_m = volumetric_result.height_p95_footprint
        rq.mean_height_m = volumetric_result.mean_height_footprint
        
        # Ground overlap replaced by leak_ratio_maskseed
        ground_overlap = volumetric_result.leak_ratio_maskseed
        
        # Skirt ratio from canonical (for trusted-max/leakage weighting)
        rq.skirt_ratio = volumetric_result.skirt_ratio_selected
        
        # Get Y_junk_max for height gate (still need max from grid cells)
        grid_cells = volumetric_result.grid_cells
        y_junk_max = max((c.trimmed_height for c in grid_cells), default=0.0)
    else:
        # Fallback for missing volumetric result
        grid_cells = []
        rq.footprint_m2 = 0.0
        rq.height_p85_m = 0.0
        rq.height_p95_m = 0.0
        rq.mean_height_m = 0.0
        ground_overlap = 0.0
        rq.skirt_ratio = 0.0
        y_junk_max = 0.0
    
    # Store quality metrics for clean frame selection
    rq.ground_overlap_ratio = ground_overlap
    rq.mask_coverage = mask_coverage
    
    # === Check Geometry Gate (applies to both roles) ===
    # v8.5.3: Pass support-plane metrics for gate bypass
    rq.passes_geometry_gate, rq.geometry_fail_reason = _check_geometry_gate(
        inlier_ratio, yfl95, tilt_deg,
        support_plane_selected=support_plane_selected,
        sr_inlier_ratio=sr_inlier_ratio,
        sr_yfl95=sr_yfl95
    )
    
    # === Check Seg Gate (footprint role) ===
    rq.passes_seg_gate, rq.seg_fail_reason = _check_seg_gate(
        mask_coverage, ground_overlap
    )
    
    # === Check Height Gate (height role) - Fix 2: Scene-aware, stricter ===
    # v8.5.3: Pass support-plane metrics for gate bypass
    rq.passes_height_gate, rq.height_fail_reason = _check_height_gate(
        y_junk_max=y_junk_max,
        inlier_ratio=inlier_ratio,
        yfl95=yfl95,
        scene_type=scene_type,
        support_plane_selected=support_plane_selected,
        sr_inlier_ratio=sr_inlier_ratio,
        sr_yfl95=sr_yfl95
    )
    
    # === Determine Role Qualification ===
    # v8.6: Guardrail quarantine - ineligible donors cannot lead
    rq.donor_eligible = donor_eligible
    rq.qualified_footprint = rq.passes_geometry_gate and rq.passes_seg_gate and donor_eligible
    rq.qualified_height = rq.passes_geometry_gate and rq.passes_height_gate and donor_eligible
    
    # v6.4.1: Track geometry validity for trusted-max eligibility
    rq.geometry_valid = rq.passes_geometry_gate
    
    # === Compute Continuous Weight (Fix 4 + v6.4.1 dynamic floor) ===
    rq.continuous_weight = _get_continuous_weight(
        floor_quality=floor_quality,
        inlier_ratio=inlier_ratio,
        yfl95=yfl95,
        plane_angle_deg=tilt_deg,
        mask_coverage=mask_coverage,
        ground_overlap_ratio=ground_overlap,
        geometry_valid=rq.geometry_valid,        # v6.4.1
        apply_evidence_floor=True                # v6.4.1
    )
    
    # Log qualification
    # v8.5.3: Show sr_yfl95 when support plane is selected to avoid confusion
    fp_status = "✓" if rq.qualified_footprint else f"✗ ({rq.geometry_fail_reason or rq.seg_fail_reason})"
    h_status = "✓" if rq.qualified_height else f"✗ ({rq.geometry_fail_reason or rq.height_fail_reason})"
    sp_tag = f"SP(sr={sr_inlier_ratio:.2f},p95={sr_yfl95:.2f})" if support_plane_selected else f"GP(yfl95={yfl95:.2f})"
    print(f"[RoleQual] {frame_id[:8]}: {sp_tag} footprint={fp_status}, height={h_status}, w={rq.continuous_weight:.2f}")
    
    return rq



def _extract_centroid(grid_cells: list) -> tuple[float, float]:
    """Extract approximate centroid from grid cells."""
    if not grid_cells:
        return 0.0, 0.0
        
    xs = [c.x_m for c in grid_cells if c.trimmed_height > 0]
    zs = [c.z_m for c in grid_cells if c.trimmed_height > 0]
    
    if not xs:
        return 0.0, 0.0
        
    return np.mean(xs), np.mean(zs)


def _check_viewpoint_diversity(
    frame_results: list[tuple[VolumetricResult, tuple[float, float]]]
) -> tuple[bool, str]:
    """Check if camera viewpoints are diverse enough."""
    if len(frame_results) < 2:
        return False, "single_view"
        
    centroids = [c for _, c in frame_results]
    
    max_distance = 0.0
    for i in range(len(centroids)):
        for j in range(i + 1, len(centroids)):
            dx = centroids[i][0] - centroids[j][0]
            dz = centroids[i][1] - centroids[j][1]
            dist = np.sqrt(dx*dx + dz*dz)
            max_distance = max(max_distance, dist)
    
    avg_volume = np.mean([r.frame_volume_cy for r, _ in frame_results])
    expected_extent = avg_volume ** (1/3)
    
    if expected_extent > 0:
        normalized_movement = max_distance / expected_extent
    else:
        normalized_movement = 0.0
        
    is_diverse = normalized_movement > 0.15
    diversity = "good" if is_diverse else "low"
    
    return is_diverse, diversity


def _merge_discrete_items(all_items: list[list[DiscreteItem]]) -> list[DiscreteItem]:
    """Merge discrete items across views, deduplicating by label."""
    label_map = {}
    
    for frame_items in all_items:
        for item in frame_items:
            key = item.label.lower().strip()
            
            if key not in label_map:
                label_map[key] = item
            elif item.confidence > label_map[key].confidence:
                label_map[key] = item
    
    return list(label_map.values())


def _is_catastrophic(
    floor_quality: str,
    floor_flatness_p95: float,
    inlier_ratio: float,
    depth_confidence: float,
    support_plane_selected: bool = False  # v8.5: bypass yfl95 hard-fail when True
) -> tuple[bool, str]:
    """
    Check if a frame should be catastrophically dropped.
    Returns (is_catastrophic, reason).
    
    v8.5: When support_plane_selected=True, yfl95 becomes a confidence penalty
    instead of a hard-fail. This handles grass/lawn surfaces which have
    higher depth texture noise than driveways but are still valid support planes.
    """
    # Only check catastrophic for failed frames
    if floor_quality in ("good", "noisy"):
        return False, ""
    
    # Catastrophic checks for failed frames
    if inlier_ratio < CATASTROPHIC_INLIER_RATIO:
        return True, f"inlier_ratio={inlier_ratio:.2f}<{CATASTROPHIC_INLIER_RATIO}"
    
    # v8.5: Skip yfl95 hard-fail if support plane was successfully selected
    # The support plane's own metrics (sr_inlier_ratio, sr_residual_p95) 
    # already verified floor quality in the support region
    if floor_flatness_p95 > CATASTROPHIC_YFL95_CEILING:
        if support_plane_selected:
            # Log but don't drop - yfl95 will still affect confidence/weight
            print(f"[Fusion] v8.5: yfl95={floor_flatness_p95:.2f}>{CATASTROPHIC_YFL95_CEILING} "
                  f"but support_plane_selected=True, demoting to penalty")
        else:
            return True, f"Yfl95={floor_flatness_p95:.2f}>{CATASTROPHIC_YFL95_CEILING}"
    
    if depth_confidence < CATASTROPHIC_DEPTH_VALID_PCT:
        return True, f"depth_conf={depth_confidence:.2f}<{CATASTROPHIC_DEPTH_VALID_PCT}"
    
    return False, ""


def _get_weight(floor_quality: str) -> float:
    """Get fusion weight based on floor quality."""
    if floor_quality == "good":
        return WEIGHT_GOOD
    elif floor_quality == "noisy":
        return WEIGHT_NOISY
    else:  # failed (non-catastrophic)
        return WEIGHT_FAILED


def _weighted_trimmed_mean(volumes: list[float], weights: list[float]) -> float:
    """
    Weighted trimmed mean: sort by volume, trim extremes, weighted average.
    For 4 frames: trims 0-1 extremes based on weight.
    """
    if not volumes:
        return 0.0
    
    if len(volumes) == 1:
        return volumes[0]
    
    if len(volumes) == 2:
        # Simple weighted average
        total_w = sum(weights)
        return sum(v * w for v, w in zip(volumes, weights)) / total_w
    
    # Sort by volume
    paired = sorted(zip(volumes, weights))
    sorted_vols = [v for v, _ in paired]
    sorted_weights = [w for _, w in paired]
    
    # For 3-4 frames, soft-trim: give extremes reduced effective weight
    if len(volumes) <= 4:
        # Reduce weight of min/max by 50%
        sorted_weights[0] *= 0.5  # Min
        sorted_weights[-1] *= 0.5  # Max
    else:
        # For 5+ frames, hard trim the ends
        sorted_vols = sorted_vols[1:-1]
        sorted_weights = sorted_weights[1:-1]
    
    total_w = sum(sorted_weights)
    if total_w == 0:
        return np.mean(volumes)
    
    return sum(v * w for v, w in zip(sorted_vols, sorted_weights)) / total_w


def _attempt_cross_fusion(
    role_quals: list[RoleQualification],
    pile_type: str = "household",
    pile_density: str = "loose",
    density_confidence: str = "medium",
    pile_touches_background: bool = False,
    veg_overlap_high: bool = False,
    max_frame_volume: float = 999.0  # For envelope cap
) -> tuple[Optional[float], Optional[str]]:
    """
    Attempt cross-frame fusion using complementary donors.
    
    Uses footprint from best footprint-qualified frame,
    and P85 height from best height-qualified frame.
    
    Fix 1: Volume capped at evidence envelope (max_frame_volume × 1.15)
    Fix 5: Donors must have continuous_weight >= DONOR_WEIGHT_MIN
    
    Returns:
        (volume_cy, method) if successful, (None, None) if not possible
    """
    # Find qualified donors for each role
    footprint_donors = [rq for rq in role_quals if rq.qualified_footprint]
    height_donors = [rq for rq in role_quals if rq.qualified_height]
    
    # v10.2: Require minimum 3 frames for cross-fusion
    # With only 2 frames, cross-fusion picks the most aggressive single estimate
    # and ignores the other frame entirely. Weighted mean is more balanced.
    total_frames = len(role_quals)
    if total_frames < 3:
        print(f"[CrossFusion] Only {total_frames} frames — need ≥3 for cross-fusion → fallback to weighted mean")
        return None, None
    
    if not footprint_donors:
        print("[CrossFusion] No qualified footprint donors - cannot cross-fuse")
        return None, None
    
    if not height_donors:
        print("[CrossFusion] No qualified height donors - cannot cross-fuse")
        return None, None
    
    # Select footprint donor: strategy depends on pile type
    sorted_fp = sorted(footprint_donors, key=lambda rq: rq.footprint_m2)
    mid_idx = len(sorted_fp) // 2
    median_fp_donor = sorted_fp[mid_idx]  # Median frame by footprint
    median_footprint = median_fp_donor.footprint_m2
    
    # Clean frame thresholds
    CLEAN_GROUND_OVERLAP_MAX = 0.20  # Ground overlap < 20%
    CLEAN_MASK_COVERAGE_MAX = 0.50   # Mask coverage < 50%
    
    if pile_type == "yard_waste":
        # GUARDRAIL v2: MAX from "clean" frames only
        # Clean = low ground overlap (not leaking onto floor)
        clean_donors = [
            rq for rq in footprint_donors
            if rq.ground_overlap_ratio < CLEAN_GROUND_OVERLAP_MAX
        ]
        
        if clean_donors:
            # Use MAX from clean frames
            best_fp_donor = max(clean_donors, key=lambda rq: rq.footprint_m2)
            footprint_m2 = best_fp_donor.footprint_m2
            print(f"[CrossFusion] Yard waste: MAX from {len(clean_donors)} clean frames → {footprint_m2:.2f} m²")
        else:
            # No clean frames - fallback to capped median
            max_fp_donor = max(footprint_donors, key=lambda rq: rq.footprint_m2)
            max_footprint = max_fp_donor.footprint_m2
            leak_cap = median_footprint * 2.0
            
            if max_footprint > leak_cap:
                print(f"[CrossFusion] Yard waste: no clean frames, MAX {max_footprint:.2f} m² exceeds 2×median cap, using {leak_cap:.2f} m²")
                footprint_m2 = leak_cap
                best_fp_donor = median_fp_donor
            else:
                print(f"[CrossFusion] Yard waste: no clean frames, using MAX {max_footprint:.2f} m² (under 2×median cap)")
                footprint_m2 = max_footprint
                best_fp_donor = max_fp_donor
    else:
        # Non-yard waste: use MEDIAN to avoid tarp-inflation outliers
        best_fp_donor = median_fp_donor
        footprint_m2 = median_footprint
    
    # Select height donor: use MAX (tallest measurement wins)
    best_h_donor = max(height_donors, key=lambda rq: rq.height_p85_m)
    height_m = best_h_donor.height_p85_m
    
    # === Fix 5: Donor eligibility gate ===
    # Both donors must have sufficient continuous weight
    fp_weight = best_fp_donor.continuous_weight
    h_weight = best_h_donor.continuous_weight
    
    if fp_weight < DONOR_WEIGHT_MIN or h_weight < DONOR_WEIGHT_MIN:
        print(f"[CrossFusion] Donor weights too low (fp={fp_weight:.2f}, h={h_weight:.2f}, min={DONOR_WEIGHT_MIN}) → fallback")
        return None, None
    
    print(f"[CrossFusion] Footprint donor: {best_fp_donor.frame_id[:8]} → {footprint_m2:.2f} m² (weight={fp_weight:.2f})")
    print(f"[CrossFusion] Height donor: {best_h_donor.frame_id[:8]} → {height_m:.2f} m (P85, weight={h_weight:.2f})")
    
    # Compute hybrid volume with dynamic shape factor
    shape_factor = get_shape_factor(
        pile_type=pile_type,
        pile_density=pile_density,
        density_confidence=density_confidence,
        pile_touches_background=pile_touches_background,
        veg_overlap_high=veg_overlap_high
    )
    volume_m3 = footprint_m2 * height_m * shape_factor
    volume_cy = volume_m3 * 1.308  # m³ to yd³
    
    print(f"[SHAPE_FACTOR] density={pile_density}, pile_type={pile_type}, confidence={density_confidence} → factor={shape_factor:.2f}")
    print(f"[CrossFusion] Hybrid: {footprint_m2:.2f} m² × {height_m:.2f} m × {shape_factor:.2f} = {volume_cy:.2f} yd³")
    
    # === Fix 1: Evidence envelope cap ===
    envelope_cap = max_frame_volume * ENVELOPE_CAP_MULTIPLIER
    if volume_cy > envelope_cap:
        print(f"[CAP] Cross-fusion {volume_cy:.2f} > envelope {envelope_cap:.2f} (max×{ENVELOPE_CAP_MULTIPLIER}) → capped")
        volume_cy = envelope_cap
    
    # Determine fusion method name based on donor diversity
    if best_fp_donor.frame_id == best_h_donor.frame_id:
        method = "cross_fusion_same_donor"
    else:
        method = "cross_fusion_complementary"
    
    return volume_cy, method


def run_fusion(
    frame_results: list[VolumetricResult],
    floor_qualities: dict[str, str],
    depth_confidences: dict[str, float],
    floor_flatness_p95s: Optional[dict[str, float]] = None,
    inlier_ratios: Optional[dict[str, float]] = None,
    mask_coverages: Optional[dict[str, float]] = None,
    floor_area_pcts: Optional[dict[str, float]] = None,  # From Lane D
    scene_types: Optional[dict[str, str]] = None,  # Fix 2: scene type per frame
    tilt_degs: Optional[dict[str, float]] = None,  # Fix 4: plane angle per frame
    semantic_removed_pcts: Optional[dict[str, float]] = None,  # v6.4.1: semantic removal %
    uncertainty_boost: float = 1.0,  # From GPT-4o router mode config
    # Shape factor params from router
    pile_type: str = "household",
    pile_density: str = "loose",
    density_confidence: str = "medium",
    pile_touches_background: bool = False,
    veg_overlap_high: bool = False,
    # v6.9.0: VLM Triage integration
    triage_result: Optional["TriageResult"] = None,
    # v8.2.2: Depth-aware ground sub saved ratios for FP_GUARD skip
    depth_sub_saved_ratios: Optional[dict[str, float]] = None,
    # v8.5: Support plane selection flags per frame
    support_plane_selected: Optional[dict[str, bool]] = None,
    # v8.5.2: Support-plane metrics for donor eligibility
    sr_inlier_ratios: Optional[dict[str, float]] = None,
    sr_yfl95s: Optional[dict[str, float]] = None,
    # v10.4: Intrinsics mismatch gating
    intrinsics_fx_ratios: Optional[dict[str, float]] = None,
    intrinsics_derived: Optional[dict[str, bool]] = None
) -> FusionResult:

    """
    Stage 6 Entry Point: Role-Based Cross-Fusion with Weighted Fallback.
    
    Primary: Cross-frame fusion using best footprint + height donors
    Fallback: Weighted trimmed mean (if cross-fusion not possible)
    
    v6.3.0 Guardrail v3 updates:
    - Fix 1: Evidence envelope cap (max_frame × 1.15)
    - Fix 2: Scene-aware YFL95 thresholds for height donors
    - Fix 4: Continuous weight with angle + mask factors
    - Fix 5: Donor eligibility gate (weight >= 0.70)
    
    Args:
        frame_results: VolumetricResult from each frame
        floor_qualities: Dict of frame_id → floor quality from Stage 3
        depth_confidences: Dict of frame_id → depth confidence from Stage 3
        floor_flatness_p95s: Dict of frame_id → Yfl95 from Stage 3
        inlier_ratios: Dict of frame_id → RANSAC inlier ratio from Stage 3
        mask_coverages: Dict of frame_id → bulk mask area ratio from Lane B
        floor_area_pcts: Dict of frame_id → ground area % from Lane D
        scene_types: Dict of frame_id → scene type from Lane C
        
    Returns:
        FusionResult with final volume and uncertainty
    """
    result = FusionResult(
        final_volume_cy=0.0,
        uncertainty_min_cy=0.0,
        uncertainty_max_cy=0.0
    )
    
    if not frame_results:
        return result
    
    # Defaults for optional params
    if floor_flatness_p95s is None:
        floor_flatness_p95s = {}
    if inlier_ratios is None:
        inlier_ratios = {}
    if mask_coverages is None:
        mask_coverages = {}
    if floor_area_pcts is None:
        floor_area_pcts = {}
    if scene_types is None:
        scene_types = {}
    if tilt_degs is None:
        tilt_degs = {}
    if semantic_removed_pcts is None:
        semantic_removed_pcts = {}
    if support_plane_selected is None:
        support_plane_selected = {}
    if sr_inlier_ratios is None:
        sr_inlier_ratios = {}
    if sr_yfl95s is None:
        sr_yfl95s = {}
    # Step 1: Catastrophic filtering
    valid_results = []
    centroids = []
    
    for fr in frame_results:
        floor_q = floor_qualities.get(fr.frame_id, "unknown")
        depth_c = depth_confidences.get(fr.frame_id, 0.8)
        yfl95 = floor_flatness_p95s.get(fr.frame_id, 0.20)
        inlier_r = inlier_ratios.get(fr.frame_id, 0.5)
        mask_cov = mask_coverages.get(fr.frame_id, 1.0)  # Default to 1.0 if not provided
        
        # NEW: Check for no-mask catastrophic (0% coverage = no segmentation)
        if mask_cov < 0.01:  # Less than 1% mask coverage
            result.rejected_frames.append(fr.frame_id)
            result.rejection_reasons[fr.frame_id] = f"catastrophic:no_mask (coverage={mask_cov:.1%})"
            print(f"[Fusion] DROPPED (no_mask): {fr.frame_id[:8]} - coverage={mask_cov:.1%}")
            continue
        
        # Check for catastrophic failure (floor quality)
        # v8.5: Pass support_plane_selected to bypass yfl95 hard-fail
        sp_selected = support_plane_selected.get(fr.frame_id, False)
        is_cat, cat_reason = _is_catastrophic(floor_q, yfl95, inlier_r, depth_c, sp_selected)
        
        if is_cat:
            result.rejected_frames.append(fr.frame_id)
            result.rejection_reasons[fr.frame_id] = f"catastrophic:{cat_reason}"
            print(f"[Fusion] DROPPED (catastrophic): {fr.frame_id[:8]} - {cat_reason}")
            continue
        
        # Height field must be valid
        if not fr.height_field_valid:
            result.rejected_frames.append(fr.frame_id)
            result.rejection_reasons[fr.frame_id] = "height_field_invalid"
            continue
        
        # Frame is valid (or non-catastrophic failed)
        centroid = _extract_centroid(fr.grid_cells)
        valid_results.append((fr, centroid, floor_q))
        result.valid_frames.append(fr.frame_id)
    
    if not valid_results:
        # All frames rejected - use max from all as fallback
        volumes = [fr.frame_volume_cy for fr in frame_results]
        if volumes:
            result.final_volume_cy = max(volumes)
            result.fusion_method = "max_fallback"
        return result
    
    # ==========================================================================
    # Step 1.5: ROLE QUALIFICATION (NEW - Action A)
    # ==========================================================================
    # Qualify each valid frame for footprint and/or height donor roles
    # A frame must pass ALL relevant gates to be considered for a role
    
    role_qualifications = []
    for fr, _, floor_q in valid_results:
        yfl95 = floor_flatness_p95s.get(fr.frame_id, 0.20)
        inlier_r = inlier_ratios.get(fr.frame_id, 0.5)
        mask_cov = mask_coverages.get(fr.frame_id, 0.30)
        floor_area = floor_area_pcts.get(fr.frame_id, 0.35)
        scene_type = scene_types.get(fr.frame_id, "unknown")
        tilt_deg = tilt_degs.get(fr.frame_id, 0.0)  # Fix 4: plane angle for weight
        
        # v8.5.3: Get support-plane metrics for gate bypass
        sp_selected = support_plane_selected.get(fr.frame_id, False)
        sr_inlier = sr_inlier_ratios.get(fr.frame_id, 0.0)
        sr_p95 = sr_yfl95s.get(fr.frame_id, 0.20)
        
        rq = _qualify_frame_for_roles(
            frame_id=fr.frame_id,
            volumetric_result=fr,
            inlier_ratio=inlier_r,
            yfl95=yfl95,
            mask_coverage=mask_cov,
            floor_area_pct=floor_area,
            tilt_deg=tilt_deg,  # Pass plane angle for Fix 4 weighting
            scene_type=scene_type,
            floor_quality=floor_q,
            # v8.5.3: Support-plane metrics for gate bypass
            support_plane_selected=sp_selected,
            sr_inlier_ratio=sr_inlier,
            sr_yfl95=sr_p95,
            # v8.6: Guardrail quarantine
            donor_eligible=fr.filter_stats.get('donor_eligible', True),
            # v10.4: Intrinsics mismatch gating
            intrinsics_fx_ratio=intrinsics_fx_ratios.get(fr.frame_id) if intrinsics_fx_ratios else None,
            intrinsics_derived=intrinsics_derived.get(fr.frame_id, False) if intrinsics_derived else False
        )
        
        # v6.4.1: Store semantic removal percentage for partial view detection
        rq.semantic_removed_pct = semantic_removed_pcts.get(fr.frame_id, 0.0)
        
        # v8.5.2: Store support-plane metrics on rq for other uses (MES, height consensus)
        rq.support_plane_selected = sp_selected
        rq.sr_inlier_ratio = sr_inlier
        rq.sr_yfl95 = sr_p95
        
        role_qualifications.append(rq)

    
    # ==========================================================================
    # Step 1.52: v7.2 FOOTPRINT CONSISTENCY (LOG-RATIO MAD)
    # ==========================================================================
    # Identify frames with inflated footprints using robust log-ratio detection
    fp_consistency = _compute_footprint_consistency_log_ratio(role_qualifications)
    
    # Apply footprint consistency penalty to role qualifications
    fp_outlier_count = 0
    for rq in role_qualifications:
        if rq.frame_id in fp_consistency:
            log_ratio, is_inlier = fp_consistency[rq.frame_id]
            if not is_inlier:
                fp_outlier_count += 1
                # Penalize outlier frames - reduce their weight
                rq.continuous_weight *= 0.4
                rq.eligible_for_footprint = False
                print(f"[FP_CONSISTENCY] {rq.frame_id[:8]}: PENALIZED (log_ratio={log_ratio:.2f})")
    
    if fp_outlier_count > 0:
        print(f"[FP_CONSISTENCY] {fp_outlier_count} frames penalized for footprint outlier")
    
    # ==========================================================================
    # Step 1.55: v6.5 MES COMPUTATION
    # ==========================================================================
    # Compute Measurement Evidence Score for each frame using weighted mean
    
    # First compute job height consensus (robust: top-trusted frames only)
    job_height_consensus = _compute_job_height_consensus(role_qualifications)
    print(f"[MES] Job height consensus: {job_height_consensus:.2f}m")
    
    # Get sorted heights for outlier detection
    all_heights = sorted([rq.height_p85_m for rq in role_qualifications if rq.height_p85_m > 0], reverse=True)
    second_highest_height = all_heights[1] if len(all_heights) >= 2 else 0.0
    
    # Compute MES for each frame
    mes_scores: list[MeasurementEvidenceScore] = []
    
    for rq in role_qualifications:
        mes = MeasurementEvidenceScore(frame_id=rq.frame_id)
        
        # Populate tracking fields
        mes.inlier_ratio = rq.inlier_ratio
        mes.yfl95 = rq.yfl95
        mes.plane_angle_deg = rq.plane_angle_deg
        mes.border_touch_ratio = rq.border_touch_ratio
        mes.semantic_removed_pct = rq.semantic_removed_pct
        mes.height_p95_m = rq.height_p95_m  # v10.7: Use actual P95 from canonical
        
        # Geometry score (with noise-ratio and outlier guard)
        # v8.5.3: Pass support-plane metrics for yfl95 bypass
        mes.geometry_score, mes.noise_ratio, mes.hard_excluded, mes.exclusion_reason = \
            _compute_mes_geometry_score(
                inlier_ratio=rq.inlier_ratio,
                yfl95=rq.yfl95,
                height_p95=rq.height_p95_m,  # v10.7: Use actual P95 from canonical
                plane_angle_deg=rq.plane_angle_deg,
                second_highest_height=second_highest_height,
                support_plane_selected=rq.support_plane_selected,
                sr_yfl95=rq.sr_yfl95
            )
        
        # Skip other components if hard excluded
        if not mes.hard_excluded:
            # Completeness score
            floor_visible = rq.floor_area_pct > 0.08  # Matches floor visibility gate
            mes.completeness_score = _compute_mes_completeness_score(
                mask_coverage=rq.mask_coverage,
                border_touch_ratio=rq.border_touch_ratio,
                floor_visible=floor_visible,
                ground_overlap_ratio=rq.ground_overlap_ratio
            )
            
            # Height score (relative to job consensus)
            mes.height_score = _compute_mes_height_score(
                frame_height_p95=rq.height_p85_m,
                job_height_consensus=job_height_consensus
            )
            
            # Semantic score
            mes.semantic_score = _compute_mes_semantic_score(rq.semantic_removed_pct)
            
            # Composite MES (weighted mean)
            mes.raw_score = _compute_mes(
                geometry_score=mes.geometry_score,
                completeness_score=mes.completeness_score,
                height_score=mes.height_score,
                semantic_score=mes.semantic_score
            )
        
        # Log MES
        _log_mes(mes, job_height_consensus)
        mes_scores.append(mes)
    
    # ==========================================================================
    # Step 1.6: ATTEMPT CROSS-FUSION (v6.3.0 Guardrail v3)
    # ==========================================================================
    # Try to cross-fuse using best footprint donor + best height donor
    # Falls back to traditional if no qualified donors for either role
    # Fix 1: Envelope cap at max_frame × 1.15
    # Fix 5: Donor eligibility gate (weight >= 0.70)
    
    # Compute max frame volume for envelope cap
    max_frame_volume = max((fr.frame_volume_cy for fr, _, _ in valid_results), default=1.0)
    
    cross_volume, cross_method = _attempt_cross_fusion(
        role_qualifications,
        pile_type=pile_type,
        pile_density=pile_density,
        density_confidence=density_confidence,
        pile_touches_background=pile_touches_background,
        veg_overlap_high=veg_overlap_high,
        max_frame_volume=max_frame_volume
    )
    
    if cross_volume is not None:
        # Cross-fusion succeeded - use it as primary
        result.final_volume_cy = cross_volume
        result.fusion_method = cross_method
        
        # Still compute traditional for comparison (diagnostic)
        print(f"[Fusion] Cross-fusion succeeded: {cross_volume:.2f} yd³ ({cross_method})")
    
    # Step 2: Check viewpoint diversity
    is_diverse, diversity = _check_viewpoint_diversity(
        [(fr, c) for fr, c, _ in valid_results]
    )
    result.viewpoint_diversity = diversity

    
    # Step 3: Collect frame data with MES-based weights (v6.5.1)
    # MES is now the single source of truth for weights
    frame_data = []
    volumes = []
    weights = []
    
    # Build lookup from role qualifications
    rq_lookup = {rq.frame_id: rq for rq in role_qualifications}
    
    # S2: Filter to only valid frames (Fix A from review)
    valid_frame_ids = {fr.frame_id for fr, _, _ in valid_results}
    
    # v6.5.2b: Compute MES-based weights with footprint sanity guard
    # v6.9.0: Pass triage_result for w_triage multiplier
    # v8.2.2: Pass depth_sub_saved_ratios for geometry-backed FP_GUARD skip
    mes_weights = _compute_mes_fusion_weights(mes_scores, role_qualifications, triage_result, depth_sub_saved_ratios)
    
    for fr, _, floor_q in valid_results:
        rq = rq_lookup.get(fr.frame_id)
        
        # v6.5.1: Use MES-based weight instead of RoleQual weight
        weight = mes_weights.get(fr.frame_id, MES_WEIGHT_FLOOR)
        
        # Use frame_volume_cy (includes discrete), not just bulk_raw
        vol = fr.frame_volume_cy
        
        # Store frame volume in RQ for later reference
        if rq:
            rq.frame_volume_cy = vol
        
        volumes.append(vol)
        weights.append(weight)

        
        active_cells = len([c for c in fr.grid_cells if c.trimmed_height > 0])
        footprint_m2 = active_cells * 0.01
        
        frame_data.append({
            'frame_id': fr.frame_id,
            'volume': vol,
            'weight': weight,
            'floor_quality': floor_q,
            'active_cells': active_cells,
            'footprint': footprint_m2
        })
        
        # S2: Log with actual continuous weight
        print(f"[Fusion] Frame {fr.frame_id[:8]}: {vol:.2f} yd³, w={weight:.2f}, cells={active_cells}")
    
    # Step 4: Compute diagnostic sums FIRST (before fusion)
    result.sum_valid_cy = sum(volumes)
    result.sum_weighted_cy = sum(v * w for v, w in zip(volumes, weights))
    
    # v6.4.1: Detect two-tier partial views
    for rq in role_qualifications:
        if rq.frame_id not in valid_frame_ids:
            continue
        
        removed = rq.semantic_removed_pct
        mask_cov = rq.mask_coverage
        
        # Severe: exclude from trusted-max
        if removed >= SEM_REMOVED_SEVERE and mask_cov >= SEM_MASK_COV_MIN_SEVERE:
            rq.partial_view = True
            print(f"[Fusion] {rq.frame_id[:8]}: partial_view=SEVERE "
                  f"(sem={removed:.0%}, mask={mask_cov:.0%})")
        # Moderate: allow but note for logging
        elif removed >= SEM_REMOVED_MODERATE and mask_cov >= SEM_MASK_COV_MIN_MODERATE:
            rq.partial_view_soft = True
            print(f"[Fusion] {rq.frame_id[:8]}: partial_view=MODERATE "
                  f"(sem={removed:.0%}, mask={mask_cov:.0%})")
    
    # Step 5: PRIMARY FUSION - Cross-fusion or Union-Blend/Trimmed Mean fallback
    if result.fusion_method in ("cross_fusion_complementary", "cross_fusion_same_donor"):
        # Cross-fusion already set the result in Step 1.6
        # Compute traditional for diagnostic comparison
        traditional_volume = _weighted_trimmed_mean(volumes, weights)
        print(f"[Fusion] Traditional comparison: {traditional_volume:.2f} yd³ (cross-fusion used: {result.final_volume_cy:.2f} yd³)")
    else:
        # Cross-fusion failed - use S1 union-blend with v6.5 trusted-max
        
        # v10.5: Compute coverage evidence (require this to trigger union-blend)
        # Union-blend is only appropriate for TRUE complementary views (non-overlapping)
        fp_values = [rq.footprint_m2 for rq in role_qualifications if rq.footprint_m2 > 0]
        border_touch_sum = sum(rq.border_touch_ratio for rq in role_qualifications)
        
        # Evidence of complementary coverage:
        # 1. Significant footprint variance (max/median > 1.5) - different views see different amounts
        # 2. OR multiple frames with border-touch > 0.5 total - frames are cutting off parts
        fp_max = max(fp_values) if fp_values else 0
        fp_median = np.median(fp_values) if fp_values else 0
        fp_variance = (fp_max / fp_median > 1.5) if fp_median > 0 else False
        multiple_partials = border_touch_sum > 0.5
        
        coverage_evidence = fp_variance or multiple_partials
        fp_ratio = fp_max / fp_median if fp_median > 0 else 0
        print(f"[UnionBlend] coverage_evidence={coverage_evidence} "
              f"(fp_max/median={fp_ratio:.2f}, border_touch_sum={border_touch_sum:.2f})")
        
        # v6.5: Compute trusted-max using MES eligibility
        trusted_max_vol, trusted_frame_id = _get_trusted_max_volume_v65(
            mes_scores, role_qualifications, valid_frame_ids
        )
        
        blend_volume, blend_triggered = _compute_union_blend(
            volumes, weights,
            trusted_max_volume=trusted_max_vol,
            trusted_frame_id=trusted_frame_id,
            coverage_evidence=coverage_evidence  # v10.5: require evidence
        )
        result.final_volume_cy = blend_volume
        
        if blend_triggered:
            result.fusion_method = "union_blend"
            print(f"[Fusion] Using union-blend (complementary views detected)")
        else:
            result.fusion_method = "weighted_trimmed_mean"
            print(f"[Fusion] Using weighted trimmed mean (cross-fusion not available)")


    
    # Cap at physical maximum
    if result.final_volume_cy > MAX_PILE_VOLUME_CY:
        print(f"[Fusion] Capping at {MAX_PILE_VOLUME_CY} yd³ (was {result.final_volume_cy:.1f})")
        result.final_volume_cy = MAX_PILE_VOLUME_CY
    
    # Diagnostic: detect partial-complement vs overlapping
    sum_median_ratio = result.sum_valid_cy / max(result.final_volume_cy, 0.1)
    if sum_median_ratio > 2.5 and result.fusion_method != "union_blend":
        print(f"[Fusion] SIGNAL: sum >> median (ratio={sum_median_ratio:.1f}x) → likely partial-complement views")
    elif sum_median_ratio < 1.5:
        print(f"[Fusion] SIGNAL: sum ≈ median (ratio={sum_median_ratio:.1f}x) → likely overlapping views")
    
    print(f"[Fusion] Result: {result.final_volume_cy:.2f} yd³ ({result.fusion_method})")
    print(f"[Fusion] Diagnostic: sum_valid={result.sum_valid_cy:.2f}, sum_weighted={result.sum_weighted_cy:.2f}")

    
    # Step 6: Merge discrete items
    all_discrete = [fr.discrete_items for fr, _, _ in valid_results]
    result.fused_discrete_items = _merge_discrete_items(all_discrete)
    
    # Step 7: Dynamic uncertainty based on spread + penalties
    # S5: Determine confidence level for quote-friendly banding
    is_low_confidence = (
        result.fusion_method == "union_blend" or
        len(valid_results) < 3 or
        not is_diverse or
        sum(1 for f in frame_data if f['floor_quality'] == 'failed') > 0
    )
    
    # v6.9.0: Coverage policy - force low confidence if triage detects incomplete coverage
    # v6.9.1: Only apply if triage_trust is sufficient (GAP 6 fix)
    coverage_band_widen = 1.0  # Default no widening
    if triage_result and triage_result.triage_available and triage_result.triage_trust >= 0.5:
        if triage_result.coverage_confidence >= 0.6:
            if triage_result.coverage_assessment == "poor":
                is_low_confidence = True
                coverage_band_widen = 1.4  # +40% wider
                print(f"[Banding] Coverage=poor (conf={triage_result.coverage_confidence:.2f}) → forced LOW, band×1.4")
            elif triage_result.coverage_assessment == "partial":
                if not is_low_confidence:
                    is_low_confidence = True
                    print(f"[Banding] Coverage=partial (conf={triage_result.coverage_confidence:.2f}) → forced LOW")
                coverage_band_widen = 1.2  # +20% wider
        else:
            # Uncertain coverage: mild widen only
            coverage_band_widen = 1.1
            print(f"[Banding] Coverage uncertain (conf={triage_result.coverage_confidence:.2f}) → mild widen")
    
    if is_low_confidence:
        # S5: Quote-friendly banding - use conservative bounded range
        V_wmed = _weighted_percentile(volumes, weights, 50)
        V_ref = _weighted_percentile(volumes, weights, 85)
        
        # Conservative banding around estimate
        # v6.9.0: Apply coverage_band_widen to low confidence path too
        min_mult = 0.85 / coverage_band_widen  # Widen by reducing min
        max_mult = 1.25 * coverage_band_widen  # Widen by increasing max
        result.uncertainty_min_cy = round(max(0.1, result.final_volume_cy * min_mult, V_wmed * min_mult), 1)
        result.uncertainty_max_cy = round(min(result.final_volume_cy * max_mult, V_ref * ENVELOPE_CAP_MULTIPLIER * coverage_band_widen), 1)
        
        print(f"[Banding] LOW confidence → bounded range [{result.uncertainty_min_cy:.1f}, {result.uncertainty_max_cy:.1f}]")
    else:
        # Standard MAD-based uncertainty
        if len(volumes) >= 2:
            median_vol = np.median(volumes)
            mad = np.median(np.abs(np.array(volumes) - median_vol))
            base_uncertainty = mad * 1.4826  # Convert MAD to std-like
        else:
            base_uncertainty = result.final_volume_cy * 0.15
        
        # Penalties (already handled by is_low_confidence check above)
        n_failed = sum(1 for f in frame_data if f['floor_quality'] == 'failed')
        if n_failed > 0:
            base_uncertainty *= (1 + 0.2 * n_failed)
        
        if not is_diverse:
            base_uncertainty *= 1.3
        
        if len(valid_results) < 3:
            base_uncertainty *= 1.2
        
        # Minimum uncertainty: ±10% of final
        min_uncertainty = result.final_volume_cy * 0.10
        base_uncertainty = max(base_uncertainty, min_uncertainty)
        
        # v6.9.0: Apply coverage-based band widening from triage
        base_uncertainty *= coverage_band_widen
        
        result.uncertainty_min_cy = round(max(0.1, result.final_volume_cy - base_uncertainty), 1)
        result.uncertainty_max_cy = round(result.final_volume_cy + base_uncertainty, 1)
    
    result.final_volume_cy = round(result.final_volume_cy, 1)
    
    print(f"[Fusion] Final: {result.final_volume_cy:.1f} yd³ ({result.uncertainty_min_cy:.1f} - {result.uncertainty_max_cy:.1f})")
    
    # =========================================================================
    # TRIAGE VALIDATION LOGS (compare triage vs geometry outcomes)
    # =========================================================================
    if triage_result and triage_result.triage_available:
        # A) Donor alignment: triage_top2 vs MES_top2 vs V_ref selection
        triage_top2 = triage_result.ranked_frames[:2] if len(triage_result.ranked_frames) >= 2 else triage_result.ranked_frames
        mes_by_weight = sorted([(fid, mes_weights.get(fid, 0)) for fid in mes_weights.keys()], 
                                key=lambda x: -x[1])[:2]
        mes_top2 = [x[0][:8] for x in mes_by_weight]
        vref_frame_short = trusted_frame_id[:8] if trusted_frame_id else "none"
        vref_blocked = False
        if trusted_frame_id and triage_result.frame_roles.get(trusted_frame_id):
            vref_blocked = not triage_result.frame_roles[trusted_frame_id].vref_ok
        print(f"[TRIAGE_VAL] Donor: triage_top2={[f[:8] for f in triage_top2]}, "
              f"MES_top2={mes_top2}, V_ref={vref_frame_short}, triage_blocked={vref_blocked}")
        
        # B) Risk alignment: job_multi vs geometry spread_pass/multi-surface
        job_multi = "multi_surface" in triage_result.job_risks
        n_spread_fail = sum(1 for f in frame_data if not f.get('spread_pass', True))
        print(f"[TRIAGE_VAL] Risk: job_multi={job_multi} "
              f"(source={triage_result.job_risk_sources.get('multi_surface','n/a')}), "
              f"geom_spread_fail={n_spread_fail}/{len(frame_data)}")
        
        # C) Coverage alignment: donors vs band widening
        n_h = sum(1 for r in triage_result.frame_roles.values() if r.height_ok)
        n_fp = sum(1 for r in triage_result.frame_roles.values() if r.footprint_ok)
        band_widened = coverage_band_widen > 1.0
        print(f"[TRIAGE_VAL] Coverage: {triage_result.coverage_assessment}, "
              f"donors_h={n_h}, donors_fp={n_fp}, band_widen={coverage_band_widen:.1f}")
        
        # D) Contradiction check: triage says height_ok but geometry fails
        contradictions = []
        for fid, roles in triage_result.frame_roles.items():
            fd = next((f for f in frame_data if f.get('frame_id') == fid), None)
            if fd:
                if roles.height_ok and fd.get('floor_quality') == 'failed':
                    contradictions.append(f"{fid[:8]}:h_ok+floor_fail")
                if roles.footprint_ok and fd.get('inlier_ratio', 1) < 0.7:
                    contradictions.append(f"{fid[:8]}:fp_ok+low_inlier")
        if contradictions:
            print(f"[TRIAGE_VAL] Contradiction: {contradictions}")
        else:
            print(f"[TRIAGE_VAL] Contradiction: none")
    
    return result


