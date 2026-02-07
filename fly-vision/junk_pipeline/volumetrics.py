"""
Stage 5: Volumetric Integration (The Calculation)
Goal: "Truck Bed" volume - measure the terrain, subtract the knowns.
"""

from dataclasses import dataclass, field
from typing import Optional
import numpy as np

from .perception import InstanceMask

# Imports for depth-aware point filtering
from scipy.ndimage import label as scipy_label, binary_dilation
try:
    from sklearn.cluster import KMeans
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False


# Grid parameters for volumetric integration
GRID_CELL_SIZE_M = 0.10  # 10cm × 10cm cells
HEIGHT_PERCENTILE = 98  # Use 98th percentile (less trimming, preserves peaks)

# Privileged subtraction thresholds
DETECTION_CONF_THRESHOLD = 0.85  # Only subtract high-confidence items
DEPTH_CONSISTENCY_THRESHOLD = 0.20  # Max allowed depth variance in item region

# Volume catalog (cubic yards) for common discrete items
DISCRETE_VOLUME_CATALOG = {
    "sofa": 2.0,
    "couch": 2.0,
    "loveseat": 1.5,
    "refrigerator": 2.0,
    "fridge": 2.0,
    "washer": 1.2,
    "dryer": 1.2,
    "mattress": 1.2,
    "mattress_king": 1.5,
    "mattress_queen": 1.2,
    "mattress_twin": 0.8,
    "bed_frame": 0.8,
    "dresser": 1.0,
    "bookshelf": 1.0,
    "desk": 0.8,
    "table": 0.6,
    "dining_table": 1.0,
    "chair": 0.3,
    "armchair": 0.5,
    "recliner": 0.8,
    "tv": 0.3,
    "television": 0.3,
    "microwave": 0.15,
    "oven": 0.8,
    "dishwasher": 1.0,
    "treadmill": 1.5,
    "elliptical": 1.5,
    "exercise_bike": 0.8,
    "piano": 3.0,
    "hot_tub": 4.0,
}

# Meters³ to Cubic Yards conversion
M3_TO_CY = 1.30795

# ============================================================================
# DEPTH-AWARE POINT FILTERING (Background Removal)
# Removes trees, fences, walls from masked point set
# ============================================================================

# Scene-aware Y_max caps (meters)
Y_MAX_BY_SCENE = {
    "residential": 2.5,
    "outdoor_driveway": 2.5,
    "construction": 4.0,
    "demo": 4.0,
    "cleanout": 3.5,
    "indoor": 3.0,
}
Y_HARD_CAP = 6.0

# Filter thresholds
Z_SPLIT_MIN_SEPARATION = 2.0  # Minimum meters separation for Z-split
Z_SPLIT_RELATIVE_THRESHOLD = 0.4  # Also require separation > 40% of near_median
XZ_MIN_COMPONENT_AREA = 0.3  # m² - minimum to keep a component
CONTAMINATION_Y_THRESHOLD = 3.0  # Y_max above this suggests background
CONTAMINATION_MASK_THRESHOLD = 0.60  # mask_coverage above this suggests leak


def _detect_contamination(Y_max: float, mask_coverage: float, depth_at_cap_pct: float = 0.0) -> tuple[bool, list[str]]:
    """Detect if mask likely includes background contamination."""
    signals = []
    
    if Y_max > CONTAMINATION_Y_THRESHOLD:
        signals.append("tall_object")
    if mask_coverage > CONTAMINATION_MASK_THRESHOLD:
        signals.append("large_mask")
    if depth_at_cap_pct > 0.20:
        signals.append("far_background")
    
    return len(signals) > 0, signals


def _z_cluster_split_sp_aware(
    Z_vals: np.ndarray,
    Y_vals: np.ndarray,
    support_plane_selected: bool,
    sr_yfl95: float,
    sr_inlier_ratio: float = 0.0
) -> tuple[np.ndarray, bool, float, str]:
    """
    Split points by Z, but choose cluster based on Support Plane consistency.
    
    Strategy:
    - If no SP: use legacy near/far median logic
    - If SP trusted: choose cluster whose Y-heights look like "pile above floor"
    
    Args:
        Z_vals: Depth values
        Y_vals: Height values (rectified, Y=0 is floor)
        support_plane_selected: Whether a trusted support plane exists
        sr_yfl95: Support ROI P95 residual (local floor noise)
        sr_inlier_ratio: Support ROI inlier ratio
    
    Returns:
        (keep_mask, split_applied, separation_m, mode_str)
    """
    if len(Z_vals) < 100:
        return np.ones(len(Z_vals), dtype=bool), False, 0.0, 'skip'
    
    if not SKLEARN_AVAILABLE:
        # Fallback to MAD-based splitting
        Z_median = np.median(Z_vals)
        Z_mad = np.median(np.abs(Z_vals - Z_median)) * 1.4826
        near_mask = Z_vals <= Z_median + 2 * Z_mad
        return near_mask, False, 0.0, 'fallback'
    
    km = KMeans(n_clusters=2, n_init=3, random_state=42)
    # v8.6.2: Ensure no NaNs/Infs for KMeans
    Z_clean = np.nan_to_num(Z_vals, nan=0.0, posinf=0.0, neginf=0.0)
    km.fit(Z_clean.reshape(-1, 1))
    
    c0_med = np.median(Z_vals[km.labels_ == 0])
    c1_med = np.median(Z_vals[km.labels_ == 1])
    
    near_label = 0 if c0_med < c1_med else 1
    far_label = 1 - near_label
    separation = abs(c1_med - c0_med)
    
    # Check if split is meaningful
    near_med = min(c0_med, c1_med)
    sep_threshold = max(Z_SPLIT_MIN_SEPARATION, Z_SPLIT_RELATIVE_THRESHOLD * near_med)
    
    if separation <= sep_threshold:
        return np.ones(len(Z_vals), dtype=bool), False, separation, 'no_split'
    
    # === SUPPORT PLANE CONSISTENCY CHECK ===
    # If SP is trusted, choose cluster based on pile-like heights
    if support_plane_selected and sr_inlier_ratio >= 0.70:
        # Compute pile-likeness score for each cluster
        near_heights = Y_vals[km.labels_ == near_label]
        far_heights = Y_vals[km.labels_ == far_label]
        
        # Pile-like signature: Y > 2*sr_yfl95 (above floor noise)
        pile_threshold = max(2.0 * sr_yfl95, 0.05)
        
        # Score each cluster by:
        # 1) % of points above pile threshold (pile presence)
        # 2) P85 height (pile upper tail, robust to near-floor contamination)
        near_pct_above = (near_heights > pile_threshold).sum() / max(len(near_heights), 1)
        far_pct_above = (far_heights > pile_threshold).sum() / max(len(far_heights), 1)
        
        near_p85 = np.percentile(near_heights, 85)
        far_p85 = np.percentile(far_heights, 85)
        
        # Pile-likeness score: combine % above + P85 height
        near_score = near_pct_above * 0.6 + min(near_p85 / pile_threshold, 2.0) * 0.4
        far_score = far_pct_above * 0.6 + min(far_p85 / pile_threshold, 2.0) * 0.4
        
        # Choose cluster with higher pile-likeness score
        # v8.6.1: Lowered threshold 0.15 -> 0.05 to catch piles sharing cluster with floor
        if near_score > far_score and near_pct_above > 0.05:
            chosen_label = near_label
            mode = 'sp_near'
        elif far_score > near_score and far_pct_above > 0.05:
            chosen_label = far_label
            mode = 'sp_far'
        elif near_pct_above > 0.05 or far_pct_above > 0.05:
            # Both have pile signal - pick higher score
            chosen_label = near_label if near_score >= far_score else far_label
            mode = 'sp_both_elevated'
        else:
            # Neither has pile signal - legacy near logic
            chosen_label = near_label
            mode = 'sp_fallback_near'
        
        chosen_mask = km.labels_ == chosen_label
        return chosen_mask, True, separation, mode
    
    # === LEGACY MODE (no SP) ===
    near_mask = km.labels_ == near_label
    return near_mask, True, separation, 'legacy_near'



