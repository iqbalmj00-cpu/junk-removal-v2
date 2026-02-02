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

# v8.3 Feature flags
FLOOR_GEOM_GATING = True   # Phase 1: geometry-consistency gating
FLOOR_MULTI_PLANE = True   # Phase 3: multi-plane RANSAC

# v8.4 Feature flags
FLOOR_LOCAL_CONF = True    # Pile-adjacent support region for local floor confidence


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
class PointPixelMap:
    """
    v7.2: Safe pixel↔point mapping with explicit invariant.
    
    Invariant: pixel_to_point[r, c] = i ↔ pixel_indices[i] = (r, c)
    """
    points: np.ndarray          # Nx3 (X, Y, Z) in meters
    pixel_indices: np.ndarray   # Nx2 (row, col) for each point
    pixel_to_point: np.ndarray  # HxW → point index or -1
    
    @staticmethod
    def build(points: np.ndarray, pixel_indices: np.ndarray, H: int, W: int) -> "PointPixelMap":
        """Build mapping from points and their pixel indices."""
        pixel_to_point = np.full((H, W), -1, dtype=np.int32)
        for i, (r, c) in enumerate(pixel_indices):
            if 0 <= r < H and 0 <= c < W:
                pixel_to_point[int(r), int(c)] = i
        return PointPixelMap(points, pixel_indices, pixel_to_point)


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
    intrinsics_source: str = "unknown"  # v6.7.2: "calibration_bundle" or "depthpro"
    # Floor candidate fallback tracking (v6.8.0)
    floor_candidate_fallback_level: int = 0  # 0=A_hard, 1=B_eroded, 2=C_bottom_band, 3=D_skip
    floor_candidate_fallback_mode: str = "A_hard"  # Human-readable mode name
    floor_candidate_count: int = 0  # Number of candidates found
    # v7.2: Eligibility flags for fusion
    eligible_for_footprint: bool = True
    eligible_for_height: bool = True
    fusion_weight_cap: float = 1.0
    is_multi_surface: bool = False
    floor_quality_score: float = 0.7  # Continuous 0.3-1.0
    point_pixel_map: Optional["PointPixelMap"] = None
    # v8.3: Floor detection improvements
    floor_conf: float = 0.7  # Continuous 0-1 floor confidence (global)
    is_multi_surface_hint: bool = False  # From VLM triage
    num_planes_detected: int = 1  # How many planes RANSAC found
    # v8.4: Pile-adjacent local floor confidence
    floor_conf_local: float = 0.7  # Local confidence from support ROI
    sr_inlier_ratio: float = 0.0  # Inlier ratio within support ROI
    sr_yfl95: float = 0.20  # Yfl95 within support ROI
    support_roi_valid: bool = False  # Was support ROI computed successfully?
    # v8.5: Support plane selection
    support_plane_selected: bool = False  # Was a support plane successfully selected?
    support_plane_source: str = ""  # "global_0", "global_1", "local", or ""


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


def compute_geom_floor_like(depth: np.ndarray, bottom_fraction: float = 0.40) -> np.ndarray:
    """
    v8.3 Phase 1: Compute mask of pixels that are geometrically floor-like.
    
    Uses gradient + curvature, not semantic labels.
    Floor-like = low gradient (q65) + low curvature (q70) in bottom band.
    
    Args:
        depth: HxW depth map in meters
        bottom_fraction: Fraction of image height to consider as bottom band
    
    Returns:
        HxW boolean mask of floor-like pixels
    """
    from scipy.ndimage import laplace
    
    H, W = depth.shape
    
    # Gradient magnitude
    gy = np.zeros_like(depth)
    gx = np.zeros_like(depth)
    gy[:-1, :] = depth[1:, :] - depth[:-1, :]
    gx[:, :-1] = depth[:, 1:] - depth[:, :-1]
    grad = np.sqrt(gx**2 + gy**2)
    
    # Curvature (Laplacian)
    curv = np.abs(laplace(depth))
    
    # Bottom band
    bottom_start = int(H * (1 - bottom_fraction))
    bottom_band = np.zeros((H, W), dtype=bool)
    bottom_band[bottom_start:, :] = True
    
    # Valid depth
    valid = bottom_band & (depth > DEPTH_NEAR_CLIP) & (depth < DEPTH_FAR_CLIP)
    if valid.sum() < 1000:
        return bottom_band  # Fallback to raw bottom band
    
    # Compute thresholds from bottom band valid pixels
    grad_thresh = np.percentile(grad[valid], 65)
    curv_thresh = np.percentile(curv[valid], 70)
    
    # Floor-like = low gradient + low curvature
    geom_floor_like = (grad < grad_thresh) & (curv < curv_thresh)
    
    print(f"[GeomFloorLike] grad_thresh={grad_thresh:.4f}, curv_thresh={curv_thresh:.4f}, "
          f"floor_like_pct={100*geom_floor_like.sum()/(H*W):.1f}%")
    
    return geom_floor_like


