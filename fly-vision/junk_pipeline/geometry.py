"""
Stage 3: Depth & Geometry (The Physics Engine)
Goal: Create a stable 3D terrain relative to the floor using Depth Pro.
"""

import io
import tempfile
import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import numpy as np

from .perception import SceneType


# Depth cleaning thresholds
DEPTH_NEAR_CLIP = 0.1  # Minimum valid depth (meters)
DEPTH_FAR_CLIP = 10.0  # Maximum valid depth (meters)
SPIKE_FILTER_KERNEL = 3  # Median filter kernel for spike removal

# Depth Pro scale correction
# With proper intrinsics from Depth Pro npz, no scaling is needed.
# DEPTH_HEIGHT_SCALE should be 1.0 for metric-correct output.
# (Previously 5.5 was compensating for broken f_px estimation)
DEPTH_HEIGHT_SCALE = 1.0

# RANSAC ground plane parameters
RANSAC_ITERATIONS = 100
RANSAC_THRESHOLD = 0.05  # 5cm inlier threshold
RANSAC_BOTTOM_FRACTION = 0.20  # Use bottom 20% of pixels for indoor

# Gravity snap threshold
GRAVITY_SNAP_THRESHOLD = 0.10  # 10cm float tolerance


@dataclass
class PointCloud:
    """3D point cloud with per-point attributes."""
    points: np.ndarray  # Nx3 array of (X, Y, Z) in meters
    pixel_indices: Optional[np.ndarray] = None  # Nx2 array of (row, col) for each point
    colors: Optional[np.ndarray] = None  # Nx3 RGB
    mask_labels: Optional[np.ndarray] = None  # N-length label array
    confidence: Optional[np.ndarray] = None  # N-length confidence


@dataclass
class GroundPlane:
    """Fitted ground plane parameters."""
    normal: np.ndarray  # 3D normal vector (should be ~[0, -1, 0] for Y-up)
    distance: float  # Distance from origin
    inlier_count: int
    inlier_ratio: float
    is_valid: bool = True


@dataclass
class GeometryResult:
    """Result of Stage 3 depth & geometry processing."""
    frame_id: str
    depth_map: Optional[np.ndarray] = None  # HxW depth in meters
    depth_confidence_score: float = 0.0
    point_cloud: Optional[PointCloud] = None
    ground_plane: Optional[GroundPlane] = None
    rectified_cloud: Optional[PointCloud] = None  # After floor alignment
    floor_quality: str = "unknown"  # "good", "noisy", "failed"
    floor_flatness_p95: float = 0.20  # P95(|Y|) from rectified floor candidates (meters)
    intrinsics: Optional[dict] = None  # Camera intrinsics from Depth Pro