def _y_height_filter(Y_vals: np.ndarray, floor_noise: float, scene_type: str = "residential") -> tuple[np.ndarray, float, float]:
    """Height band filter with scene-aware caps."""
    Y_min = max(2.0 * floor_noise, 0.05)
    Y_max = Y_MAX_BY_SCENE.get(scene_type, 2.5)
    Y_max = min(Y_max, Y_HARD_CAP)
    
    height_mask = (Y_vals > Y_min) & (Y_vals < Y_max)
    return height_mask, Y_min, Y_max


def _xz_multicomponent_filter(X_vals: np.ndarray, Z_vals: np.ndarray, cell_size: float = 0.2) -> np.ndarray:
    """Keep all connected components above minimum area threshold."""
    if len(X_vals) < 10:
        return np.ones(len(X_vals), dtype=bool)
    
    # Rasterize to grid
    X_offset = X_vals - X_vals.min()
    Z_offset = Z_vals - Z_vals.min()
    X_bins = (X_offset / cell_size).astype(int)
    Z_bins = (Z_offset / cell_size).astype(int)
    
    grid_w = X_bins.max() + 1 if len(X_bins) > 0 else 1
    grid_h = Z_bins.max() + 1 if len(Z_bins) > 0 else 1
    
    grid = np.zeros((grid_h, grid_w), dtype=bool)
    for i in range(len(X_vals)):
        grid[Z_bins[i], X_bins[i]] = True
    
    labeled, n_comp = scipy_label(grid)
    
    if n_comp <= 1:
        return np.ones(len(X_vals), dtype=bool)
    
    # Count cells per component, keep those above threshold
    min_cells = int(XZ_MIN_COMPONENT_AREA / (cell_size ** 2))
    valid_labels = []
    for i in range(1, n_comp + 1):
        if (labeled == i).sum() >= min_cells:
            valid_labels.append(i)
    
    if not valid_labels:
        # Keep largest if none meet threshold
        sizes = [(labeled == i).sum() for i in range(1, n_comp + 1)]
        valid_labels = [np.argmax(sizes) + 1]
    
    # Map back to points
    point_labels = labeled[Z_bins, X_bins]
    keep_mask = np.isin(point_labels, valid_labels)
    return keep_mask


def _check_plausibility(
    points: np.ndarray, 
    pile_threshold: float = 0.10,
    min_footprint_m2: float = 0.25
) -> tuple[bool, dict]:
    """
    Cheap plausibility check to prevent guardrail from rescuing wrong content.
    
    Checks:
    1. Max height above small minimum (not all floor)
    2. Non-trivial XY footprint (not just a thin strip)
    3. Volume not absurdly low relative to footprint
    
    Args:
        points: Nx3 filtered points
        pile_threshold: Minimum elevation for pile presence
        min_footprint_m2: Minimum XY footprint area
    
    Returns:
        (is_plausible, diagnostics)
    """
    if len(points) < 50:
        return False, {'reason': 'too_few_points'}
    
    X, Y, Z = points[:, 0], points[:, 1], points[:, 2]
    
    # Check 1: Max height above minimum
    y_max = Y.max()
    if y_max < pile_threshold:
        return False, {'reason': 'no_elevation', 'y_max': y_max}
    
    # Check 2: XY footprint area (convex hull or bounding box)
    x_span = X.max() - X.min()
    z_span = Z.max() - Z.min()
    footprint_area = x_span * z_span
    
    if footprint_area < min_footprint_m2:
        return False, {'reason': 'tiny_footprint', 'area_m2': footprint_area}
    
    # Check 3: Estimated volume not absurdly low
    # Quick volume estimate: mean height * footprint
    y_mean = Y.mean()
    quick_vol_m3 = y_mean * footprint_area
    quick_vol_cy = quick_vol_m3 * 1.30795  # m³ → yd³
    
    if quick_vol_cy < 0.05:  # Less than 0.05 yd³ is suspiciously low
        return False, {'reason': 'absurd_volume', 'vol_cy': quick_vol_cy}
    
    return True, {
        'y_max': y_max,
        'footprint_m2': footprint_area,
        'quick_vol_cy': quick_vol_cy
    }