def _compute_support_roi(
    bulk_mask: np.ndarray,
    depth: np.ndarray,
    bottom_band_mask: np.ndarray,
    geom_floor_like: Optional[np.ndarray] = None,
    dilation_radius: int = 30
) -> tuple[np.ndarray, np.ndarray, bool]:
    """
    v8.4: Compute pile-adjacent support region with LOCAL candidates.
    
    Key insight: Global floor candidates use strict thresholds that may not
    overlap with the near-pile region. We compute relaxed local candidates
    specifically in the near-pile zone.
    
    Returns:
        (support_roi, local_cand_mask, is_valid)
        - support_roi: HxW boolean mask (same as local_cand_mask when valid)
        - local_cand_mask: HxW boolean of relaxed-threshold candidates in near-pile
        - is_valid: False means fallback to global bottom band needed
    """
    import cv2
    from scipy.ndimage import laplace
    
    H, W = bulk_mask.shape
    MIN_SUPPORT_ROI_PX = 2000
    MIN_BULK_AREA_PCT = 1.0
    
    valid_depth = (depth > DEPTH_NEAR_CLIP) & (depth < DEPTH_FAR_CLIP)
    
    # Check bulk mask validity
    bulk_area_pct = 100.0 * bulk_mask.sum() / (H * W)
    if bulk_area_pct < MIN_BULK_AREA_PCT:
        print(f"[SupportROI] FALLBACK: bulk_area={bulk_area_pct:.1f}% < {MIN_BULK_AREA_PCT}%")
        fallback = bottom_band_mask & valid_depth
        return fallback, fallback, False
    
    # Dilate bulk mask using cv2 (ellipse kernel)
    kernel_size = 2 * dilation_radius + 1
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
    bulk_uint8 = bulk_mask.astype(np.uint8) * 255
    dilated = cv2.dilate(bulk_uint8, kernel) > 0
    
    # Near-pile region = dilated ∩ bottom_band - bulk ∩ valid_depth
    near_pile = dilated & bottom_band_mask & ~bulk_mask & valid_depth
    near_pile_px = near_pile.sum()
    
    print(f"[SupportROI] near_pile_px={near_pile_px}")
    
    if near_pile_px < 500:
        print(f"[SupportROI] FALLBACK: near_pile too small ({near_pile_px} < 500)")
        fallback = bottom_band_mask & valid_depth
        return fallback, fallback, False
    
    # === Compute LOCAL thresholds from near-pile (RELAXED) ===
    # Gradient
    gy = np.zeros_like(depth)
    gx = np.zeros_like(depth)
    gy[:-1, :] = depth[1:, :] - depth[:-1, :]
    gx[:, :-1] = depth[:, 1:] - depth[:, :-1]
    grad = np.sqrt(gx**2 + gy**2)
    
    # Curvature
    curv = np.abs(laplace(depth))
    
    # Get stats from near-pile pixels
    grad_near = grad[near_pile]
    curv_near = curv[near_pile]
    depth_near = depth[near_pile]
    
    # Relaxed thresholds: p98 grad, p90 curv, [p15, p85] depth
    grad_thresh = np.percentile(grad_near, 98)
    curv_thresh = np.percentile(curv_near, 90)
    depth_lo = np.percentile(depth_near, 15)
    depth_hi = np.percentile(depth_near, 85)
    
    print(f"[SupportROI] LOCAL thresholds: grad<{grad_thresh:.4f} (p98), "
          f"curv<{curv_thresh:.6f} (p90), depth=[{depth_lo:.2f}m, {depth_hi:.2f}m]")
    
    # Local candidates = near_pile with relaxed filters
    local_cand = (
        near_pile &
        (grad < grad_thresh) &
        (curv < curv_thresh) &
        (depth >= depth_lo) &
        (depth <= depth_hi)
    )
    
    local_cand_px = local_cand.sum()
    print(f"[SupportROI] local_cand_px={local_cand_px}")
    
    if local_cand_px < MIN_SUPPORT_ROI_PX:
        print(f"[SupportROI] FALLBACK: local_cand={local_cand_px} < {MIN_SUPPORT_ROI_PX}")
        fallback = bottom_band_mask & valid_depth
        return fallback, fallback, False
    
    sr_pct = 100.0 * local_cand_px / (H * W)
    print(f"[SupportROI] SUCCESS: bulk={bulk_area_pct:.1f}%, "
          f"support_roi={sr_pct:.1f}% ({local_cand_px} px)")
    
    return local_cand, local_cand, True


# =============================================================================
# v8.5: SUPPORT PLANE ARCHITECTURE
# =============================================================================