def _run_depth_pro(data_uri: str) -> tuple[Optional[np.ndarray], Optional[dict]]:
    """
    Run Depth Pro model to get metric depth.
    Returns (depth_map, intrinsics) or (None, None) on failure.
    
    Intrinsics returned as dict: {fx, fy, cx, cy, depth_width, depth_height}
    """
    import replicate
    import requests
    
    try:
        output = replicate.run(
            "chenxwh/ml-depth-pro:a6645b33f4e36eda0d8d52ab3da6ef37b82d198e2b70c72e680cc75f0baf1623",
            input={"image_path": data_uri}
        )
        
        # Output should contain depth map URL and intrinsics
        depth_url = None
        intrinsics = {}
        
        # Depth Pro returns: {'color_map': FileOutput, 'npz': FileOutput}
        if isinstance(output, dict):
            # Try to get the npz file (contains depth data)
            npz_output = output.get("npz") or output.get("depth") or output.get("depth_map")
            
            if npz_output:
                # FileOutput object has .url property or can be converted to string
                if hasattr(npz_output, 'url'):
                    depth_url = npz_output.url
                elif hasattr(npz_output, 'read'):
                    depth_url = None
                else:
                    depth_url = str(npz_output)
                    
        elif isinstance(output, str):
            depth_url = output
        elif hasattr(output, 'url'):
            depth_url = output.url
            
        if not depth_url:
            print("[Depth Pro] No depth URL in output")
            return None, None
            
        # Download the depth map (usually .npz format)
        response = requests.get(depth_url, timeout=30)
        response.raise_for_status()
        
        depth_map = None
        
        # Parse .npz format and extract both depth AND intrinsics
        if depth_url.endswith(".npz") or b"PK" in response.content[:4]:
            with io.BytesIO(response.content) as f:
                data = np.load(f, allow_pickle=True)
                npz_keys = list(data.keys())
                print(f"[Depth Pro] NPZ keys: {npz_keys}")
                
                # Extract depth map
                for key in ['depth', 'metric_depth', 'prediction', 'arr_0']:
                    if key in data:
                        depth_map = data[key]
                        print(f"[Depth Pro] Depth from key '{key}': shape={depth_map.shape}")
                        break
                else:
                    depth_map = data[npz_keys[0]]
                    print(f"[Depth Pro] Depth from fallback key '{npz_keys[0]}': shape={depth_map.shape}")
                
                # Extract intrinsics from npz (Fix 2)
                # Common patterns: 'intrinsics', 'K', 'camera_intrinsics', 'focallength'
                intrinsics_found = False
                
                # Check for 4-vector [fx, fy, cx, cy]
                for key in ['intrinsics', 'camera_intrinsics', 'cam_intrinsics']:
                    if key in data:
                        intr_data = data[key]
                        if hasattr(intr_data, 'item'):
                            intr_data = intr_data.item()  # Unwrap scalar arrays
                        if isinstance(intr_data, (list, np.ndarray)) and len(intr_data) >= 4:
                            intrinsics = {
                                'fx': float(intr_data[0]),
                                'fy': float(intr_data[1]),
                                'cx': float(intr_data[2]),
                                'cy': float(intr_data[3])
                            }
                            intrinsics_found = True
                            print(f"[Depth Pro] Intrinsics from '{key}': fx={intrinsics['fx']:.1f}, fy={intrinsics['fy']:.1f}")
                            break
                        elif isinstance(intr_data, dict):
                            intrinsics = intr_data
                            intrinsics_found = True
                            print(f"[Depth Pro] Intrinsics dict from '{key}': {list(intr_data.keys())}")
                            break
                
                # Check for 3x3 K matrix
                if not intrinsics_found:
                    for key in ['K', 'camera_matrix', 'intrinsic_matrix']:
                        if key in data:
                            K = data[key]
                            if K.shape == (3, 3):
                                intrinsics = {
                                    'fx': float(K[0, 0]),
                                    'fy': float(K[1, 1]),
                                    'cx': float(K[0, 2]),
                                    'cy': float(K[1, 2])
                                }
                                intrinsics_found = True
                                print(f"[Depth Pro] Intrinsics from K matrix: fx={intrinsics['fx']:.1f}, fy={intrinsics['fy']:.1f}")
                                break
                
                # Check for focal length scalar
                if not intrinsics_found:
                    for key in ['focallength', 'focal_length', 'focal_length_px', 'f']:
                        if key in data:
                            f = float(data[key])
                            intrinsics = {'fx': f, 'fy': f, 'cx': None, 'cy': None}
                            intrinsics_found = True
                            print(f"[Depth Pro] Focal length from '{key}': f={f:.1f}")
                            break
                
                if not intrinsics_found:
                    print(f"[Depth Pro] WARNING: No intrinsics found in npz!")
                
                # Store depth dimensions for later scaling
                if depth_map is not None:
                    intrinsics['depth_height'] = depth_map.shape[0]
                    intrinsics['depth_width'] = depth_map.shape[1]
                    
        else:
            # Assume raw numpy or image format (no intrinsics available)
            from PIL import Image
            img = Image.open(io.BytesIO(response.content))
            depth_map = np.array(img).astype(np.float32)
            if depth_map.max() > 100:
                depth_map = depth_map / 1000.0  # Convert mm to meters
            intrinsics['depth_height'] = depth_map.shape[0]
            intrinsics['depth_width'] = depth_map.shape[1]
                
        return depth_map, intrinsics
        
    except Exception as e:
        print(f"[Depth Pro] Error: {e}")
        import traceback
        traceback.print_exc()
        return None, None