def _filter_masked_points(
    points: np.ndarray,
    floor_noise: float,
    scene_type: str = "residential",
    mask_coverage: float = 0.0,
    depth_at_cap_pct: float = 0.0,
    support_plane_selected: bool = False,
    sr_yfl95: float = 0.20,
    sr_inlier_ratio: float = 0.0
) -> tuple[np.ndarray, dict]:
    """
    Filter 3D points with multi-stage fallback ladder.
    
    Mode hierarchy:
    1. Normal mode (full chain, global metrics)
    2. SP-aware mode (full chain, local metrics)
    3. Minimal mode (Y-band only, conservative)
    4. Unreliable (mark frame as non-donor)
    
    Args:
        points: Nx3 array of rectified points (X=lateral, Y=height, Z=depth)
        floor_noise: Floor flatness P95 from geometry
        scene_type: Scene classification for Y_max selection
        mask_coverage: Fraction of image covered by mask
        depth_at_cap_pct: Fraction of points at depth cap (10m)
        support_plane_selected: Whether a trusted support plane exists
        sr_yfl95: Support ROI P95 residual (local floor noise)
        sr_inlier_ratio: Support ROI inlier ratio
    
    Returns:
        keep_mask: Boolean mask of points to keep
        stats: Diagnostic dictionary
    """
    n_before = len(points)
    if n_before < 50:
        return np.ones(n_before, dtype=bool), {
            'n_before': n_before, 
            'n_after': n_before, 
            'filter_mode': 'skip',
            'guardrail_triggered': False
        }
    
    X, Y, Z = points[:, 0], points[:, 1], points[:, 2]
    Y_max_raw = Y.max()
    
    # === STAGE 1: NORMAL MODE ===
    contaminated, signals = _detect_contamination(Y_max_raw, mask_coverage, depth_at_cap_pct)
    
    if not contaminated:
        # Light filter: Y-band only
        y_mask, Y_min, Y_cap = _y_height_filter(Y, floor_noise, scene_type)
        n_after = y_mask.sum()
        return y_mask, {
            'n_before': n_before,
            'n_after': int(n_after),
            'pct_retained': n_after / max(n_before, 1),
            'filter_mode': 'light',
            'z_split_applied': False,
            'Y_cap': Y_cap,
            'guardrail_triggered': False
        }
    
    # Full filter pipeline
    z_mask, z_applied, z_sep, z_mode = _z_cluster_split_sp_aware(
        Z, Y, support_plane_selected, sr_yfl95, sr_inlier_ratio
    )
    n_after_z = z_mask.sum()
    
    # Y-Band
    y_mask, Y_min, Y_cap = _y_height_filter(Y, floor_noise, scene_type)
    n_after_y = y_mask.sum()
    
    # XZ Multi-Component
    combined = z_mask & y_mask
    n_after_combined = combined.sum()
    
    if combined.sum() > 50:
        xz_mask = _xz_multicomponent_filter(X[combined], Z[combined])
        final = np.zeros(n_before, dtype=bool)
        combined_indices = np.where(combined)[0]
        final[combined_indices[xz_mask]] = True
        n_after_xz = xz_mask.sum()
    else:
        final = combined
        n_after_xz = combined.sum()
    
    n_after = final.sum()
    pct_retained = n_after / max(n_before, 1)
    
    # Stage-by-stage drop counters
    stage_drops = {
        'z_split_kept': int(n_after_z),
        'z_split_dropped': n_before - n_after_z if z_applied else 0,
        'y_band_kept': int(n_after_y),
        'y_band_dropped': n_before - int(n_after_y),
        'combined_kept': int(n_after_combined),
        'xz_cluster_kept': int(n_after_xz),
        'xz_cluster_dropped': n_after_combined - n_after_xz if n_after_combined > 50 else 0,
    }
    
    # === COLLAPSE DETECTION ===
    MIN_RETENTION_PCT = 0.05  # 5% minimum
    
    if pct_retained >= MIN_RETENTION_PCT:
        # Normal mode succeeded
        return final, {
            'n_before': n_before,
            'n_after': int(n_after),
            'pct_retained': pct_retained,
            'filter_mode': 'full',
            'contamination_signals': signals,
            'z_split_applied': z_applied,
            'z_separation_m': z_sep,
            'z_mode': z_mode,
            'Y_cap': Y_cap,
            'stage_drops': stage_drops,
            'donor_eligible': True,
            'guardrail_triggered': False
        }
    
    # === COLLAPSE DETECTED ===
    # Check if SP rescue is warranted
    sp_trusted = (
        support_plane_selected and 
        sr_inlier_ratio >= 0.70 and 
        sr_yfl95 <= 0.15
    )
    
    if not sp_trusted:
        # No trusted SP - mark as unreliable
        return final, {
            'n_before': n_before,
            'n_after': int(n_after),
            'pct_retained': pct_retained,
            'filter_mode': 'unreliable',
            'collapse_reason': 'no_sp_rescue',
            'guardrail_triggered': True,
            'guardrail_mode': 'unreliable',
            'donor_eligible': False
        }
    
    # === STAGE 2: SP-AWARE MODE ===
    print(f"[VOL_FILTER] ⚠️ COLLAPSE GUARDRAIL: {pct_retained:.1%} < {MIN_RETENTION_PCT:.0%}", flush=True)
    print(f"[VOL_FILTER] Retrying with SP-aware mode (sr={sr_inlier_ratio:.2f}, sr_p95={sr_yfl95:.3f})", flush=True)
    
    # Rerun with SP-aware thresholds
    z_mask_sp, z_applied_sp, z_sep_sp, z_mode_sp = _z_cluster_split_sp_aware(
        Z, Y, True, sr_yfl95, sr_inlier_ratio  # Force SP mode
    )
    y_mask_sp, _, _ = _y_height_filter(Y, sr_yfl95, scene_type)  # Use local noise
    combined_sp = z_mask_sp & y_mask_sp
    
    if combined_sp.sum() > 50:
        xz_mask_sp = _xz_multicomponent_filter(X[combined_sp], Z[combined_sp])
        final_sp = np.zeros(n_before, dtype=bool)
        combined_indices_sp = np.where(combined_sp)[0]
        final_sp[combined_indices_sp[xz_mask_sp]] = True
    else:
        final_sp = combined_sp
    
    pct_retained_sp = final_sp.sum() / max(n_before, 1)
    
    if pct_retained_sp >= MIN_RETENTION_PCT:
        # SP-aware mode retention OK - check plausibility
        plausible, plaus_diag = _check_plausibility(final_points[final_sp])
        
        if plausible:
            # SP-aware mode succeeded + plausible
            print(f"[VOL_FILTER] ✓ SP-aware mode succeeded: {pct_retained_sp:.0%} retained, plausible", flush=True)
            return final_sp, {
                'n_before': n_before,
                'n_after': int(final_sp.sum()),
                'pct_retained': pct_retained_sp,
                'filter_mode': 'sp_aware',
                'z_mode': z_mode_sp,
                'guardrail_triggered': True,
                'guardrail_mode': 'sp_aware',
                'plausibility': plaus_diag,
                'donor_eligible': False  # Guardrail frames are non-donor
            }
        else:
            # High retention but implausible - fall through to minimal
            print(f"[VOL_FILTER] SP-aware mode retained {pct_retained_sp:.0%} but IMPLAUSIBLE: {plaus_diag.get('reason')}", flush=True)

    
    # === STAGE 3: MINIMAL MODE ===
    print(f"[VOL_FILTER] SP-aware mode still collapsed ({pct_retained_sp:.1%}), using minimal mode", flush=True)
    
    # Conservative Y-band only, strict threshold
    y_minimal, _, _ = _y_height_filter(Y, max(sr_yfl95, 0.08), scene_type)
    pct_retained_min = y_minimal.sum() / max(n_before, 1)
    
    if pct_retained_min >= MIN_RETENTION_PCT:
        # Minimal mode retention OK - check plausibility
        plausible, plaus_diag = _check_plausibility(final_points[y_minimal])
        
        if plausible:
            print(f"[VOL_FILTER] ✓ Minimal mode succeeded: {pct_retained_min:.0%} retained, plausible", flush=True)
            return y_minimal, {
                'n_before': n_before,
                'n_after': int(y_minimal.sum()),
                'pct_retained': pct_retained_min,
                'filter_mode': 'minimal',
                'guardrail_triggered': True,
                'guardrail_mode': 'minimal',
                'plausibility': plaus_diag,
                'donor_eligible': False
            }
        else:
            # High retention but implausible - mark unreliable
            print(f"[VOL_FILTER] Minimal mode retained {pct_retained_min:.0%} but IMPLAUSIBLE: {plaus_diag.get('reason')}", flush=True)

    
    # === STAGE 4: UNRELIABLE ===
    # Even minimal mode failed - mark as unreliable
    print(f"[VOL_FILTER] ✗ All modes failed, frame marked unreliable", flush=True)
    return final, {
        'n_before': n_before,
        'n_after': int(final.sum()),
        'pct_retained': pct_retained,
        'filter_mode': 'unreliable',
        'collapse_reason': 'all_modes_failed',
        'guardrail_triggered': True,
        'guardrail_mode': 'unreliable',
        'donor_eligible': False
    }



@dataclass
class GridCell:
    """A single cell in the volumetric grid."""
    x_idx: int
    y_idx: int
    x_m: float  # World X coordinate
    z_m: float  # World Z coordinate (depth direction)
    heights: list[float] = field(default_factory=list)
    mask_heights: list[float] = field(default_factory=list)    # v10.5: heights from mask points
    recall_heights: list[float] = field(default_factory=list)  # v10.5: heights from recall points
    trimmed_height: float = 0.0
    owned_by: Optional[str] = None  # item_id if owned by discrete item


@dataclass
class DiscreteItem:
    """A discrete item with assigned volume."""
    item_id: str
    label: str
    volume_cy: float
    source: str  # "catalog", "measured", "bulk_included"
    confidence: float
    subtracted: bool = False  # True if subtracted from bulk
    surcharges: list[str] = field(default_factory=list)


@dataclass
class VolumeDiagnostics:
    """Per-frame diagnostic metrics for failure analysis."""
    mask_area_pct: float = 0.0          # Percent of image pixels in junk mask
    valid_depth_in_mask_pct: float = 0.0  # Percent of masked pixels with valid depth
    num_points_used: int = 0            # Points after all filtering
    grid_active_cells: int = 0          # Cells passing min_points threshold
    p95_height_median: float = 0.0      # Median of per-cell 95th percentile heights
    failure_class: str = ""             # Diagnosed failure mode (if any)


