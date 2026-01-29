"""
Stage 5: Volumetric Integration (The Calculation)
Goal: "Truck Bed" volume - measure the terrain, subtract the knowns.
"""

from dataclasses import dataclass, field
from typing import Optional
import numpy as np

from .perception import InstanceMask


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


@dataclass
class GridCell:
    """A single cell in the volumetric grid."""
    x_idx: int
    y_idx: int
    x_m: float  # World X coordinate
    z_m: float  # World Z coordinate (depth direction)
    heights: list[float] = field(default_factory=list)
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
    floor_flatness_p95: float = 0.20  # From geometry - P95(|Y|) of RANSAC floor inliers
) -> tuple[list[GridCell], float]:
    """
    Build a 2D height field grid from rectified point cloud.
    Uses MASK-FIRST foreground extraction when mask is available.
    
    Args:
        rectified_cloud: Nx3 array of 3D points (X, Y=height, Z=depth)
        scale_factor: Scale correction from calibration
        bulk_mask: Optional HxW boolean mask from Lane B (dilated for recall)
        image_width, image_height: For mask-to-point correspondence (deprecated, use pixel_indices)
        pixel_indices: Nx2 array of (row, col) for each point - REQUIRED for correct mask mapping
        
    Returns (grid_cells, bulk_raw_volume_cy).
    """
    MIN_POINTS_PER_CELL = 8  # Minimum support for height calculation
    MAX_HEIGHT_M = 3.5  # Cap at 3.5m (~11.5ft) - raised from 2.0 to avoid compressing tall piles
    RECALL_PATCH_RADIUS_M = 0.7  # Include points within this distance of pile centroid
    
    if len(rectified_cloud) < 100:
        return [], 0.0
        
    # Scale points
    points = rectified_cloud * scale_factor
    n_points = len(points)
    
    # MASK-FIRST FOREGROUND SELECTION
    # If we have a bulk mask, use it as primary selector
    if bulk_mask is not None and pixel_indices is not None:
        mask_h, mask_w = bulk_mask.shape
        depth_h, depth_w = image_height, image_width  # For coordinate scaling
        
        # Use pixel_indices for correct point-to-pixel mapping
        foreground_indices = []
        
        for idx in range(n_points):
            # Get the actual pixel coordinates from pixel_indices
            row, col = pixel_indices[idx]
            
            # Scale to mask dimensions if different from depth dimensions
            mask_row = int(row * mask_h / depth_h) if depth_h > 0 else int(row)
            mask_col = int(col * mask_w / depth_w) if depth_w > 0 else int(col)
            
            mask_row = max(0, min(mask_row, mask_h - 1))
            mask_col = max(0, min(mask_col, mask_w - 1))
            
            if bulk_mask[mask_row, mask_col]:
                foreground_indices.append(idx)
        
        if len(foreground_indices) > 50:
            foreground_points = points[foreground_indices]
            
            # Compute pile centroid from masked points
            pile_centroid_x = np.mean(foreground_points[:, 0])
            pile_centroid_z = np.mean(foreground_points[:, 2])
            
            # RECALL PATCH: Also include points near the pile that mask might have missed
            # (captures dark bags, thin objects, occluded regions adjacent to pile)
            distances_xz = np.sqrt(
                (points[:, 0] - pile_centroid_x)**2 + 
                (points[:, 2] - pile_centroid_z)**2
            )
            
            # Include points within RECALL_PATCH_RADIUS that are above floor
            recall_mask = (
                (distances_xz < RECALL_PATCH_RADIUS_M) & 
                (points[:, 1] > 0.02)  # At least 2cm above floor
            )
            
            # Combine mask foreground + recall patch
            all_foreground = set(foreground_indices)
            recall_indices = np.where(recall_mask)[0]
            all_foreground.update(recall_indices)
            
            final_points = points[list(all_foreground)]
            print(f"[Volumetrics] Mask-first: {len(foreground_points)} masked + {len(recall_indices)} recall = {len(final_points)} total")
        else:
            # Mask didn't provide enough points - fall back to height-only filter
            final_points = points[points[:, 1] > 0.02]
            print(f"[Volumetrics] Mask too sparse ({len(foreground_indices)} pts), using height filter")
    else:
        # No mask available - use simple height filter (above floor only)
        final_points = points[points[:, 1] > 0.02]
        print(f"[Volumetrics] No mask - height filter: {len(final_points)} points above floor")
    
    if len(final_points) < 50:
        return [], 0.0
    
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
    
    # Assign points to cells
    for point in final_points:
        x, y, z = point
        if y <= 0:  # Below or at floor level
            continue
            
        i = int((x - x_min_grid) / GRID_CELL_SIZE_M)
        j = int((z - z_min_grid) / GRID_CELL_SIZE_M)
        
        i = max(0, min(i, n_cells_x - 1))
        j = max(0, min(j, n_cells_z - 1))
        
        grid[(i, j)].heights.append(y)
    
    # Compute trimmed heights and volume with STABILIZERS
    # First pass: collect all cell heights for MAD calculation and floor noise estimation
    all_cell_heights = []
    for cell in grid.values():
        if len(cell.heights) >= MIN_POINTS_PER_CELL:
            cell.trimmed_height = np.percentile(cell.heights, HEIGHT_PERCENTILE)
            all_cell_heights.append(cell.trimmed_height)
    
    if not all_cell_heights:
        return [], 0.0
    
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
    
    # FIX A: DUAL THRESHOLD - decouple "floor cleanup" from "pile footprint"
    # T_footprint: softer threshold for cell activation and footprint growth
    # T_floor: stricter threshold for volume integration (revenue-safe denoising)
    T_footprint = np.clip(floor_noise + 0.02, 0.04, 0.10)  # 4-10cm for footprint
    T_floor = np.clip(floor_noise + 0.06, 0.08, 0.14)      # 8-14cm for volume (original)
    
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
    
    # Build grid for connected component analysis using SOFTER T_footprint
    active_cell_coords = []
    for cell in grid.values():
        if cell.trimmed_height >= T_footprint:  # Use softer threshold for footprint
            active_cell_coords.append((cell.x_idx, cell.y_idx, cell))
    
    if not active_cell_coords:
        return list(grid.values()), 0.0
    
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
        return list(grid.values()), 0.0
    
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
    
    return cells, bulk_raw_cy


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
    floor_flatness_p95: float = 0.20  # From geometry - P95(|Y|) of RANSAC floor inliers
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
        
    Returns:
        VolumetricResult with bulk and discrete volumes
    """
    result = VolumetricResult(frame_id=frame_id)
    
    # Step A: Build height field from point cloud (MASK-FIRST when available)
    if rectified_cloud is not None and len(rectified_cloud) > 0:
        cells, bulk_raw = _build_height_field(
            rectified_cloud, 
            scale_factor,
            bulk_mask=bulk_mask_np,
            ground_mask=ground_mask_np,  # Lane D (kept for compatibility)
            image_width=image_width,
            image_height=image_height,
            pixel_indices=pixel_indices,
            floor_flatness_p95=floor_flatness_p95  # From geometry RANSAC
        )
        result.grid_cells = cells
        result.bulk_raw_cy = bulk_raw
        result.height_field_valid = True
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