def _clean_depth_map(depth: np.ndarray) -> tuple[np.ndarray, float]:
    """
    Clean depth map: clip extremes, remove spikes.
    Returns (cleaned_depth, confidence_score).
    """
    from scipy.ndimage import median_filter
    
    cleaned = depth.copy()
    
    # Clip extreme values
    cleaned = np.clip(cleaned, DEPTH_NEAR_CLIP, DEPTH_FAR_CLIP)
    
    # Remove isolated spikes with median filter
    cleaned = median_filter(cleaned, size=SPIKE_FILTER_KERNEL)
    
    # Calculate confidence score based on depth variance
    # Low variance = featureless (bad), High variance within reason = good
    valid_mask = (depth > DEPTH_NEAR_CLIP) & (depth < DEPTH_FAR_CLIP)
    if valid_mask.sum() > 0:
        variance = np.var(depth[valid_mask])
        # Normalize variance to 0-1 score
        confidence = min(1.0, variance / 2.0)  # 2.0m² variance = max confidence
    else:
        confidence = 0.0
        
    return cleaned, confidence


def _back_project(
    depth: np.ndarray, 
    fx: float,
    fy: Optional[float] = None,
    cx: Optional[float] = None,
    cy: Optional[float] = None
) -> tuple[np.ndarray, np.ndarray]:
    """
    Back-project depth map to 3D point cloud in Y_UP world coordinates.
    
    Args:
        depth: HxW depth map in meters
        fx: Focal length X in pixels
        fy: Focal length Y in pixels (defaults to fx if not provided)
        cx, cy: Principal point (defaults to image center)
        
    Returns:
        Tuple of:
        - Nx3 array of (X, Y, Z) points in Y_UP world coords
        - Nx2 array of (row, col) pixel indices for each point
    """
    H, W = depth.shape
    
    # Default fy to fx if not provided
    if fy is None:
        fy = fx
    if cx is None:
        cx = W / 2.0
    if cy is None:
        cy = H / 2.0
    
    # Create pixel coordinate grids
    u, v = np.meshgrid(np.arange(W), np.arange(H))
    
    # Back-project to 3D (camera coordinates: Y_down)
    # Fix 4: Use separate fx and fy for proper intrinsics
    Z = depth
    X = (u - cx) * Z / fx
    Y_cam = (v - cy) * Z / fy
    
    # Convert to Y_UP world coordinates
    # In camera coords: v increases downward, so Y_cam is positive downward
    # In world coords: Y should be positive upward
    Y = -Y_cam  # Flip Y so positive = up
    
    # Stack and reshape to Nx3
    points = np.stack([X, Y, Z], axis=-1)
    points = points.reshape(-1, 3)
    
    # Create pixel index array (row, col) for each point
    rows = v.flatten()
    cols = u.flatten()
    pixel_indices = np.stack([rows, cols], axis=-1)  # Nx2
    
    # Filter out invalid points
    valid = (depth.flatten() > DEPTH_NEAR_CLIP) & (depth.flatten() < DEPTH_FAR_CLIP)
    points = points[valid]
    pixel_indices = pixel_indices[valid]  # Keep parallel indices
    
    return points, pixel_indices