@dataclass
class VolumetricResult:
    """Result of Stage 5 volumetric integration."""
    frame_id: str
    bulk_raw_cy: float = 0.0
    bulk_net_cy: float = 0.0
    discrete_volume_cy: float = 0.0
    frame_volume_cy: float = 0.0
    discrete_items: list[DiscreteItem] = field(default_factory=list)
    grid_cells: list[GridCell] = field(default_factory=list)
    height_field_valid: bool = False
    diagnostics: Optional[VolumeDiagnostics] = None  # Failure diagnosis
    filter_stats: Optional[dict] = None  # Depth-aware filter diagnostics
    
    # === v10.7: Canonical metrics for fusion (authoritative values) ===
    # Footprint metrics (from selected footprint cells)
    footprint_cells_selected: int = 0           # Count of cells in selected footprint
    footprint_m2_selected: float = 0.0          # Area in m² of selected footprint
    
    # Volume metrics (from cells with height >= T_floor)
    volume_cells_selected: int = 0              # Count of volume-contributing cells
    volume_area_m2_selected: float = 0.0        # Area in m² of volume-contributing cells
    
    # Height metrics (computed over selected footprint cells)
    height_p85_footprint: float = 0.0           # P85 height for consensus/cross-fusion
    height_p95_footprint: float = 0.0           # P95 height for geometry noise ratio
    mean_height_footprint: float = 0.0          # Mean height for diagnostics
    
    # Floor-overlap metrics (dual-ratio design)
    leak_ratio_maskseed: float = 0.0            # Fraction of mask-seeded cells on floor (replaces ground_overlap_ratio)
    skirt_ratio_selected: float = 0.0           # Fraction of footprint in [T_footprint, T_floor) band
    
    # Recall/capping diagnostics
    recall_point_fraction: float = 0.0          # Fraction of points from recall (vs mask)
    cells_using_mask_heights_frac: float = 0.0  # Fraction of cells that used mask_heights
    height_cap_m: float = 0.0                   # The MAD-derived cap applied
    pct_cells_clamped: float = 0.0              # Percentage of cells that hit the cap


def _lookup_catalog_volume(label: str) -> Optional[float]:
    """Look up volume from catalog by label."""
    label_clean = label.lower().strip().replace(" ", "_")
    
    # Direct match
    if label_clean in DISCRETE_VOLUME_CATALOG:
        return DISCRETE_VOLUME_CATALOG[label_clean]
        
    # Partial match
    for key, vol in DISCRETE_VOLUME_CATALOG.items():
        if key in label_clean or label_clean in key:
            return vol
            
    return None


def _check_depth_consistency(
    depth_map: np.ndarray,
    bbox: tuple[int, int, int, int],
    image_width: int,
    image_height: int
) -> float:
    """
    Check depth consistency in item region.
    Returns normalized variance (lower = more consistent).
    """
    x1, y1, x2, y2 = bbox
    
    # Clamp to bounds
    x1 = max(0, min(x1, image_width - 1))
    x2 = max(0, min(x2, image_width - 1))
    y1 = max(0, min(y1, image_height - 1))
    y2 = max(0, min(y2, image_height - 1))
    
    if x2 <= x1 or y2 <= y1:
        return 1.0
        
    region = depth_map[y1:y2, x1:x2]
    valid = region[region > 0.1]
    
    if len(valid) < 10:
        return 1.0
        
    # Normalized variance (variance / mean²)
    mean_depth = np.mean(valid)
    if mean_depth < 0.1:
        return 1.0
        
    variance = np.var(valid)
    normalized_var = variance / (mean_depth ** 2)
    
    return float(normalized_var)


def _measure_item_volume(
    item: InstanceMask,
    rectified_cloud: np.ndarray,
    depth_map: np.ndarray,
    scale_factor: float,
    image_width: int,
    image_height: int
) -> float:
    """
    Measure item volume from the rectified point cloud.
    Returns volume in cubic yards.
    """
    # This is a simplified measurement - in production would use
    # convex hull or voxelization of the item's point subset
    x1, y1, x2, y2 = item.bbox
    
    # Estimate bounding box dimensions in world space
    x1 = max(0, min(x1, image_width - 1))
    x2 = max(0, min(x2, image_width - 1))
    y1 = max(0, min(y1, image_height - 1))
    y2 = max(0, min(y2, image_height - 1))
    
    if x2 <= x1 or y2 <= y1:
        return 0.0
        
    region = depth_map[y1:y2, x1:x2]
    valid = region[region > 0.1]
    
    if len(valid) < 10:
        return 0.0
        
    # Estimate depth range (item thickness)
    depth_range = np.percentile(valid, 95) - np.percentile(valid, 5)
    mean_depth = np.mean(valid)
    
    # Estimate width and height in meters (assuming f_px was already applied)
    # Using the area ratio from perception
    area_ratio = item.area_ratio if item.area_ratio > 0 else 0.05
    
    # Rough volume estimate: area_ratio * image_area_at_depth * depth_range
    estimated_width = (x2 - x1) / image_width * mean_depth * 2  # Approximate
    estimated_height = (y2 - y1) / image_height * mean_depth * 2
    
    volume_m3 = estimated_width * estimated_height * depth_range * scale_factor ** 3
    volume_cy = volume_m3 * M3_TO_CY
    
    return max(0.1, min(5.0, volume_cy))  # Clamp to reasonable range