def _fit_local_support_plane(
    local_cand_mask: np.ndarray,
    depth: np.ndarray,
    fx: float, fy: float, cx: float, cy: float,
    scene_type: SceneType,
    seed: int = 42
) -> Optional[GroundPlane]:
    """
    v8.5: Fit a single plane to near-pile local candidates.
    
    Uses ROI-RELATIVE validity gates, not global spread requirements.
    A support plane is valid if it explains the ROI adequately,
    even if the ROI is small.
    """
    v, u = np.where(local_cand_mask)
    
    if len(v) < 500:  # Lowered from 1000 for small ROIs
        print(f"[LocalPlane] SKIP: only {len(v)} candidates < 500")
        return None
    
    # Backproject to 3D
    z = depth[v, u]
    valid = (z > DEPTH_NEAR_CLIP) & (z < DEPTH_FAR_CLIP)
    v, u, z = v[valid], u[valid], z[valid]
    
    if len(z) < 500:
        print(f"[LocalPlane] SKIP: only {len(z)} valid depth < 500")
        return None
    
    x = (u - cx) * z / fx
    y = (v - cy) * z / fy
    local_pts = np.stack([x, y, z], axis=1)
    
    # --- LOCAL RANSAC (ROI-relative) ---
    rng = np.random.default_rng(seed)
    n_candidates = len(local_pts)
    
    # Adaptive iterations for smaller point set
    n_iterations = min(200, max(50, n_candidates // 20))
    dist_threshold = 0.05 if scene_type == SceneType.INDOOR_FLAT else 0.06
    
    best_plane = None
    best_inliers = 0
    best_inlier_mask = None
    best_quality_score = 0
    
    for _ in range(n_iterations):
        # Sample 3 random points
        idx = rng.choice(n_candidates, size=3, replace=False)
        p1, p2, p3 = local_pts[idx]
        
        # Compute plane normal
        v1 = p2 - p1
        v2 = p3 - p1
        normal = np.cross(v1, v2)
        norm = np.linalg.norm(normal)
        if norm < 1e-10:
            continue
        normal = normal / norm
        
        # Check vertical alignment (within 25° of vertical for support planes)
        vertical_dot = abs(normal[1])
        if vertical_dot < 0.90:  # ~25° tolerance
            continue
        
        # Compute inliers
        d = -np.dot(normal, p1)
        distances = np.abs(np.dot(local_pts, normal) + d)
        inlier_mask = distances < dist_threshold
        inlier_count = np.sum(inlier_mask)
        inlier_ratio = inlier_count / n_candidates
        
        # Quality score: prioritize inlier count × ratio × verticality
        quality_score = inlier_count * inlier_ratio * vertical_dot
        
        if quality_score > best_quality_score:
            best_quality_score = quality_score
            best_inliers = inlier_count
            best_inlier_mask = inlier_mask
            best_plane = (normal, d)
    
    if best_plane is None:
        print(f"[LocalPlane] SKIP: no valid plane within 25° of vertical")
        return None
    
    normal, d = best_plane
    inlier_ratio = best_inliers / n_candidates
    inlier_points = local_pts[best_inlier_mask]
    
    # --- ROI-RELATIVE VALIDITY ---
    # Instead of absolute extent threshold, use ratio of ROI coverage
    x_coords = inlier_points[:, 0]
    extent_x = np.max(x_coords) - np.min(x_coords)
    
    # ROI bounding box (in 3D X dimension)
    roi_extent_x = np.max(local_pts[:, 0]) - np.min(local_pts[:, 0])
    
    # Support plane is valid if:
    # 1. Inlier ratio >= 0.25 (at least 25% of ROI candidates are inliers)
    # 2. At least 300 inliers (absolute minimum)
    # 3. Extent covers at least 50% of ROI extent OR at least 0.15m (whichever is smaller)
    min_extent_threshold = min(0.5 * roi_extent_x, 0.15)
    
    ratio_pass = inlier_ratio >= 0.25
    count_pass = best_inliers >= 300
    extent_pass = extent_x >= min_extent_threshold
    
    is_valid = ratio_pass and count_pass and extent_pass
    
    # Compute angle from vertical for logging
    vertical = np.array([0, -1, 0])
    angle = np.degrees(np.arccos(np.clip(np.abs(np.dot(normal, vertical)), -1, 1)))
    
    print(f"[LocalPlane] candidates={n_candidates}, inliers={best_inliers}, "
          f"ratio={inlier_ratio:.3f}, angle={angle:.1f}°, "
          f"extent={extent_x:.2f}m (roi={roi_extent_x:.2f}m), valid={is_valid}")
    
    if not is_valid:
        print(f"[LocalPlane] SKIP: ratio_pass={ratio_pass}, count_pass={count_pass}, extent_pass={extent_pass}")
        return None
    
    return GroundPlane(
        normal=normal,
        distance=d,
        inlier_count=best_inliers,
        inlier_ratio=inlier_ratio,
        is_valid=True
    )


def _check_plane_under_pile(
    plane: GroundPlane,
    bulk_mask: np.ndarray,
    depth: np.ndarray,
    fx: float, fy: float, cx: float, cy: float,
    required_fraction: float = 0.70
) -> tuple[bool, float]:
    """
    v8.5: Verify that most pile points lie ABOVE the plane.
    
    Prevents selecting curb faces, fence planes, or pile-side planes.
    
    Returns:
        (passes_gate, fraction_above)
    """
    H, W = bulk_mask.shape
    pile_v, pile_u = np.where(bulk_mask)
    
    if len(pile_v) < 100:
        return True, 1.0  # Can't check, pass by default
    
    # Focus on bottom portion of pile (more likely to be near floor)
    v_thresh = np.percentile(pile_v, 70)  # bottom 30% of pile in image
    bottom_mask = pile_v >= v_thresh
    pile_v_sample = pile_v[bottom_mask]
    pile_u_sample = pile_u[bottom_mask]
    
    if len(pile_v_sample) < 50:
        return True, 1.0
    
    # Subsample for speed
    if len(pile_v_sample) > 1000:
        np.random.seed(42)
        idx = np.random.choice(len(pile_v_sample), 1000, replace=False)
        pile_v_sample = pile_v_sample[idx]
        pile_u_sample = pile_u_sample[idx]
    
    # Backproject to 3D
    z = depth[pile_v_sample, pile_u_sample]
    valid = (z > 0.1) & (z < 10.0)
    
    if valid.sum() < 50:
        return True, 1.0
    
    pile_v_sample = pile_v_sample[valid]
    pile_u_sample = pile_u_sample[valid]
    z = z[valid]
    
    x = (pile_u_sample - cx) * z / fx
    y = (pile_v_sample - cy) * z / fy
    pile_pts = np.stack([x, y, z], axis=1)
    
    # Ensure normal points "up" (negative Y in image coords = up in world)
    normal = plane.normal.copy()
    distance = plane.distance  # Track distance for potential flip
    if normal[1] > 0:  # Normal pointing down, flip it
        normal = -normal
        distance = -distance  # MUST flip distance too for consistent plane equation
    
    # Signed distance: positive = above plane
    signed_dist = np.dot(pile_pts, normal) + distance
    above_plane = signed_dist > 0.02  # 2cm margin
    
    fraction_above = np.mean(above_plane)
    passes = fraction_above >= required_fraction
    
    return passes, fraction_above


def _compute_adaptive_tau(
    support_eval_pts: np.ndarray,
    base_tau: float = 0.05
) -> float:
    """
    v8.5: Compute noise-aware inlier threshold.
    
    Outdoor grass/lawn can have 0.1-0.3m depth noise.
    Scale tau based on median depth.
    """
    if len(support_eval_pts) == 0:
        return base_tau
    
    # Median depth in support region
    median_depth = np.median(support_eval_pts[:, 2])
    
    # Depth-proportional scaling: further = more noise
    # At 2m: tau = base_tau
    # At 4m: tau = base_tau * 1.5
    depth_scale = 1.0 + 0.25 * (median_depth - 2.0)
    depth_scale = np.clip(depth_scale, 0.8, 2.0)
    
    tau = base_tau * depth_scale
    
    # Clamp to reasonable range
    tau = np.clip(tau, 0.03, 0.12)
    
    return tau


def _select_support_plane(
    candidate_planes: list,  # List of (source: str, plane: GroundPlane)
    support_eval_pts: np.ndarray,  # Nx3 backprojected points
    bulk_mask: np.ndarray,
    depth: np.ndarray,
    fx: float, fy: float, cx: float, cy: float
) -> tuple[Optional[GroundPlane], dict]:
    """
    v8.5: Select support plane using rank-based tier selection.
    
    1. Hard gates: coverage, normal angle, residual p95, under-pile check
    2. Rank by sr_inlier_ratio
    3. Tie-break on sr_residual_p95
    
    Returns:
        (support_plane, metrics_dict) or (None, {'reason': ...})
    """
    if len(support_eval_pts) < 500:
        print(f"[SupportPlane] SKIP: only {len(support_eval_pts)} eval points")
        return None, {'reason': 'insufficient_eval_points'}
    
    # Compute adaptive threshold
    tau = _compute_adaptive_tau(support_eval_pts)
    print(f"[SupportPlane] tau={tau:.3f}m (depth_median={np.median(support_eval_pts[:, 2]):.2f}m)")
    
    eligible = []
    
    for source, plane in candidate_planes:
        if plane is None:
            continue
        
        # Enforce normal orientation (pointing "up" = negative Y)
        normal = plane.normal.copy()
        distance = plane.distance
        if normal[1] > 0:
            normal = -normal
            distance = -distance
        
        # Compute residuals on support_eval points
        residuals = np.abs(np.dot(support_eval_pts, normal) + distance)
        
        sr_inliers = int(np.sum(residuals < tau))
        sr_inlier_ratio = sr_inliers / len(support_eval_pts)
        sr_residual_p95 = float(np.percentile(residuals, 95))
        
        # Normal angle from vertical (Y-axis)
        vertical = np.array([0, -1, 0])
        normal_angle = float(np.degrees(np.arccos(np.clip(np.abs(np.dot(normal, vertical)), -1, 1))))
        
        # === HARD GATES ===
        # Gate 1: Minimum coverage
        if sr_inliers < 500:
            print(f"[SupportPlane] {source}: FAIL(coverage={sr_inliers}<500)")
            continue
        
        # Gate 2: Normal angle [0°, 45°]
        if normal_angle > 45:
            print(f"[SupportPlane] {source}: FAIL(angle={normal_angle:.1f}>45)")
            continue
        
        # Gate 3: Residual p95 < 2.5*tau
        max_p95 = 2.5 * tau
        if sr_residual_p95 > max_p95:
            print(f"[SupportPlane] {source}: FAIL(p95={sr_residual_p95:.3f}>{max_p95:.3f})")
            continue
        
        # Gate 4: Plane is under the pile
        under_pile_pass, fraction_above = _check_plane_under_pile(
            plane, bulk_mask, depth, fx, fy, cx, cy
        )
        if not under_pile_pass:
            print(f"[SupportPlane] {source}: FAIL(under_pile={fraction_above:.2f}<0.70)")
            continue
        
        print(f"[SupportPlane] {source}: PASS(sr={sr_inlier_ratio:.3f}, p95={sr_residual_p95:.3f}m, "
              f"angle={normal_angle:.1f}°, under={fraction_above:.2f})")
        
        eligible.append({
            'source': source,
            'plane': plane,
            'sr_inlier_ratio': sr_inlier_ratio,
            'sr_residual_p95': sr_residual_p95,
            'sr_inliers': sr_inliers,
            'normal_angle': normal_angle,
            'fraction_above': fraction_above
        })
    
    if not eligible:
        print(f"[SupportPlane] No eligible planes")
        return None, {'reason': 'no_eligible_planes'}
    
    # === TIER-BASED SELECTION ===
    # Tier 1: Maximize sr_inlier_ratio
    eligible.sort(key=lambda x: -x['sr_inlier_ratio'])
    
    # Tier 2: Tie-break on lower sr_residual_p95 (within 5% of best ratio)
    best_ratio = eligible[0]['sr_inlier_ratio']
    top_tier = [e for e in eligible if e['sr_inlier_ratio'] >= best_ratio * 0.95]
    top_tier.sort(key=lambda x: x['sr_residual_p95'])
    
    winner = top_tier[0]
    
    print(f"[SupportPlane] SELECTED: {winner['source']} "
          f"(sr={winner['sr_inlier_ratio']:.3f}, p95={winner['sr_residual_p95']:.3f}m)")
    
    return winner['plane'], {
        'source': winner['source'],
        'sr_inlier_ratio': winner['sr_inlier_ratio'],
        'sr_residual_p95': winner['sr_residual_p95'],
        'sr_inliers': winner['sr_inliers'],
        'normal_angle': winner['normal_angle'],
        'tau': tau
    }



def _build_floor_candidates(
    depth: np.ndarray,
    fx: float,
    fy: float,
    cx: float,
    cy: float,
    bulk_mask: Optional[np.ndarray] = None,
    floor_mask: Optional[np.ndarray] = None,
    multi_surface_hint: bool = False,  # v8.3: From VLM triage
    **kwargs
) -> tuple[np.ndarray, np.ndarray, int]:
    """
    Build floor candidates from depth map with robust filtering.
    
    Filters:
    - Bottom 40% of image (or floor_mask if available)
    - Valid depth
    - Smoothness (percentile-based gradient threshold)
    - Depth band (p20-p80 range, or p30-p70 if multi_surface_hint)
    - Low curvature (Laplacian)
    - Conditional bulk mask exclusion with erosion
    
    v8.3: When multi_surface_hint=True, ignore semantic floor_mask and use
    geometry-only filtering (grad q65 + curv q70).
    """
    from scipy.ndimage import laplace, binary_erosion
    
    H, W = depth.shape
    
    # === Filter 1: Spatial region (bottom band OR floor_mask) ===
    bottom_start_row = int(H * 0.60)
    bottom_mask = np.zeros((H, W), dtype=bool)
    bottom_mask[bottom_start_row:, :] = True
    
    # v8.3: When multi_surface_hint=True, skip semantic floor_mask (it's contaminated)
    if multi_surface_hint:
        print(f"[FloorCandidates] multi_surface_hint=True: ignoring semantic floor_mask, using geometry-only")
    elif floor_mask is not None and floor_mask.shape == (H, W):
        floor_area_pct = np.mean(floor_mask) * 100
        if 2.0 < floor_area_pct < 80.0:  # Sane range
            # v8.3 Phase 1: When FLOOR_GEOM_GATING enabled, refine semantic mask with geometry
            if FLOOR_GEOM_GATING:
                geom_floor_like = compute_geom_floor_like(depth)
                refined_floor_mask = floor_mask & geom_floor_like
                refined_pct = np.mean(refined_floor_mask) * 100
                print(f"[FloorCandidates] GEOM_GATING: semantic={floor_area_pct:.1f}% → refined={refined_pct:.1f}%")
                bottom_mask = bottom_mask & refined_floor_mask
            else:
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
    
    # === Fix 2: Depth band filter ===
    # v8.3: Use tighter p30-p70 when multi_surface_hint (more contamination expected)
    if np.sum(valid_bottom) > 0:
        depth_in_band = depth[valid_bottom]
        if multi_surface_hint:
            d_lo = np.percentile(depth_in_band, 30)
            d_hi = np.percentile(depth_in_band, 70)
            print(f"[FloorCandidates] depth band (multi_surface): p30={d_lo:.2f}m, p70={d_hi:.2f}m")
        else:
            d_lo = np.percentile(depth_in_band, 20)
            d_hi = np.percentile(depth_in_band, 80)
            print(f"[FloorCandidates] depth band: p20={d_lo:.2f}m, p80={d_hi:.2f}m")
        depth_band_mask = (depth >= d_lo) & (depth <= d_hi)
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
    
    # === Fix 4: Conditional bulk mask with fallback modes ===
    # bulk_exclusion_mode controls how aggressively we exclude bulk mask:
    #   'hard': Full exclusion (original behavior)
    #   'eroded': Apply erosion based on bulk coverage
    #   'bottom_band_only': Only exclude bulk in bottom band
    #   'skip': No bulk exclusion (last resort fallback)
    bulk_exclusion_mode = kwargs.get('bulk_exclusion_mode', 'hard')
    
    if bulk_mask is not None and bulk_exclusion_mode != 'skip':
        bulk_area_pct = np.mean(bulk_mask) * 100
        
        if bulk_area_pct >= 85:
            # Flooded - ignore completely
            not_bulk = np.ones((H, W), dtype=bool)
            print(f"[FloorCandidates] Ignoring flooded bulk_mask ({bulk_area_pct:.1f}% >= 85%)")
        elif bulk_exclusion_mode == 'eroded':
            # Erosion in pixels based on bulk coverage
            # v6.8.0 Fix D: Increased erosion for high bulk frames
            if bulk_area_pct < 35:
                erode_px = 3
            elif bulk_area_pct < 60:
                erode_px = 7
            elif bulk_area_pct < 65:
                erode_px = 12
            else:
                erode_px = 18  # Was 12px, increased for better floor recovery
            eroded = binary_erosion(bulk_mask, iterations=erode_px)
            not_bulk = ~eroded
            print(f"[FloorCandidates] Eroded bulk_mask ({bulk_area_pct:.1f}%→{np.mean(eroded)*100:.1f}%, {erode_px}px)")
        elif bulk_exclusion_mode == 'bottom_band_only':
            # Only exclude bulk where it intersects bottom band
            bulk_in_bottom = bulk_mask & bottom_mask
            not_bulk = ~bulk_in_bottom
            excluded_pct = np.mean(bulk_in_bottom) * 100
            print(f"[FloorCandidates] Bottom-band-only exclusion ({excluded_pct:.1f}% excluded)")
        elif bulk_area_pct >= 5 and bulk_area_pct < 70:
            # Hard exclusion (original behavior)
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
        if bulk_exclusion_mode == 'skip':
            print(f"[FloorCandidates] FALLBACK: Skipping bulk exclusion")
    
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


def _fit_multi_plane_ransac(
    candidates: np.ndarray,
    scene_type: SceneType,
    floor_candidate_mask: np.ndarray,
    depth: np.ndarray,
    seed: int = 42,
    max_planes: int = 2,
    support_roi: Optional[np.ndarray] = None,  # v8.4: Pile-adjacent support region (HxW)
    candidate_pixel_coords: Optional[tuple] = None  # v8.4 Fix: (v, u) arrays for index alignment
) -> tuple[GroundPlane, int, dict]:
    """
    v8.3/8.4 Phase 3: Sequential RANSAC to detect multiple floor planes.
    
    v8.4: Uses support_roi (pile-adjacent region) for scoring instead of bottom band.
    v8.4 Fix: candidate_pixel_coords ensures proper index-space alignment.
    
    Score components:
    - sr_inliers: inliers inside support ROI (v8.4) or bottom band (v8.3 fallback)
    - sr_inlier_ratio: fit quality within support region
    - residual_p95: penalty for high residuals
    
    Returns:
        (best_plane, num_planes_detected, local_metrics_dict)
    """
    import math
    
    if len(candidates) < 1000:
        print(f"[MultiPlane] SKIP: Only {len(candidates)} candidates (< 1000 required)")
        # Fallback to single-plane
        plane = _fit_ground_plane_ransac(candidates, scene_type, seed)
        return plane, 1, {'sr_inlier_ratio': 0.0, 'sr_yfl95': 0.20, 'sr_valid': False}
    
    planes = []
    remaining_mask = np.ones(len(candidates), dtype=bool)
    
    for i in range(max_planes):
        remaining_candidates = candidates[remaining_mask]
        if len(remaining_candidates) < 500:
            print(f"[MultiPlane] Iteration {i}: stopping, only {len(remaining_candidates)} candidates remain")
            break
        
        # Fit single plane to remaining candidates
        plane = _fit_ground_plane_ransac(remaining_candidates, scene_type, seed + i)
        if not plane.is_valid or plane.inlier_ratio < 0.15:
            print(f"[MultiPlane] Iteration {i}: plane invalid or low inlier ratio, stopping")
            break
        
        # Find which candidates are inliers for this plane
        distances = np.abs(np.dot(remaining_candidates, plane.normal) + plane.distance)
        inlier_mask_local = distances < 0.05  # 5cm threshold
        
        # Map back to original indices
        remaining_indices = np.where(remaining_mask)[0]
        plane.inlier_indices = remaining_indices[inlier_mask_local]
        
        planes.append(plane)
        print(f"[MultiPlane] Plane {i}: inliers={plane.inlier_count}, ratio={plane.inlier_ratio:.3f}")
        
        # Remove inliers for next iteration
        remaining_mask[plane.inlier_indices] = False
    
    if not planes:
        # Fallback to single-plane
        plane = _fit_ground_plane_ransac(candidates, scene_type, seed)
        return plane, 1, {'sr_inlier_ratio': 0.0, 'sr_yfl95': 0.20, 'sr_valid': False}
    
    # === v8.4 SCORED PLANE SELECTION ===
    # Use support_roi if available (pile-adjacent), otherwise bottom band (fallback)
    H, W = floor_candidate_mask.shape
    
    use_support_roi = support_roi is not None and support_roi.sum() >= 2000 and candidate_pixel_coords is not None
    
    if use_support_roi:
        # v8.4 Fix: Compute support_roi in CANDIDATE space using pixel coords
        cand_v, cand_u = candidate_pixel_coords  # (v, u) arrays length N_candidates
        
        # support_roi_cand[i] = True if candidate i is in support ROI
        support_roi_cand = support_roi[cand_v, cand_u]  # boolean length N_candidates
        sr_total_valid = support_roi_cand.sum()  # count in candidate space
        
        # Debug: also log image-space count for comparison
        sr_img_count = support_roi.sum()
        print(f"[MultiPlane] v8.4: support_roi_img={sr_img_count}px, support_roi_cand={sr_total_valid}px")
        
        if sr_total_valid < 500:
            # Fallback if too few candidates overlap with support ROI
            print(f"[MultiPlane] v8.4 FALLBACK: support_roi_cand={sr_total_valid} < 500, using bottom_band")
            use_support_roi = False
    
    if not use_support_roi:
        # v8.3 fallback: bottom band in candidate space
        if candidate_pixel_coords is not None:
            cand_v, cand_u = candidate_pixel_coords
            bottom_start = int(H * 0.60)
            # support_roi_cand[i] = True if candidate i is in bottom band
            support_roi_cand = cand_v >= bottom_start
            sr_total_valid = support_roi_cand.sum()
        else:
            # Ultimate fallback: all candidates are scoring region
            support_roi_cand = np.ones(len(candidates), dtype=bool)
            sr_total_valid = len(candidates)
        print(f"[MultiPlane] v8.3 fallback: bottom_band, sr_total_valid={sr_total_valid}")
    
    # Hard gate thresholds
    MIN_INLIER_RATIO = 0.55
    MAX_RESIDUAL_P95 = 0.12  # meters
    
    best_plane = None
    best_score = -np.inf
    eligible_planes = []
    best_local_metrics = {'sr_inlier_ratio': 0.0, 'sr_yfl95': 0.20, 'sr_valid': use_support_roi}
    
    for plane in planes:
        # Compute metrics using scoring region (support ROI or bottom band) IN CANDIDATE SPACE
        sr_inliers = 0
        if hasattr(plane, 'inlier_indices') and len(plane.inlier_indices) > 0:
            # v8.4 Fix: Index support_roi_cand with plane inlier indices
            sr_inliers = np.sum(support_roi_cand[plane.inlier_indices])
        
        # v8.4: Compute sr_inlier_ratio (fit quality within scoring region)
        sr_inlier_ratio = sr_inliers / sr_total_valid if sr_total_valid > 0 else 0.0
        
        inlier_pts = candidates[plane.inlier_indices] if hasattr(plane, 'inlier_indices') else candidates[:100]
        residuals = np.abs(np.dot(inlier_pts, plane.normal) + plane.distance)
        residual_p95 = np.percentile(residuals, 95) if len(residuals) else 1.0
        
        # v8.4: Compute local Yfl95 from residuals within scoring region
        sr_mask = support_roi_cand[plane.inlier_indices] if hasattr(plane, 'inlier_indices') else np.zeros(len(residuals), dtype=bool)
        sr_residuals = residuals[sr_mask] if sr_mask.any() else residuals
        sr_residual_p95 = np.percentile(sr_residuals, 95) if len(sr_residuals) else 1.0
        
        # === HARD GATES ===
        # v8.4: Use sr_inlier_ratio for gate check when support ROI is active
        gate_pass = True
        gate_reasons = []
        
        effective_ratio = sr_inlier_ratio if use_support_roi and sr_inlier_ratio > 0 else plane.inlier_ratio
        if effective_ratio < MIN_INLIER_RATIO:
            gate_pass = False
            gate_reasons.append(f"ratio={effective_ratio:.2f}<{MIN_INLIER_RATIO}")
        
        if sr_residual_p95 > MAX_RESIDUAL_P95:
            gate_pass = False
            gate_reasons.append(f"res_p95={sr_residual_p95:.3f}>{MAX_RESIDUAL_P95}")
        
        # === v8.4 TIER 1 NONLINEAR FIT-STRENGTH SCORING ===
        # (sr^0.85) × (ratio^2.0) × exp(-res/0.05)
        sr = float(sr_inliers)
        r = sr_inlier_ratio if use_support_roi else plane.inlier_ratio
        rp = sr_residual_p95
        
        res_penalty = np.exp(-rp / 0.05)  # exp decay for residuals
        score = (sr ** 0.85) * (r ** 2.0) * res_penalty
        
        print(f"[MultiPlane] Plane: sr={sr_inliers}, sr_ratio={r:.3f}, res_p95={rp:.4f}, "
              f"res_pen={res_penalty:.3f}, gate={'PASS' if gate_pass else 'FAIL(' + ','.join(gate_reasons) + ')'}, "
              f"score={score:.1f}")
        
        # Store metrics for dominance check
        plane_metrics = {
            'plane': plane,
            'sr_inliers': sr_inliers,
            'sr_inlier_ratio': sr_inlier_ratio,
            'sr_residual_p95': sr_residual_p95,
            'ratio': r,
            'residual_p95': rp,
            'score': score,
            'gate_pass': gate_pass
        }
        
        if gate_pass:
            eligible_planes.append(plane_metrics)
            if score > best_score:
                best_score = score
                best_plane = plane
                best_local_metrics = {
                    'sr_inlier_ratio': sr_inlier_ratio,
                    'sr_yfl95': sr_residual_p95,
                    'sr_valid': use_support_roi
                }
    
    # === v8.4 HIGH-RATIO DOMINANCE RULE ===
    # If any plane has ratio >= 0.83 and has >= 20% of best's sr_inliers, prefer it
    if len(eligible_planes) > 1 and best_plane is not None:
        best_ratio_pm = max(eligible_planes, key=lambda pm: pm['ratio'])
        best_score_pm = max(eligible_planes, key=lambda pm: pm['score'])
        
        if best_ratio_pm['ratio'] >= 0.83:
            # Check it has meaningful support (>= 20% of best score plane's sr_inliers)
            if best_ratio_pm['sr_inliers'] >= 0.20 * best_score_pm['sr_inliers']:
                if best_ratio_pm['plane'] != best_plane:
                    print(f"[MultiPlane] DOMINANCE: ratio={best_ratio_pm['ratio']:.3f}>=0.83 "
                          f"with sr={best_ratio_pm['sr_inliers']} (>= 20% of {best_score_pm['sr_inliers']}) → override")
                    best_plane = best_ratio_pm['plane']
                    best_local_metrics = {
                        'sr_inlier_ratio': best_ratio_pm['sr_inlier_ratio'],
                        'sr_yfl95': best_ratio_pm['sr_residual_p95'],
                        'sr_valid': use_support_roi
                    }
    
    # === TIER 2: Fit-first fallback when no planes pass gates ===
    if best_plane is None:
        print(f"[MultiPlane] WARNING: No planes passed hard gates, using fit-first fallback")
        
        MIN_SR_INLIERS = 1000  # Sanity check: don't pick a plane with tiny support
        best_bad_score = -np.inf
        
        for plane in planes:
            # Recompute metrics for fallback scoring
            sr_inliers = 0
            if hasattr(plane, 'inlier_indices') and len(plane.inlier_indices) > 0:
                # v8.4 Fix: Use support_roi_cand
                sr_inliers = np.sum(support_roi_cand[plane.inlier_indices])
            
            # Skip planes with too few sr_inliers
            if sr_inliers < MIN_SR_INLIERS:
                print(f"[MultiPlane] Tier2 SKIP: sr_inliers={sr_inliers} < {MIN_SR_INLIERS}")
                continue
            
            inlier_pts = candidates[plane.inlier_indices] if hasattr(plane, 'inlier_indices') else candidates[:100]
            residuals = np.abs(np.dot(inlier_pts, plane.normal) + plane.distance)
            residual_p95 = np.percentile(residuals, 95) if len(residuals) else 1.0
            
            # Fit-first scoring: fit quality dominates
            score_bad = (
                3.0 * plane.inlier_ratio
                - 2.5 * min(residual_p95 / 0.20, 1.0)
                - 1.5 * min(residual_p95 * 2.0 / 0.25, 1.0)  # yfl95 proxy
            )
            
            print(f"[MultiPlane] Tier2: ratio={plane.inlier_ratio:.3f}, res_p95={residual_p95:.4f}, "
                  f"sr={sr_inliers}, score_bad={score_bad:.3f}")
            
            if score_bad > best_bad_score:
                best_bad_score = score_bad
                best_plane = plane
                best_local_metrics = {
                    'sr_inlier_ratio': sr_inliers / sr_total_valid if sr_total_valid > 0 else 0.0,
                    'sr_yfl95': residual_p95,
                    'sr_valid': use_support_roi
                }
        
        # Ultimate fallback: just pick highest inlier_ratio
        if best_plane is None:
            print(f"[MultiPlane] WARNING: Tier2 also failed, using highest inlier_ratio")
            best_plane = max(planes, key=lambda p: p.inlier_ratio)
    
    return best_plane, len(planes), best_local_metrics


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


# =============================================================================
# v7.2: FUSION ELIGIBILITY HELPERS
# =============================================================================

def _compute_floor_quality_score(
    floor_quality: str,
    ground_plane: Optional[GroundPlane],
    floor_flatness_p95: float,
    fallback_level: int
) -> float:
    """
    v7.2: Compute continuous floor quality score for confidence model.
    
    Range: 0.3 (failed) to 1.0 (excellent)
    
    Factors:
    - Base from floor_quality label
    - Inlier ratio (geometry confidence)
    - Flatness P95 (how uniform the floor is)
    - Fallback level (how many candidate searches were needed)
    """
    base = {"good": 1.0, "noisy": 0.7, "failed": 0.4}.get(floor_quality, 0.5)
    
    inlier_factor = 1.0
    if ground_plane and ground_plane.inlier_ratio > 0:
        inlier_factor = min(1.0, ground_plane.inlier_ratio / 0.8)
    
    flatness_factor = max(0.5, 1.0 - floor_flatness_p95 / 0.20)
    fallback_penalty = {0: 1.0, 1: 0.9, 2: 0.7, 3: 0.4}.get(fallback_level, 0.5)
    
    return max(0.3, min(1.0, base * inlier_factor * flatness_factor * fallback_penalty))


def _detect_multi_surface(labels_found: list[str]) -> tuple[bool, list[str]]:
    """
    v7.2: Detect if floor spans multiple surface types.
    
    Multi-surface floors (e.g., grass + concrete) are unreliable for
    footprint/height donation because RANSAC fits a single plane.
    
    Returns:
        (is_multi_surface, list of detected surface types)
    """
    surface_types = {"road", "floor", "grass", "gravel", "dirt", "sidewalk", "pavement"}
    detected = [label for label in labels_found if label.lower() in surface_types]
    
    # More than one surface type = multi-surface
    unique_surfaces = list(set(detected))
    return len(unique_surfaces) >= 2, unique_surfaces


def run_geometry(
    frame_id: str,
    working_pil: "Image.Image",
    scene_type: SceneType,
    bulk_mask: Optional[np.ndarray] = None,
    floor_mask: Optional[np.ndarray] = None,
    calibration_bundle: Optional["CalibrationBundle"] = None,  # v6.7.2: Single source of truth
    floor_labels: Optional[list[str]] = None,  # v7.2: For multi-surface detection
    multi_surface_hint: bool = False  # v8.3: From VLM triage
) -> GeometryResult:
    """
    Stage 3 Entry Point: Generate 3D terrain from depth.
    
    Args:
        frame_id: Unique frame identifier
        working_pil: PIL Image at working resolution (same size as masks)
        scene_type: From Stage 2 Lane C
        bulk_mask: From Stage 2 Lane B (optional)
        floor_mask: From Stage 2 Lane D SegFormer (optional)
        calibration_bundle: v6.7.2 - If HIGH confidence, use as authoritative intrinsics
        
    Returns:
        GeometryResult with depth map, point cloud, and ground plane
    """
    from PIL import Image
    from .depth_pro import DepthProRunner
    
    result = GeometryResult(frame_id=frame_id)
    result.is_multi_surface_hint = multi_surface_hint  # v8.3
    if multi_surface_hint:
        print(f"[Geometry] multi_surface_hint=True from VLM triage")
    
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
    
    # Extract intrinsics - SINGLE SOURCE OF TRUTH
    depth_h, depth_w = cleaned_depth.shape
    image_w, image_h = working_pil.size
    
    # v6.7.2: CalibrationBundle is authoritative when HIGH confidence
    intrinsics_source = "depthpro"
    if calibration_bundle and calibration_bundle.calib_confidence == "HIGH" and calibration_bundle.fx > 0:
        fx = calibration_bundle.fx
        fy = calibration_bundle.fy
        cx = calibration_bundle.cx
        cy = calibration_bundle.cy
        intrinsics_source = "calibration_bundle"
        print(f"[Geometry] Using CalibrationBundle intrinsics (HIGH confidence): fx={fx:.1f}, fy={fy:.1f}")
    else:
        # Fallback to DepthPro's estimated intrinsics
        fx = intrinsics["fx"]
        fy = intrinsics["fy"]
        cx = intrinsics["cx"]
        cy = intrinsics["cy"]
        bundle_reason = "no bundle" if not calibration_bundle else f"confidence={calibration_bundle.calib_confidence}"
        print(f"[Geometry] Using DepthPro intrinsics ({bundle_reason}): fx={fx:.1f}, fy={fy:.1f}")
    
    # === Sanity Check: Resolution agreement ===
    if (depth_h, depth_w) != (image_h, image_w):
        print(f"[Geometry] WARNING: Resolution mismatch! depth={depth_w}×{depth_h}, image={image_w}×{image_h}")
    
    # === Sanity Check: Intrinsics plausibility ===
    fx_min = 0.4 * depth_w
    fx_max = 1.5 * depth_w
    if fx < fx_min or fx > fx_max:
        print(f"[Geometry] WARNING: fx={fx:.1f} outside expected range [{fx_min:.0f}, {fx_max:.0f}]")
    
    result.intrinsics_source = intrinsics_source  # Track for debugging
    
    # === OPTION A: Build floor candidates from depth (using floor_mask if available) ===
    # Fallback ladder: try progressively less aggressive bulk exclusion if starved
    FALLBACK_MODES = [
        ('A_hard', 'hard'),           # Pass A: original full exclusion
        ('B_eroded', 'eroded'),       # Pass B: eroded based on coverage
        ('C_bottom_band', 'bottom_band_only'),  # Pass C: only exclude in bottom band
        ('D_skip', 'skip'),           # Pass D: last resort, no exclusion
    ]
    
    floor_candidates = None
    floor_candidate_mask = None
    candidate_count = 0
    fallback_level = 0
    fallback_mode_used = 'A_hard'
    
    for level, (mode_name, bulk_mode) in enumerate(FALLBACK_MODES):
        floor_candidates, floor_candidate_mask, candidate_count = _build_floor_candidates(
            cleaned_depth, fx, fy, cx, cy, bulk_mask=bulk_mask, floor_mask=floor_mask,
            bulk_exclusion_mode=bulk_mode, multi_surface_hint=multi_surface_hint
        )
        
        if candidate_count >= 5000:
            # Sufficient candidates - use this result
            if level > 0:
                print(f"[FloorCandidates] FALLBACK SUCCESS: {mode_name} recovered {candidate_count} candidates")
            fallback_level = level
            fallback_mode_used = mode_name
            break
        elif level < len(FALLBACK_MODES) - 1:
            print(f"[FloorCandidates] Pass {mode_name}: only {candidate_count} candidates, trying next fallback...")
        else:
            # Final fallback also failed
            fallback_level = level
            fallback_mode_used = mode_name
    
    # Store fallback metadata in result for MES to use
    result.floor_candidate_fallback_level = fallback_level
    result.floor_candidate_fallback_mode = fallback_mode_used
    result.floor_candidate_count = candidate_count
    
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
    
    # Fit ground plane to floor candidates
    seed = int(hashlib.md5(frame_id.encode()).hexdigest()[:8], 16) % (2**31)
    
    # v8.3: Use multi-plane RANSAC when multi_surface_hint and FLOOR_MULTI_PLANE enabled
    if FLOOR_MULTI_PLANE and multi_surface_hint and len(floor_candidates) > 10_000:
        print(f"[Geometry] Using multi-plane RANSAC (multi_surface_hint=True, candidates={len(floor_candidates)})")
        
        # v8.4 Fix: Get candidate pixel coords for proper index-space alignment
        cand_v, cand_u = np.where(floor_candidate_mask)
        candidate_pixel_coords = (cand_v, cand_u)
        
        # v8.5: Compute support ROI and local candidates
        support_roi = None
        local_cand_mask = None
        support_eval_pts = None
        
        if FLOOR_LOCAL_CONF and bulk_mask is not None:
            H, W = cleaned_depth.shape
            bottom_start = int(H * 0.60)
            bottom_band_mask = np.zeros((H, W), dtype=bool)
            bottom_band_mask[bottom_start:, :] = True
            
            # Compute geom_floor_like for filtering
            geom_floor_like = compute_geom_floor_like(cleaned_depth)
            
            # v8.4: Returns (support_roi, local_cand_mask, is_valid)
            support_roi, local_cand_mask, sr_valid = _compute_support_roi(
                bulk_mask, cleaned_depth, bottom_band_mask, geom_floor_like, dilation_radius=30
            )
            result.support_roi_valid = sr_valid
            
            # v8.5: Compute support_eval = support_roi ∩ local_cand ∩ ~bulk_dilated
            import cv2
            bulk_dilated = cv2.dilate(bulk_mask.astype(np.uint8) * 255, 
                                       cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (21, 21))) > 0
            support_eval = support_roi & local_cand_mask & ~bulk_dilated
            
            # Backproject support_eval to 3D for scoring
            eval_v, eval_u = np.where(support_eval)
            if len(eval_v) >= 500:
                eval_z = cleaned_depth[eval_v, eval_u]
                valid_z = (eval_z > DEPTH_NEAR_CLIP) & (eval_z < DEPTH_FAR_CLIP)
                eval_v, eval_u, eval_z = eval_v[valid_z], eval_u[valid_z], eval_z[valid_z]
                
                eval_x = (eval_u - cx) * eval_z / fx
                eval_y = (eval_v - cy) * eval_z / fy
                support_eval_pts = np.stack([eval_x, eval_y, eval_z], axis=1)
                print(f"[Geometry] v8.5: support_eval_pts={len(support_eval_pts)}")
        
        # Step 1: Fit global planes (existing)
        ground_plane, num_planes, _ = _fit_multi_plane_ransac(
            floor_candidates, scene_type, floor_candidate_mask, cleaned_depth, 
            seed=seed, support_roi=support_roi, candidate_pixel_coords=candidate_pixel_coords
        )
        result.num_planes_detected = num_planes
        
        # Collect global planes
        all_planes = [('global_0', ground_plane)]
        
        # v8.5: Fit local support plane
        local_plane = None
        if local_cand_mask is not None and local_cand_mask.sum() >= 2000:
            local_plane = _fit_local_support_plane(
                local_cand_mask, cleaned_depth, fx, fy, cx, cy, scene_type, seed=seed
            )
            if local_plane is not None:
                all_planes.append(('local', local_plane))
        
        # v8.5: Select best support plane
        support_plane = ground_plane  # Default fallback
        support_metrics = {'source': 'global_0', 'sr_inlier_ratio': 0.0, 'sr_residual_p95': 0.20}
        
        if support_eval_pts is not None and len(support_eval_pts) >= 500:
            selected_plane, selected_metrics = _select_support_plane(
                all_planes, support_eval_pts, bulk_mask, cleaned_depth, fx, fy, cx, cy
            )
            if selected_plane is not None:
                support_plane = selected_plane
                support_metrics = selected_metrics
        
        # v8.5: Store support plane metrics
        result.sr_inlier_ratio = support_metrics.get('sr_inlier_ratio', 0.0)
        result.sr_yfl95 = support_metrics.get('sr_residual_p95', 0.20)
        result.floor_conf_local = min(1.0, max(0.0, result.sr_inlier_ratio * 1.2))
        
        # v8.5: Track if support plane was successfully selected
        if selected_plane is not None:
            result.support_plane_selected = True
            result.support_plane_source = support_metrics.get('source', 'unknown')
        
        # Use support plane for ground plane (determines floor reference)
        ground_plane = support_plane
        
        if num_planes > 1:
            result.is_multi_surface = True
            print(f"[Geometry] Multi-surface detected: {num_planes} planes")
    else:
        ground_plane = _fit_ground_plane_ransac(floor_candidates, scene_type, seed=seed)
        result.num_planes_detected = 1
        result.floor_conf_local = result.floor_conf  # Fallback: local = global
    
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
    
    # =========================================================================
    # v7.2: ELIGIBILITY GATING FOR FUSION
    # =========================================================================
    
    # D_skip gating: frames that couldn't find floor candidates
    if result.floor_candidate_fallback_mode == "D_skip":
        result.eligible_for_footprint = False
        result.eligible_for_height = False
        result.fusion_weight_cap = 0.3
        print(f"[Geometry] D_skip fallback: frame gated as non-donor (cap=0.3)")
    
    # Multi-surface gating: mixed surfaces (grass + concrete) are unreliable
    if floor_labels:
        is_multi, surfaces = _detect_multi_surface(floor_labels)
        result.is_multi_surface = is_multi
        if is_multi:
            result.eligible_for_footprint = False
            result.eligible_for_height = False
            result.fusion_weight_cap = min(result.fusion_weight_cap, 0.4)
            print(f"[Geometry] Multi-surface detected ({surfaces}): frame gated (cap={result.fusion_weight_cap})")
    
    # Compute continuous floor quality score
    result.floor_quality_score = _compute_floor_quality_score(
        result.floor_quality,
        result.ground_plane,
        result.floor_flatness_p95,
        result.floor_candidate_fallback_level
    )
    print(f"[Geometry] floor_quality_score={result.floor_quality_score:.2f}")
    
    # Build PointPixelMap for leakage detection
    if result.rectified_cloud and result.rectified_cloud.pixel_indices is not None:
        H, W = result.depth_map.shape if result.depth_map is not None else (0, 0)
        if H > 0 and W > 0:
            result.point_pixel_map = PointPixelMap.build(
                result.rectified_cloud.points,
                result.rectified_cloud.pixel_indices,
                H, W
            )
        
    return result