def _build_floor_candidates(
    depth: np.ndarray,
    fx: float,
    fy: float,
    cx: float,
    cy: float,
    bulk_mask: Optional[np.ndarray] = None,
    floor_mask: Optional[np.ndarray] = None
) -> tuple[np.ndarray, np.ndarray, int]:
    """
    Build floor candidates from depth map with robust filtering.
    
    Filters:
    - Bottom 40% of image (or floor_mask if available)
    - Valid depth
    - Smoothness (percentile-based gradient threshold)
    - Depth band (p20-p80 range)
    - Low curvature (Laplacian)
    - Conditional bulk mask exclusion with erosion
    """
    from scipy.ndimage import laplace, binary_erosion
    
    H, W = depth.shape
    
    # === Filter 1: Spatial region (bottom band OR floor_mask) ===
    bottom_start_row = int(H * 0.60)
    bottom_mask = np.zeros((H, W), dtype=bool)
    bottom_mask[bottom_start_row:, :] = True
    
    # If SegFormer floor_mask available, intersect with bottom band
    if floor_mask is not None and floor_mask.shape == (H, W):
        floor_area_pct = np.mean(floor_mask) * 100
        if 2.0 < floor_area_pct < 80.0:  # Sane range
            # Use intersection: must be in bottom band AND floor_mask
            bottom_mask = bottom_mask & floor_mask
            print(f"[FloorCandidates] Using SegFormer floor_mask ({floor_area_pct:.1f}%) ∩ bottom band")
    
    # === Filter 2: Valid depth ===
    valid_depth = (depth > DEPTH_NEAR_CLIP) & (depth < DEPTH_FAR_CLIP) & np.isfinite(depth)
    
    # === Fix 1: Scale-aware smoothness (percentile-based threshold) ===
    gy = np.zeros_like(depth)
    gx = np.zeros_like(depth)
    gy[:-1, :] = depth[1:, :] - depth[:-1, :]
    gx[:, :-1] = depth[:, 1:] - depth[:, :-1]
    grad_magnitude = np.sqrt(gx**2 + gy**2)
    
    # Get gradient stats in valid bottom band
    valid_bottom = bottom_mask & valid_depth
    if np.sum(valid_bottom) > 0:
        grad_in_band = grad_magnitude[valid_bottom]
        grad_min = np.min(grad_in_band)
        grad_median = np.median(grad_in_band)
        grad_p95 = np.percentile(grad_in_band, 95)
        grad_max = np.max(grad_in_band)
        
        # Use p95 as threshold (reject only extreme 5% discontinuities)
        # Ensure minimum threshold to avoid filtering everything
        grad_thresh = max(grad_p95, 0.005)
        print(f"[FloorCandidates] grad: min={grad_min:.4f}, med={grad_median:.4f}, "
              f"p95={grad_p95:.4f}, max={grad_max:.4f} → thresh={grad_thresh:.4f}")
    else:
        grad_thresh = 0.05
        print(f"[FloorCandidates] No valid bottom band, using default grad_thresh={grad_thresh}")
    
    smooth_mask = grad_magnitude < grad_thresh
    
    # === Fix 2: Depth band filter (keep p20-p80 range) ===
    if np.sum(valid_bottom) > 0:
        depth_in_band = depth[valid_bottom]
        d_lo = np.percentile(depth_in_band, 20)
        d_hi = np.percentile(depth_in_band, 80)
        depth_band_mask = (depth >= d_lo) & (depth <= d_hi)
        print(f"[FloorCandidates] depth band: p20={d_lo:.2f}m, p80={d_hi:.2f}m")
    else:
        depth_band_mask = np.ones((H, W), dtype=bool)
    
    # === Fix 3: Low curvature filter (Laplacian) ===
    # Floor has low curvature, curved objects have high curvature
    lap = laplace(depth)
    lap_abs = np.abs(lap)
    
    if np.sum(valid_bottom) > 0:
        lap_in_band = lap_abs[valid_bottom]
        # Use p70 to keep lower 70% curvature (ensure non-zero)
        lap_thresh = max(np.percentile(lap_in_band, 70), 0.001)
        print(f"[FloorCandidates] curvature (Laplacian p70): {lap_thresh:.6f}")
    else:
        lap_thresh = 0.1
    
    low_curvature_mask = lap_abs < lap_thresh
    
    # === Fix 4: Conditional bulk mask with erosion ===
    if bulk_mask is not None:
        bulk_area_pct = np.mean(bulk_mask) * 100
        
        if bulk_area_pct >= 85:
            # Flooded - ignore completely
            not_bulk = np.ones((H, W), dtype=bool)
            print(f"[FloorCandidates] Ignoring flooded bulk_mask ({bulk_area_pct:.1f}% >= 85%)")
        elif bulk_area_pct >= 5 and bulk_area_pct < 70:
            # Reliable range - use with soft exclusion
            not_bulk = ~bulk_mask
            print(f"[FloorCandidates] Using bulk_mask exclusion ({bulk_area_pct:.1f}%)")
        elif bulk_area_pct > 0:
            # High coverage (70-85%) - erode mask to protect floor edges
            eroded = binary_erosion(bulk_mask, iterations=15)
            not_bulk = ~eroded
            print(f"[FloorCandidates] Eroded bulk_mask ({bulk_area_pct:.1f}%→{np.mean(eroded)*100:.1f}%)")
        else:
            not_bulk = np.ones((H, W), dtype=bool)
    else:
        not_bulk = np.ones((H, W), dtype=bool)
    
    # === Combine all filters ===
    candidate_mask = (bottom_mask & valid_depth & smooth_mask & 
                      depth_band_mask & low_curvature_mask & not_bulk)
    candidate_count = np.sum(candidate_mask)
    
    # Log filter chain
    n_valid_bottom = np.sum(bottom_mask & valid_depth)
    n_smooth = np.sum(bottom_mask & valid_depth & smooth_mask)
    n_depth_band = np.sum(bottom_mask & valid_depth & smooth_mask & depth_band_mask)
    n_low_curv = np.sum(bottom_mask & valid_depth & smooth_mask & depth_band_mask & low_curvature_mask)
    
    print(f"[FloorCandidates] Filter chain: valid_bottom={n_valid_bottom} → "
          f"smooth={n_smooth} → depth_band={n_depth_band} → low_curv={n_low_curv} → final={candidate_count}")
    
    # Quick reject if too few
    if candidate_count < 5_000:
        print(f"[FloorCandidates] WARNING: Only {candidate_count} candidates (< 5k)")
    
    # Backproject to 3D
    v, u = np.where(candidate_mask)
    if len(v) == 0:
        return np.zeros((0, 3)), candidate_mask, 0
        
    Z = depth[v, u]
    X = (u - cx) * Z / fx
    Y_cam = (v - cy) * Z / fy
    Y = -Y_cam  # Y_UP convention
    
    candidate_points = np.stack([X, Y, Z], axis=-1)
    
    return candidate_points, candidate_mask, candidate_count