def _build_height_field(
    rectified_cloud: np.ndarray,
    scale_factor: float,
    bulk_mask: Optional[np.ndarray] = None,
    ground_mask: Optional[np.ndarray] = None,  # From Lane D SegFormer (kept for compatibility)
    image_width: int = 0,
    image_height: int = 0,
    pixel_indices: Optional[np.ndarray] = None,  # Nx2 array of (row, col) for each point
    floor_flatness_p95: float = 0.20,  # From geometry - P95(|Y|) of RANSAC floor inliers
    scene_type: str = "residential",  # Scene classification for Y_max selection
    mask_coverage: float = 0.0,  # Fraction of image covered by mask
    support_plane_selected: bool = False,  # v8.6: Support plane trust signal
    sr_yfl95: float = 0.20,  # v8.6: Support ROI P95 residual
    sr_inlier_ratio: float = 0.0  # v8.6: Support ROI inlier ratio
) -> tuple[list[GridCell], float, dict, dict]:
    """
    Build a 2D height field grid from rectified point cloud.
    Uses MASK-FIRST foreground extraction when mask is available.
    
    Args:
        rectified_cloud: Nx3 array of 3D points (X, Y=height, Z=depth)
        scale_factor: Scale correction from calibration
        bulk_mask: Optional HxW boolean mask from Lane B (dilated for recall)
        image_width, image_height: For mask-to-point correspondence (deprecated, use pixel_indices)
        pixel_indices: Nx2 array of (row, col) for each point - REQUIRED for correct mask mapping
        
    Returns:
        (grid_cells, bulk_raw_volume_cy, filter_stats, canonical_metrics)
        canonical_metrics contains authoritative footprint/height/leak metrics for fusion.
    """
    MIN_POINTS_PER_CELL = 8  # Minimum support for height calculation
    MAX_HEIGHT_M = 3.5  # Cap at 3.5m (~11.5ft) - raised from 2.0 to avoid compressing tall piles
    RECALL_PATCH_RADIUS_M = 0.7  # Include points within this distance of pile centroid
    
    if len(rectified_cloud) < 100:
        return [], 0.0, {'filter_mode': 'skip', 'n_before': 0, 'n_after': 0, 'pct_retained': 0.0}, {}
        
    # Scale points
    points = rectified_cloud * scale_factor
    n_points = len(points)
    
    # v10.4: Log XYZ extents to verify scaling
    if abs(scale_factor - 1.0) > 0.01:
        x_range_raw = np.max(rectified_cloud[:, 0]) - np.min(rectified_cloud[:, 0])
        z_range_raw = np.max(rectified_cloud[:, 2]) - np.min(rectified_cloud[:, 2])
        y_max_raw = np.max(rectified_cloud[:, 1])
        x_range_scaled = np.max(points[:, 0]) - np.min(points[:, 0])
        z_range_scaled = np.max(points[:, 2]) - np.min(points[:, 2])
        y_max_scaled = np.max(points[:, 1])
        print(f"[SCALE_DIAG] scale_factor={scale_factor:.3f}")
        print(f"[SCALE_DIAG] X_range: {x_range_raw:.2f}m → {x_range_scaled:.2f}m ({x_range_scaled/x_range_raw:.3f}x)")
        print(f"[SCALE_DIAG] Z_range: {z_range_raw:.2f}m → {z_range_scaled:.2f}m ({z_range_scaled/z_range_raw:.3f}x)")
        print(f"[SCALE_DIAG] Y_max: {y_max_raw:.2f}m → {y_max_scaled:.2f}m ({y_max_scaled/y_max_raw:.3f}x)")

    
    # MASK-FIRST FOREGROUND SELECTION
    # If we have a bulk mask, use it as primary selector
    # v10.3 FIX A: Track mask vs recall points separately - recall cannot create footprint
    mask_point_indices = set()  # Track which points are from mask (for footprint)
    
    if bulk_mask is not None and pixel_indices is not None:
        mask_h, mask_w = bulk_mask.shape
        depth_h, depth_w = image_height, image_width  # For coordinate scaling
        
        # VECTORIZED mask lookup (10x+ faster than loop)
        rows = pixel_indices[:, 0]
        cols = pixel_indices[:, 1]
        
        # Scale to mask dimensions
        if depth_h > 0:
            mask_rows = np.clip((rows * mask_h / depth_h).astype(int), 0, mask_h - 1)
        else:
            mask_rows = np.clip(rows.astype(int), 0, mask_h - 1)
        if depth_w > 0:
            mask_cols = np.clip((cols * mask_w / depth_w).astype(int), 0, mask_w - 1)
        else:
            mask_cols = np.clip(cols.astype(int), 0, mask_w - 1)
        
        # Vectorized mask lookup
        in_mask = bulk_mask[mask_rows, mask_cols]
        foreground_indices = np.where(in_mask)[0]
        
        if len(foreground_indices) > 50:
            foreground_points = points[foreground_indices]
            
            # v10.3: Track mask point indices in final_points array
            # These are the ONLY points that can seed footprint cells
            mask_point_indices = set(range(len(foreground_indices)))
            
            # Compute pile centroid from masked points
            pile_centroid_x = np.mean(foreground_points[:, 0])
            pile_centroid_z = np.mean(foreground_points[:, 2])
            
            # RECALL PATCH: Also include points near the pile that mask might have missed
            # (captures dark bags, thin objects, occluded regions adjacent to pile)
            # v10.3: Recall points can contribute VOLUME but NOT FOOTPRINT
            distances_xz = np.sqrt(
                (points[:, 0] - pile_centroid_x)**2 + 
                (points[:, 2] - pile_centroid_z)**2
            )
            
            # Include points within RECALL_PATCH_RADIUS that are above floor
            recall_mask = (
                (distances_xz < RECALL_PATCH_RADIUS_M) & 
                (points[:, 1] > 0.02)  # At least 2cm above floor
            )
            
            # Combine mask foreground + recall patch (vectorized)
            foreground_set = set(foreground_indices)
            recall_indices = np.where(recall_mask)[0]
            recall_only = np.array([idx for idx in recall_indices if idx not in foreground_set])
            
            all_foreground = np.concatenate([foreground_indices, recall_only]) if len(recall_only) > 0 else foreground_indices
            
            final_points = points[all_foreground]
            # mask_point_indices already set above (indices 0 to len(foreground_indices)-1)
            
            print(f"[Volumetrics] Mask-first: {len(foreground_points)} masked + {len(recall_only)} recall = {len(final_points)} total")
        else:
            # Mask didn't provide enough points - fall back to height-only filter
            final_points = points[points[:, 1] > 0.02]
            mask_point_indices = set(range(len(final_points)))  # All points are "mask" in fallback
            print(f"[Volumetrics] Mask too sparse ({len(foreground_indices)} pts), using height filter")
    else:
        # No mask available - use simple height filter (above floor only)
        final_points = points[points[:, 1] > 0.02]
        mask_point_indices = set(range(len(final_points)))  # All points are "mask" in fallback
        print(f"[Volumetrics] No mask - height filter: {len(final_points)} points above floor")
    
    if len(final_points) < 50:
        return [], 0.0, {'filter_mode': 'skip', 'n_before': 0, 'n_after': 0}
    
    # ========== DEPTH-AWARE BACKGROUND FILTERING ==========
    # Remove trees, fences, walls from masked point set
    filter_mask, filter_stats = _filter_masked_points(
        points=final_points,
        floor_noise=floor_flatness_p95,
        scene_type=scene_type,
        mask_coverage=mask_coverage,
        support_plane_selected=support_plane_selected,  # v8.6
        sr_yfl95=sr_yfl95,  # v8.6
        sr_inlier_ratio=sr_inlier_ratio  # v8.6
    )
    filtered_points = final_points[filter_mask]
    
    # v10.3 FIX A: Track which filtered points are from mask (for footprint seeding)
    # Vectorized: create mask flags using numpy advanced indexing
    mask_flags_full = np.zeros(len(final_points), dtype=bool)
    mask_indices_array = np.array(list(mask_point_indices))
    if len(mask_indices_array) > 0:
        valid_mask = mask_indices_array < len(mask_flags_full)
        mask_flags_full[mask_indices_array[valid_mask]] = True
    filtered_mask_flags = mask_flags_full[filter_mask]
    n_mask_after_filter = filtered_mask_flags.sum()
    n_recall_after_filter = len(filtered_points) - n_mask_after_filter
    print(f"[VOL_FILTER] After filter: {n_mask_after_filter} mask pts, {n_recall_after_filter} recall pts")
    
    print(f"[VOL_FILTER] mode={filter_stats['filter_mode']}, "
          f"{filter_stats['n_before']} → {filter_stats['n_after']} "
          f"({filter_stats['pct_retained']:.0%} retained)")
    if filter_stats.get('z_split_applied'):
        print(f"[VOL_FILTER] Z-split: separation={filter_stats.get('z_separation_m', 0):.1f}m")
    
    # v6.8.0: Log per-stage drops if available
    if 'stage_drops' in filter_stats:
        sd = filter_stats['stage_drops']
        print(f"[VOL_FILTER_STAGES] z_split={sd['z_split_kept']}/{filter_stats['n_before']}, "
              f"y_band={sd['y_band_kept']}/{filter_stats['n_before']}, "
              f"combined={sd['combined_kept']}, xz_cluster={sd['xz_cluster_kept']}")
    
    # Guard: if heavy filtering, flag for fusion
    if filter_stats['pct_retained'] < 0.20:
        print(f"[VOL_FILTER] ⚠️ Heavy filtering detected - frame may be unreliable")
    
    final_points = filtered_points
    # ======================================================
    
    if len(final_points) < 50:
        return [], 0.0, filter_stats
    
    # Determine grid bounds from final points
    x_min_grid, x_max_grid = np.min(final_points[:, 0]), np.max(final_points[:, 0])
    z_min_grid, z_max_grid = np.min(final_points[:, 2]), np.max(final_points[:, 2])
    
    # Create grid
    n_cells_x = max(1, int((x_max_grid - x_min_grid) / GRID_CELL_SIZE_M))
    n_cells_z = max(1, int((z_max_grid - z_min_grid) / GRID_CELL_SIZE_M))
    
    # Cap grid size for performance
    n_cells_x = min(n_cells_x, 100)
    n_cells_z = min(n_cells_z, 100)
    
    grid = {}
    for i in range(n_cells_x):
        for j in range(n_cells_z):
            cell_x = x_min_grid + (i + 0.5) * GRID_CELL_SIZE_M
            cell_z = z_min_grid + (j + 0.5) * GRID_CELL_SIZE_M
            grid[(i, j)] = GridCell(x_idx=i, y_idx=j, x_m=cell_x, z_m=cell_z)
    
    # v10.3 FIX A: Track cells seeded by mask points vs recall points
    # Only mask-seeded cells can be part of the footprint
    mask_seeded_cells = set()  # Cells that have at least one mask point
    
    # Assign points to cells
    for idx, point in enumerate(final_points):
        x, y, z = point
        if y <= 0:  # Below or at floor level
            continue
            
        i = int((x - x_min_grid) / GRID_CELL_SIZE_M)
        j = int((z - z_min_grid) / GRID_CELL_SIZE_M)
        
        i = max(0, min(i, n_cells_x - 1))
        j = max(0, min(j, n_cells_z - 1))
        
        grid[(i, j)].heights.append(y)
        
        # v10.5: Track heights by source (mask vs recall)
        if filtered_mask_flags[idx]:
            grid[(i, j)].mask_heights.append(y)
            mask_seeded_cells.add((i, j))
        else:
            grid[(i, j)].recall_heights.append(y)
    
    print(f"[VOL_DEBUG] Mask-seeded cells: {len(mask_seeded_cells)} / {len(grid)} total")
    
    # Compute trimmed heights and volume with STABILIZERS
    # First pass: collect all cell heights for MAD calculation and floor noise estimation
    all_cell_heights = []
    mask_height_cells = 0  # v10.5: track how many cells used mask-only heights
    for cell in grid.values():
        # v10.5: Prefer mask heights to prevent recall from inflating peaks
        if len(cell.mask_heights) >= MIN_POINTS_PER_CELL:
            cell.trimmed_height = np.percentile(cell.mask_heights, HEIGHT_PERCENTILE)
            mask_height_cells += 1
        elif len(cell.heights) >= MIN_POINTS_PER_CELL:
            # Fallback: use all heights (recall-heavy cells or recall-only)
            cell.trimmed_height = np.percentile(cell.heights, HEIGHT_PERCENTILE)
        
        if cell.trimmed_height > 0:
            all_cell_heights.append(cell.trimmed_height)
    
    print(f"[VOL_DEBUG] v10.5: mask_heights used for {mask_height_cells} cells")
    
    if not all_cell_heights:
        return [], 0.0, filter_stats, {}
    
    # Compute median and MAD for outlier detection
    all_cell_heights = np.array(all_cell_heights)
    median_height = np.median(all_cell_heights)
    mad = np.median(np.abs(all_cell_heights - median_height))
    mad_derived_cap = median_height + 3 * mad * 1.4826
    height_cap = min(MAX_HEIGHT_M, mad_derived_cap)
    
    # Diagnostic: log per-cell height percentiles (p50/p75/p90/p95/p98) for selected cells
    cell_height_p50 = np.percentile(all_cell_heights, 50)
    cell_height_p75 = np.percentile(all_cell_heights, 75)
    cell_height_p90 = np.percentile(all_cell_heights, 90)
    cell_height_p95 = np.percentile(all_cell_heights, 95)
    cell_height_p98 = np.percentile(all_cell_heights, 98)
    print(f"[VOL_DEBUG] cell_heights: p50={cell_height_p50:.3f}m, p75={cell_height_p75:.3f}m, p90={cell_height_p90:.3f}m, p95={cell_height_p95:.3f}m, p98={cell_height_p98:.3f}m")
    print(f"[VOL_DEBUG] height_cap: MAX_HEIGHT_M={MAX_HEIGHT_M:.1f}m, mad_derived={mad_derived_cap:.3f}m, final_cap={height_cap:.3f}m")
    
    # ADAPTIVE MIN_CELL_HEIGHT based on floor noise (generalizes across surfaces)
    # STEP A FIX: Use floor_flatness_p95 from geometry (RANSAC floor inliers)
    # This is the P95(|Y|) from rectified floor candidates - much cleaner than ground_mask
    # Avoids "ground mask includes pile" contamination issues
    
    floor_noise_raw = floor_flatness_p95
    floor_noise = np.clip(floor_noise_raw, 0.02, 0.20)  # Clamp to 2-20cm
    
    print(f"[VOL_DEBUG] floor_noise_raw={floor_noise_raw:.4f}m (from geometry floor_flatness_p95)")
    
    # v10.2: FIXED THRESHOLDS - decouple from floor_noise for cross-frame stability
    # Previously: adaptive thresholds caused footprint to swing +38% between views
    # Now: constant thresholds ensure footprint stability unless mask truly changes
    T_footprint = 0.08  # 8cm for footprint activation (fixed)
    T_floor = 0.12      # 12cm for volume integration (fixed)
    
    print(f"[VOL_DEBUG] floor_noise={floor_noise:.3f}m, T_footprint={T_footprint:.3f}m, T_floor={T_floor:.3f}m")
    
    # Second pass: compute per-cell heights with stabilizers + clamping diagnostics
    num_cells_clamped = 0
    total_cells_with_height = 0
    for cell in grid.values():
        if len(cell.heights) >= MIN_POINTS_PER_CELL:
            total_cells_with_height += 1
            # Apply outlier guard (cap extreme heights)
            if cell.trimmed_height > height_cap:
                num_cells_clamped += 1
            cell.trimmed_height = min(cell.trimmed_height, height_cap)
        else:
            cell.trimmed_height = 0.0
    
    pct_cells_clamped = (num_cells_clamped / total_cells_with_height * 100) if total_cells_with_height > 0 else 0
    print(f"[VOL_DEBUG] clamping: num_cells_clamped={num_cells_clamped}, total_cells={total_cells_with_height}, pct_clamped={pct_cells_clamped:.1f}%")
    
    # v10.3 FIX A: Build footprint ONLY from mask-seeded cells
    # Recall points can contribute volume within this footprint, but cannot expand it
    active_cell_coords = []
    recall_only_cells = 0
    for cell in grid.values():
        if cell.trimmed_height >= T_footprint:
            cell_key = (cell.x_idx, cell.y_idx)
            if cell_key in mask_seeded_cells:
                # This cell has mask points - include in footprint
                active_cell_coords.append((cell.x_idx, cell.y_idx, cell))
            else:
                # This cell only has recall points - cannot seed footprint
                recall_only_cells += 1
    
    if recall_only_cells > 0:
        print(f"[VOL_DEBUG] FIX_A: Excluded {recall_only_cells} recall-only cells from footprint")
    
    if not active_cell_coords:
        return list(grid.values()), 0.0, filter_stats
    
    # ADAPTIVE PILE-LIKE THRESHOLD
    # T_pile = T_footprint + 0.04m, clamped to [0.08, 0.18]
    # This preserves low-profile pile edges on clean floors
    T_pile = np.clip(T_footprint + 0.04, 0.08, 0.18)
    
    # PILE COMPONENT FILTERING using adaptive thresholds
    from scipy import ndimage
    
    # Build binary grid
    x_indices = [c[0] for c in active_cell_coords]
    y_indices = [c[1] for c in active_cell_coords]
    min_x, max_x = min(x_indices), max(x_indices)
    min_y, max_y = min(y_indices), max(y_indices)
    
    grid_w = max_x - min_x + 1
    grid_h = max_y - min_y + 1
    
    binary_grid = np.zeros((grid_h, grid_w), dtype=np.int32)
    cell_lookup = {}
    for x_idx, y_idx, cell in active_cell_coords:
        gx, gy = x_idx - min_x, y_idx - min_y
        binary_grid[gy, gx] = 1
        cell_lookup[(gx, gy)] = cell
    
    # Find connected components with 8-connectivity for better pile merging
    structure = np.ones((3, 3), dtype=np.int32)  # 8-connectivity
    labeled, num_features = ndimage.label(binary_grid, structure=structure)
    
    if num_features == 0:
        return list(grid.values()), 0.0, filter_stats
    
    # Collect pile-like components
    selected_cells = set()
    for comp_id in range(1, num_features + 1):
        comp_mask = labeled == comp_id
        comp_cells = []
        for gy, gx in zip(*np.where(comp_mask)):
            if (gx, gy) in cell_lookup:
                comp_cells.append(cell_lookup[(gx, gy)])
        
        if not comp_cells:
            continue
        
        # Use p75 height instead of median for pile-likeness (preserves mixed-height components)
        heights = [c.trimmed_height for c in comp_cells]
        p75_h = np.percentile(heights, 75)
        area_m2 = len(comp_cells) * (GRID_CELL_SIZE_M ** 2)
        
        # Adaptive pile-likeness using T_pile
        is_pile_like = p75_h >= T_pile
        is_small_debris = area_m2 < 0.5 and p75_h >= T_footprint  # Small but elevated
        is_flat_floor = p75_h < T_footprint and area_m2 > 1.0  # Large flat region
        
        if (is_pile_like or is_small_debris) and not is_flat_floor:
            selected_cells.update(id(c) for c in comp_cells)
    
    # Compute final volume from selected pile components using STRICTER T_floor
    total_volume_m3 = 0.0
    active_cells = 0
    footprint_cells = 0  # Track footprint separately
    cells = []
    
    for cell in grid.values():
        if id(cell) in selected_cells:
            footprint_cells += 1  # All selected cells contribute to footprint
            if cell.trimmed_height >= T_floor:  # Only cells above T_floor contribute to volume
                cell_volume = GRID_CELL_SIZE_M ** 2 * cell.trimmed_height
                total_volume_m3 += cell_volume
                active_cells += 1
        cells.append(cell)
    
    bulk_raw_cy = total_volume_m3 * M3_TO_CY
    
    # Log footprint stats for debugging
    footprint_m2 = footprint_cells * (GRID_CELL_SIZE_M ** 2)  # Use footprint_cells
    volume_cells_m2 = active_cells * (GRID_CELL_SIZE_M ** 2)
    if active_cells > 0:
        avg_height = total_volume_m3 / volume_cells_m2
        print(f"[Volumetrics] T_footprint={T_footprint:.2f}m, T_floor={T_floor:.2f}m")
        print(f"[Volumetrics] Footprint cells: {footprint_cells} ({footprint_m2:.1f}m²), Volume cells: {active_cells} ({volume_cells_m2:.1f}m²), Avg height: {avg_height:.2f}m")
    
    # === DIAGNOSTIC DEBUG BLOCK ===
    cell_area_m2 = GRID_CELL_SIZE_M ** 2
    
    # Collect heights from volume-contributing cells (above T_floor)
    active_heights = []
    for cell in grid.values():
        if id(cell) in selected_cells and cell.trimmed_height >= T_floor:
            active_heights.append(cell.trimmed_height)
    
    mean_cell_height_m = np.mean(active_heights) if active_heights else 0.0
    
    # Recompute volume step-by-step
    bulk_m3_check = volume_cells_m2 * mean_cell_height_m
    bulk_cy_check = bulk_m3_check * M3_TO_CY
    
    print(f"[VOL_DEBUG] CELL_SIZE_M={GRID_CELL_SIZE_M:.2f}, cell_area_m2={cell_area_m2:.4f}")
    print(f"[VOL_DEBUG] footprint_cells={footprint_cells}, footprint_m2={footprint_m2:.3f}")
    print(f"[VOL_DEBUG] volume_cells={active_cells}, volume_area_m2={volume_cells_m2:.3f}")
    print(f"[VOL_DEBUG] mean_cell_height_m={mean_cell_height_m:.3f}")
    print(f"[VOL_DEBUG] bulk_m3 (area×height)={bulk_m3_check:.4f}")
    print(f"[VOL_DEBUG] bulk_cy (m3×1.308)={bulk_cy_check:.3f}")
    print(f"[VOL_DEBUG] raw_cy (actual output)={bulk_raw_cy:.3f}")
    print(f"[VOL_DEBUG] total_volume_m3 (loop sum)={total_volume_m3:.4f}")
    print(f"[VOL_DEBUG] scale_factor applied={scale_factor:.3f}")
    # === END DEBUG BLOCK ===
    
    # === v10.7: CANONICAL METRICS for fusion (authoritative values) ===
    # These metrics are computed over the SAME cell sets that volumetrics integrates
    
    # 1. Height percentiles over selected footprint cells (>= T_footprint)
    selected_footprint_heights = [
        grid[ck].trimmed_height for ck in grid.keys()
        if id(grid[ck]) in selected_cells and grid[ck].trimmed_height >= T_footprint
    ]
    
    height_p85_footprint = float(np.percentile(selected_footprint_heights, 85)) if selected_footprint_heights else 0.0
    height_p95_footprint = float(np.percentile(selected_footprint_heights, 95)) if selected_footprint_heights else 0.0
    mean_height_footprint = float(np.mean(selected_footprint_heights)) if selected_footprint_heights else 0.0
    
    # 2. Leak ratio: fraction of mask-seeded cells that leaked onto floor (h < T_footprint)
    mask_seeded_with_height = [
        ck for ck in mask_seeded_cells
        if ck in grid and grid[ck].trimmed_height > 0
    ]
    floor_leak_cells = sum(
        1 for ck in mask_seeded_with_height
        if grid[ck].trimmed_height < T_footprint
    )
    leak_ratio_maskseed = floor_leak_cells / max(len(mask_seeded_with_height), 1)
    
    # 3. Skirt ratio: fraction of selected footprint in [T_footprint, T_floor) band
    selected_footprint_cells_list = [
        ck for ck in grid.keys()
        if id(grid[ck]) in selected_cells and grid[ck].trimmed_height >= T_footprint
    ]
    skirt_cells_count = sum(
        1 for ck in selected_footprint_cells_list
        if T_footprint <= grid[ck].trimmed_height < T_floor
    )
    skirt_ratio_selected = skirt_cells_count / max(len(selected_footprint_cells_list), 1)
    
    # 4. Recall/capping diagnostics
    n_total_filtered = len(mask_point_indices) + len(final_points) - len(mask_point_indices)
    n_mask_points = len([i for i in range(len(final_points)) if filtered_mask_flags[i]])
    n_recall_points = len(final_points) - n_mask_points
    recall_point_fraction = n_recall_points / max(len(final_points), 1)
    
    cells_using_mask_heights_frac = mask_height_cells / max(len([c for c in grid.values() if c.trimmed_height > 0]), 1)
    
    pct_cells_clamped = sum(1 for c in grid.values() if c.trimmed_height >= height_cap) / max(len([c for c in grid.values() if c.trimmed_height > 0]), 1)
    
    canonical = {
        'footprint_cells_selected': footprint_cells,
        'footprint_m2_selected': footprint_m2,
        'volume_cells_selected': active_cells,
        'volume_area_m2_selected': volume_cells_m2,
        'height_p85_footprint': height_p85_footprint,
        'height_p95_footprint': height_p95_footprint,
        'mean_height_footprint': mean_height_footprint,
        'leak_ratio_maskseed': leak_ratio_maskseed,
        'skirt_ratio_selected': skirt_ratio_selected,
        'recall_point_fraction': recall_point_fraction,
        'cells_using_mask_heights_frac': cells_using_mask_heights_frac,
        'height_cap_m': height_cap,
        'pct_cells_clamped': pct_cells_clamped,
    }
    
    print(f"[CANONICAL] footprint={footprint_m2:.2f}m², volume_area={volume_cells_m2:.2f}m²")
    print(f"[CANONICAL] height_p85={height_p85_footprint:.3f}m, height_p95={height_p95_footprint:.3f}m")
    print(f"[CANONICAL] leak_ratio={leak_ratio_maskseed:.2%}, skirt_ratio={skirt_ratio_selected:.2%}")
    
    return cells, bulk_raw_cy, filter_stats, canonical


