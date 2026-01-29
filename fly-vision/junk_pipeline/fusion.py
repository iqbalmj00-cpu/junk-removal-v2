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
    depth_confidence: float
) -> tuple[bool, str]:
    """
    Check if a frame should be catastrophically dropped.
    Returns (is_catastrophic, reason).
    """
    # Only check catastrophic for failed frames
    if floor_quality in ("good", "noisy"):
        return False, ""
    
    # Catastrophic checks for failed frames
    if inlier_ratio < CATASTROPHIC_INLIER_RATIO:
        return True, f"inlier_ratio={inlier_ratio:.2f}<{CATASTROPHIC_INLIER_RATIO}"
    
    if floor_flatness_p95 > CATASTROPHIC_YFL95_CEILING:
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


def run_fusion(
    frame_results: list[VolumetricResult],
    floor_qualities: dict[str, str],
    depth_confidences: dict[str, float],
    floor_flatness_p95s: Optional[dict[str, float]] = None,
    inlier_ratios: Optional[dict[str, float]] = None,
    mask_coverages: Optional[dict[str, float]] = None
) -> FusionResult:
    """
    Stage 6 Entry Point: Weighted Trimmed Mean Fusion.
    
    Primary: Weighted trimmed mean (production-safe, stable)
    Diagnostic: Also computes sum_valid and sum_weighted for anomaly detection
    
    Args:
        frame_results: VolumetricResult from each frame
        floor_qualities: Dict of frame_id → floor quality from Stage 3
        depth_confidences: Dict of frame_id → depth confidence from Stage 3
        floor_flatness_p95s: Dict of frame_id → Yfl95 from Stage 3
        inlier_ratios: Dict of frame_id → RANSAC inlier ratio from Stage 3
        mask_coverages: Dict of frame_id → bulk mask area ratio from Lane B
        
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
        is_cat, cat_reason = _is_catastrophic(floor_q, yfl95, inlier_r, depth_c)
        
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
    
    # Step 2: Check viewpoint diversity
    is_diverse, diversity = _check_viewpoint_diversity(
        [(fr, c) for fr, c, _ in valid_results]
    )
    result.viewpoint_diversity = diversity
    
    # Step 3: Collect frame data with weights
    frame_data = []
    volumes = []
    weights = []
    
    for fr, _, floor_q in valid_results:
        weight = _get_weight(floor_q)
        vol = fr.bulk_raw_cy
        
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
        
        print(f"[Fusion] Frame {fr.frame_id[:8]}: {vol:.2f} yd³, weight={weight:.2f} ({floor_q}), cells={active_cells}")
    
    # Step 4: Compute diagnostic sums FIRST (before fusion)
    result.sum_valid_cy = sum(volumes)
    result.sum_weighted_cy = sum(v * w for v, w in zip(volumes, weights))
    
    # Step 5: PRIMARY FUSION - Weighted Trimmed Mean
    result.final_volume_cy = _weighted_trimmed_mean(volumes, weights)
    result.fusion_method = "weighted_trimmed_mean"
    
    # Cap at physical maximum
    if result.final_volume_cy > MAX_PILE_VOLUME_CY:
        print(f"[Fusion] Capping at {MAX_PILE_VOLUME_CY} yd³ (was {result.final_volume_cy:.1f})")
        result.final_volume_cy = MAX_PILE_VOLUME_CY
    
    # Diagnostic: detect partial-complement vs overlapping
    sum_median_ratio = result.sum_valid_cy / max(result.final_volume_cy, 0.1)
    if sum_median_ratio > 2.5:
        print(f"[Fusion] SIGNAL: sum >> median (ratio={sum_median_ratio:.1f}x) → likely partial-complement views")
    elif sum_median_ratio < 1.5:
        print(f"[Fusion] SIGNAL: sum ≈ median (ratio={sum_median_ratio:.1f}x) → likely overlapping views")
    
    print(f"[Fusion] Weighted Trimmed Mean: {result.final_volume_cy:.2f} yd³")
    print(f"[Fusion] Diagnostic: sum_valid={result.sum_valid_cy:.2f}, sum_weighted={result.sum_weighted_cy:.2f}")
    
    # Step 6: Merge discrete items
    all_discrete = [fr.discrete_items for fr, _, _ in valid_results]
    result.fused_discrete_items = _merge_discrete_items(all_discrete)
    
    # Step 7: Dynamic uncertainty based on spread + penalties
    if len(volumes) >= 2:
        # MAD-based uncertainty
        median_vol = np.median(volumes)
        mad = np.median(np.abs(np.array(volumes) - median_vol))
        base_uncertainty = mad * 1.4826  # Convert MAD to std-like
    else:
        # Single frame: use ±15%
        base_uncertainty = result.final_volume_cy * 0.15
    
    # Penalties
    n_failed = sum(1 for f in frame_data if f['floor_quality'] == 'failed')
    if n_failed > 0:
        base_uncertainty *= (1 + 0.2 * n_failed)  # +20% per failed frame
    
    if not is_diverse:
        base_uncertainty *= 1.3  # Low diversity penalty
    
    if len(valid_results) < 3:
        base_uncertainty *= 1.2  # Few frames penalty
    
    # Minimum uncertainty: ±10% of final
    min_uncertainty = result.final_volume_cy * 0.10
    base_uncertainty = max(base_uncertainty, min_uncertainty)
    
    result.uncertainty_min_cy = round(max(0.1, result.final_volume_cy - base_uncertainty), 1)
    result.uncertainty_max_cy = round(result.final_volume_cy + base_uncertainty, 1)
    result.final_volume_cy = round(result.final_volume_cy, 1)
    
    print(f"[Fusion] Final: {result.final_volume_cy:.1f} yd³ ({result.uncertainty_min_cy:.1f} - {result.uncertainty_max_cy:.1f})")
    
    return result