def _fit_ground_plane_ransac(
    candidates: np.ndarray,
    scene_type: SceneType,
    seed: int = 42
) -> GroundPlane:
    """
    Option A Step 2: Fit ground plane to floor candidates with constrained RANSAC.
    
    Features:
    - 800 RANSAC iterations
    - 20° normal constraint
    - Spread requirement: extent_x > 1.0m AND extent_z > 1.0m
    - Scene-aware distance threshold: 0.02m indoor, 0.03m outdoor
    """
    import math
    
    if len(candidates) < 100:
        print(f"[RANSAC] FAILED: Only {len(candidates)} candidates (< 100 required)")
        return GroundPlane(
            normal=np.array([0, 1, 0]),
            distance=0,
            inlier_count=0,
            inlier_ratio=0,
            is_valid=False
        )
    
    # Scene-aware distance threshold
    if scene_type == SceneType.INDOOR_FLAT:
        dist_threshold = 0.02  # 2cm for indoor
    else:
        dist_threshold = 0.03  # 3cm for outdoor
    
    # RANSAC parameters
    n_iterations = 800
    rng = np.random.default_rng(seed)
    
    best_plane = None
    best_inliers = 0
    best_inlier_mask = None
    best_quality_score = 0
    
    for _ in range(n_iterations):
        if len(candidates) < 3:
            break
        idx = rng.choice(len(candidates), 3, replace=False)
        p1, p2, p3 = candidates[idx]
        
        # Compute plane normal
        v1 = p2 - p1
        v2 = p3 - p1
        normal = np.cross(v1, v2)
        norm = np.linalg.norm(normal)
        if norm < 1e-6:
            continue
        normal = normal / norm
        
        # 20° normal constraint
        vertical_dot = abs(normal[1])
        if vertical_dot < 0.94:  # cos(20°)
            continue
        
        # Compute inliers
        d = -np.dot(normal, p1)
        distances = np.abs(np.dot(candidates, normal) + d)
        inlier_mask = distances < dist_threshold
        inlier_count = np.sum(inlier_mask)
        inlier_ratio = inlier_count / len(candidates)
        
        # Quality score
        quality_score = inlier_count * inlier_ratio * vertical_dot
        
        if quality_score > best_quality_score:
            best_quality_score = quality_score
            best_inliers = inlier_count
            best_inlier_mask = inlier_mask
            best_plane = (normal, d)
    
    if best_plane is None:
        print("[RANSAC] FAILED: No valid plane found within 20° of vertical")
        return GroundPlane(
            normal=np.array([0, 1, 0]),
            distance=0,
            inlier_count=0,
            inlier_ratio=0,
            is_valid=False
        )
    
    normal, d = best_plane
    # Ensure normal points UP
    if normal[1] < 0:
        normal = -normal
        d = -d
    
    inlier_ratio = best_inliers / len(candidates)
    inlier_points = candidates[best_inlier_mask]
    
    # === SPREAD REQUIREMENT ===
    # Check that floor spans a reasonable area (not just a small patch)
    # Note: Z extent is naturally small because floor candidates are at similar depths
    # Use X extent + minimum inlier count as proxy for floor coverage
    x_coords = inlier_points[:, 0]
    extent_x = np.max(x_coords) - np.min(x_coords)
    
    # Floor must span at least 0.3m in X (lower due to correct focal length)
    # and have at least 5k inliers (HuggingFace intrinsics concentrate points)
    spread_pass = extent_x > 0.3 and best_inliers > 5_000
    
    # Validity check - good inlier ratio + spread
    is_valid = inlier_ratio > 0.10 and best_inliers > 5_000 and spread_pass
    
    angle_to_up = math.degrees(math.acos(min(1.0, abs(normal[1]))))
    print(f"[RANSAC] candidates={len(candidates)}, inliers={best_inliers}, "
          f"ratio={inlier_ratio:.3f}, angle={angle_to_up:.1f}°, "
          f"extent_x={extent_x:.2f}m, spread_pass={spread_pass}, valid={is_valid}")
    
    return GroundPlane(
        normal=normal,
        distance=d,
        inlier_count=best_inliers,
        inlier_ratio=inlier_ratio,
        is_valid=is_valid
    )