def run_volumetrics(
    frame_id: str,
    instances: list[InstanceMask],
    rectified_cloud: Optional[np.ndarray],
    depth_map: Optional[np.ndarray],
    scale_factor: float,
    image_width: int,
    image_height: int,
    bulk_mask_np: Optional[np.ndarray] = None,
    ground_mask_np: Optional[np.ndarray] = None,  # From Lane D SegFormer (kept for compatibility)
    pixel_indices: Optional[np.ndarray] = None,  # Nx2 array of (row, col) for each point
    floor_flatness_p95: float = 0.20,  # From geometry - P95(|Y|) of RANSAC floor inliers
    scene_type: str = "residential",  # Scene classification for Y_max selection
    mask_coverage: float = 0.0,  # Fraction of image covered by mask
    # Mode config from GPT-4o router
    z_split_strict: bool = False,  # Use stricter Z-split threshold
    density_crop: bool = False,  # Enable density-based cropping
    height_cap_m: float = 2.5,  # Maximum height cap in meters
    # v8.6: Support plane metrics for filter collapse guardrail
    support_plane_selected: bool = False,
    sr_yfl95: float = 0.20,
    sr_inlier_ratio: float = 0.0
) -> VolumetricResult:
    """
    Stage 5 Entry Point: Calculate truck-bed volume.
    
    Args:
        frame_id: Unique frame identifier
        instances: Detected items from Stage 2
        rectified_cloud: Floor-aligned point cloud from Stage 3
        depth_map: Depth map from Stage 3
        scale_factor: Scale correction from Stage 4
        image_width, image_height: Image dimensions
        bulk_mask_np: Optional HxW boolean mask from Lane B (dilated for recall)
        ground_mask_np: Optional HxW boolean mask from Lane D (ground/floor from SegFormer)
        pixel_indices: Nx2 array of (row, col) pixel coordinates for each point
        floor_flatness_p95: From geometry - P95(|Y|) of RANSAC floor inliers
        scene_type: Scene classification for Y_max selection
        mask_coverage: Fraction of image covered by mask
        support_plane_selected: v8.6 - Whether a trusted support plane exists
        sr_yfl95: v8.6 - Support ROI P95 residual (local floor noise)
        sr_inlier_ratio: v8.6 - Support ROI inlier ratio
        
    Returns:
        VolumetricResult with bulk and discrete volumes
    """
    result = VolumetricResult(frame_id=frame_id)
    
    # Step A: Build height field from point cloud (MASK-FIRST when available)
    if rectified_cloud is not None and len(rectified_cloud) > 0:
        cells, bulk_raw, filter_stats, canonical = _build_height_field(
            rectified_cloud, 
            scale_factor,
            bulk_mask=bulk_mask_np,
            ground_mask=ground_mask_np,  # Lane D (kept for compatibility)
            image_width=image_width,
            image_height=image_height,
            pixel_indices=pixel_indices,
            floor_flatness_p95=floor_flatness_p95,  # From geometry RANSAC
            scene_type=scene_type,
            mask_coverage=mask_coverage,
            support_plane_selected=support_plane_selected,  # v8.6
            sr_yfl95=sr_yfl95,  # v8.6
            sr_inlier_ratio=sr_inlier_ratio  # v8.6
        )
        result.grid_cells = cells
        result.bulk_raw_cy = bulk_raw
        result.height_field_valid = True
        # Store filter stats for fusion weight calculation
        result.filter_stats = filter_stats
        
        # === v10.7: Populate canonical metrics from _build_height_field ===
        if canonical:
            result.footprint_cells_selected = canonical.get('footprint_cells_selected', 0)
            result.footprint_m2_selected = canonical.get('footprint_m2_selected', 0.0)
            result.volume_cells_selected = canonical.get('volume_cells_selected', 0)
            result.volume_area_m2_selected = canonical.get('volume_area_m2_selected', 0.0)
            result.height_p85_footprint = canonical.get('height_p85_footprint', 0.0)
            result.height_p95_footprint = canonical.get('height_p95_footprint', 0.0)
            result.mean_height_footprint = canonical.get('mean_height_footprint', 0.0)
            result.leak_ratio_maskseed = canonical.get('leak_ratio_maskseed', 0.0)
            result.skirt_ratio_selected = canonical.get('skirt_ratio_selected', 0.0)
            result.recall_point_fraction = canonical.get('recall_point_fraction', 0.0)
            result.cells_using_mask_heights_frac = canonical.get('cells_using_mask_heights_frac', 0.0)
            result.height_cap_m = canonical.get('height_cap_m', 0.0)
            result.pct_cells_clamped = canonical.get('pct_cells_clamped', 0.0)
    else:
        result.bulk_raw_cy = 0.0
        result.height_field_valid = False
    
    # Step B: Process discrete items with privileged subtraction
    measured_volume_to_subtract = 0.0
    
    for item in instances:
        # Look up catalog volume first
        catalog_vol = _lookup_catalog_volume(item.label)
        
        # Check if eligible for privileged subtraction
        can_subtract = False
        depth_consistent = True
        
        if depth_map is not None:
            depth_var = _check_depth_consistency(
                depth_map, item.bbox, image_width, image_height
            )
            depth_consistent = depth_var < DEPTH_CONSISTENCY_THRESHOLD
            
        if item.confidence >= DETECTION_CONF_THRESHOLD and depth_consistent:
            can_subtract = True
            
        if catalog_vol is not None and can_subtract:
            # High-confidence discrete item - use catalog volume
            discrete = DiscreteItem(
                item_id=item.instance_id,
                label=item.label,
                volume_cy=catalog_vol,
                source="catalog",
                confidence=item.confidence,
                subtracted=True
            )
            result.discrete_items.append(discrete)
            result.discrete_volume_cy += catalog_vol
            
            # Measure and subtract from bulk
            if rectified_cloud is not None:
                measured = _measure_item_volume(
                    item, rectified_cloud, depth_map, 
                    scale_factor, image_width, image_height
                )
                measured_volume_to_subtract += measured
                
        elif catalog_vol is not None:
            # Low confidence - include in discrete but don't subtract from bulk
            discrete = DiscreteItem(
                item_id=item.instance_id,
                label=item.label,
                volume_cy=catalog_vol,
                source="catalog",
                confidence=item.confidence,
                subtracted=False
            )
            result.discrete_items.append(discrete)
            result.discrete_volume_cy += catalog_vol
            
        else:
            # Unknown item - leave in bulk, add to list as detected
            discrete = DiscreteItem(
                item_id=item.instance_id,
                label=item.label,
                volume_cy=0.0,
                source="bulk_included",
                confidence=item.confidence,
                subtracted=False
            )
            result.discrete_items.append(discrete)
    
    # Step C: Compute net bulk and frame total
    result.bulk_net_cy = max(0, result.bulk_raw_cy - measured_volume_to_subtract)
    result.frame_volume_cy = result.bulk_net_cy + result.discrete_volume_cy
    
    return result