def _rectify_point_cloud(
    points: np.ndarray,
    ground_plane: GroundPlane
) -> np.ndarray:
    """
    Rotate point cloud so ground plane is Y=0.
    Apply gravity snap if cloud floats above floor.
    """
    if not ground_plane.is_valid:
        return points
        
    # Compute rotation to align ground normal with +Y axis (Y_UP convention)
    target = np.array([0, 1, 0])  # Floor normal should point UP
    current = ground_plane.normal
    
    # Rotation axis (cross product)
    axis = np.cross(current, target)
    axis_norm = np.linalg.norm(axis)
    
    if axis_norm < 1e-6:
        # Already aligned
        rotation = np.eye(3)
    else:
        axis = axis / axis_norm
        # Rotation angle
        angle = np.arccos(np.clip(np.dot(current, target), -1, 1))
        
        # Rodrigues' rotation formula
        K = np.array([
            [0, -axis[2], axis[1]],
            [axis[2], 0, -axis[0]],
            [-axis[1], axis[0], 0]
        ])
        rotation = np.eye(3) + np.sin(angle) * K + (1 - np.cos(angle)) * (K @ K)
    
    # Apply rotation
    rectified = (rotation @ points.T).T
    
    # Apply height scale correction to Y only (Depth Pro underestimates heights)
    rectified[:, 1] *= DEPTH_HEIGHT_SCALE
    
    # NOW zero the floor (AFTER scaling)
    # Find floor level using bottom 20% of Y values
    y_vals = rectified[:, 1]
    sorted_y = np.sort(y_vals)
    bottom_20_pct = sorted_y[:int(len(sorted_y) * 0.20)]
    if len(bottom_20_pct) > 10:
        floor_level = np.median(bottom_20_pct)
    else:
        floor_level = np.min(y_vals)
    
    # Shift so floor is at Y=0
    rectified[:, 1] -= floor_level
    
    return rectified


def run_geometry(
    frame_id: str,
    working_pil: "Image.Image",
    scene_type: SceneType,
    bulk_mask: Optional[np.ndarray] = None,
    floor_mask: Optional[np.ndarray] = None
) -> GeometryResult:
    """
    Stage 3 Entry Point: Generate 3D terrain from depth.
    
    Args:
        frame_id: Unique frame identifier
        working_pil: PIL Image at working resolution (same size as masks)
        scene_type: From Stage 2 Lane C
        bulk_mask: From Stage 2 Lane B (optional)
        floor_mask: From Stage 2 Lane D SegFormer (optional)
        
    Returns:
        GeometryResult with depth map, point cloud, and ground plane
    """
    from PIL import Image
    from .depth_pro import DepthProRunner
    
    result = GeometryResult(frame_id=frame_id)
    
    # === Run Depth Pro (HuggingFace) ===
    try:
        runner = DepthProRunner.get_instance()
        depth_output = runner.infer(working_pil)
        
        depth_map = depth_output["depth_m"]
        intrinsics = depth_output["intrinsics"]
        fov = depth_output.get("field_of_view")
        
    except Exception as e:
        print(f"[Geometry] Depth Pro failed: {e}")
        import traceback
        traceback.print_exc()
        result.floor_quality = "failed"
        return result
    
    result.depth_map = depth_map
    result.intrinsics = intrinsics
    
    # Clean depth map
    cleaned_depth, confidence = _clean_depth_map(depth_map)
    result.depth_confidence_score = confidence
    
    # Extract intrinsics from Depth Pro (now always available!)
    depth_h, depth_w = cleaned_depth.shape
    fx = intrinsics["fx"]
    fy = intrinsics["fy"]
    cx = intrinsics["cx"]
    cy = intrinsics["cy"]
    
    # === Sanity Check: Resolution agreement ===
    image_w, image_h = working_pil.size
    if (depth_h, depth_w) != (image_h, image_w):
        print(f"[Geometry] WARNING: Resolution mismatch! depth={depth_w}×{depth_h}, image={image_w}×{image_h}")
    
    # === Sanity Check: Intrinsics plausibility ===
    # For W=1024, typical fx is 700-1100px
    fx_min = 0.4 * depth_w
    fx_max = 1.5 * depth_w
    if fx < fx_min or fx > fx_max:
        print(f"[Geometry] WARNING: fx={fx:.1f} outside expected range [{fx_min:.0f}, {fx_max:.0f}]")
    else:
        print(f"[Geometry] Intrinsics: fx={fx:.1f}, fy={fy:.1f}, cx={cx:.1f}, cy={cy:.1f}")
    
    # === OPTION A: Build floor candidates from depth (using floor_mask if available) ===
    floor_candidates, floor_candidate_mask, candidate_count = _build_floor_candidates(
        cleaned_depth, fx, fy, cx, cy, bulk_mask=bulk_mask, floor_mask=floor_mask
    )
    
    if candidate_count < 5000:
        print(f"[Geometry] Floor detection SKIPPED: only {candidate_count} candidates")
        result.floor_quality = "failed"
        # Still create point cloud for discrete items
        points, pixel_indices = _back_project(cleaned_depth, fx, fy, cx, cy)
        result.point_cloud = PointCloud(points=points, pixel_indices=pixel_indices)
        result.rectified_cloud = result.point_cloud
        return result
    
    # Back-project full depth for point cloud
    points, pixel_indices = _back_project(cleaned_depth, fx, fy, cx, cy)
    result.point_cloud = PointCloud(points=points, pixel_indices=pixel_indices)
    
    # Fit ground plane to floor candidates (not all points)
    seed = int(hashlib.md5(frame_id.encode()).hexdigest()[:8], 16) % (2**31)
    ground_plane = _fit_ground_plane_ransac(floor_candidates, scene_type, seed=seed)
    result.ground_plane = ground_plane
    
    # Rectify full point cloud (not just candidates)
    if ground_plane.is_valid:
        rectified_points = _rectify_point_cloud(points, ground_plane)
        result.rectified_cloud = PointCloud(points=rectified_points, pixel_indices=pixel_indices)
        
        # === STEP 3: Floor Flatness Verification ===
        # Compute P95(|Y|) from rectified floor candidates (not all points)
        # This measures actual floor flatness, not whole-scene metrics
        rectified_floor = _rectify_point_cloud(floor_candidates, ground_plane)
        y_floor = rectified_floor[:, 1]
        p95_y_floor = np.percentile(np.abs(y_floor), 95)
        median_y_floor = np.median(np.abs(y_floor))
        
        # Store floor flatness metric for volumetrics to use
        result.floor_flatness_p95 = p95_y_floor
        
        # === DIAGNOSTIC: Stage 3 Invariants for Height Compression Debug ===
        # 1. Depth sanity (before rectification)
        depth_valid = cleaned_depth[cleaned_depth > 0]
        depth_p50 = np.percentile(depth_valid, 50) if len(depth_valid) > 0 else 0
        depth_p95 = np.percentile(depth_valid, 95) if len(depth_valid) > 0 else 0
        print(f"[GEOM_DEBUG] Depth sanity: depth_p50={depth_p50:.2f}m, depth_p95={depth_p95:.2f}m")
        
        # 2. Rectified Y sanity (after rotation + floor snap)
        # Floor points (from floor_candidates)
        print(f"[GEOM_DEBUG] Y_floor_p95={p95_y_floor:.3f}m (should be ~0.02-0.08m)")
        
        # Junk points (from bulk_mask if available) - using correct pixel_indices mapping
        rectified_pts = result.rectified_cloud.points
        pix_indices = result.rectified_cloud.pixel_indices
        if bulk_mask is not None and pix_indices is not None:
            mask_h, mask_w = bulk_mask.shape
            junk_heights = []
            for idx in range(len(rectified_pts)):
                # Use pixel_indices for correct point-to-pixel mapping
                row, col = pix_indices[idx]
                mask_row = int(row * mask_h / depth_h)
                mask_col = int(col * mask_w / depth_w)
                mask_row = max(0, min(mask_row, mask_h - 1))
                mask_col = max(0, min(mask_col, mask_w - 1))
                if bulk_mask[mask_row, mask_col]:
                    junk_heights.append(rectified_pts[idx, 1])
            
            if junk_heights:
                junk_heights = np.array(junk_heights)
                Y_junk_p50 = np.percentile(junk_heights, 50)
                Y_junk_p95 = np.percentile(junk_heights, 95)
                Y_junk_max = np.max(junk_heights)
                print(f"[GEOM_DEBUG] Y_junk_p50={Y_junk_p50:.3f}m, Y_junk_p95={Y_junk_p95:.3f}m, Y_junk_max={Y_junk_max:.3f}m")
                print(f"[GEOM_DEBUG] (n_junk_points={len(junk_heights)})")
        # === END DIAGNOSTIC ===
        
        print(f"[Floor Flatness] P95(|Y|)={p95_y_floor:.3f}m, median(|Y|)={median_y_floor:.3f}m, ratio={ground_plane.inlier_ratio:.3f}")
        
        # Classify based on flatness (inlier_ratio already checked in RANSAC)
        # Thresholds per Option A: good (≤0.08m), noisy (0.08-0.20m), failed (>0.20m)
        if p95_y_floor <= 0.08 and ground_plane.inlier_ratio >= 0.05:
            result.floor_quality = "good"
        elif p95_y_floor <= 0.20 and ground_plane.inlier_ratio >= 0.05:
            result.floor_quality = "noisy"
        else:
            result.floor_quality = "failed"
            if p95_y_floor > 0.20:
                print(f"  ⚠️ Floor FAILED: P95(|Y|)={p95_y_floor:.3f}m > 0.20m")
            if ground_plane.inlier_ratio < 0.05:
                print(f"  ⚠️ Floor FAILED: inlier_ratio={ground_plane.inlier_ratio:.3f} < 0.05")
    else:
        result.rectified_cloud = result.point_cloud
        result.floor_quality = "failed"
        
    return result
