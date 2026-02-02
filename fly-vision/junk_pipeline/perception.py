"""
Stage 2: Parallel Perception (The "Tri-Lane" Vision)
Goal: Generate clean semantic layers for geometry to act upon.
"""

import hashlib
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class SceneType(Enum):
    """Scene classification for ground plane logic."""
    INDOOR_FLAT = "indoor_flat"
    OUTDOOR_DRIVEWAY = "outdoor_driveway"
    UNEVEN_GROUND = "uneven_ground"
    UNKNOWN = "unknown"


@dataclass
class InstanceMask:
    """A segmented instance with its mask data."""
    instance_id: str
    label: str
    confidence: float
    bbox: tuple[int, int, int, int]  # x1, y1, x2, y2
    mask_url: Optional[str] = None  # URL to mask image from segmenter
    mask_data: Optional[bytes] = None  # Raw mask bytes if downloaded
    area_ratio: float = 0.0  # Fraction of image area
    is_anchor: bool = False  # Tire, door, bin - used for calibration
    is_high_value: bool = False  # Sofa, fridge - discrete billing


# Lane A: High-value discrete items and calibration anchors
HIGH_VALUE_ITEMS = {
    "sofa", "couch", "refrigerator", "fridge", "washer", "dryer",
    "mattress", "bed", "dresser", "bookshelf", "desk", "table",
    "chair", "armchair", "tv", "television", "microwave", "oven",
    "dishwasher", "exercise equipment", "treadmill", "elliptical",
}

ANCHOR_ITEMS = {
    "tire": 0.60,  # ~24" diameter = 0.6m 
    "door": 2.03,  # Standard door height = 2.03m (80")
    "bin": 0.90,   # Standard trash bin = 0.90m
    "trash can": 0.90,
    "bucket": 0.30,
    "chair": 0.45,  # Seat height ~18"
}

# Lane B: Bulk/pile prompts for Lang-SAM
BULK_PROMPTS = [
    "pile of junk",
    "debris pile", 
    "garbage bags",
    "cardboard boxes",
    "mixed waste",
    "yard waste",
    "construction debris",
]

# Negative prompts to exclude from bulk segmentation
NEGATIVE_PROMPTS = [
    "wall", "floor", "ceiling", "grass", "sky", "tree",
    "driveway", "sidewalk", "fence", "window", "door frame",
]


@dataclass
class LaneAResult:
    """Lane A: Discrete Items (Instance Segmentation)"""
    instances: list[InstanceMask] = field(default_factory=list)
    anchors: list[InstanceMask] = field(default_factory=list)


@dataclass
class LaneBResult:
    """Lane B: Bulk Segmentation"""
    bulk_mask_url: Optional[str] = None
    bulk_mask_data: Optional[bytes] = None
    bulk_mask_np: Optional[object] = None  # numpy array (H, W) boolean mask (after ground sub)
    bulk_raw_np: Optional[object] = None   # v8.2.2: mask BEFORE ground sub (for depth-aware refinement)
    bulk_area_ratio: float = 0.0
    clipped_by_wall: bool = False  # True if geometric sanity check applied
    # v7.2: Risk signals for fusion (populated by geometry enrichment)
    mask_risk: float = 0.0           # 0-1 overall leakage risk
    vertical_pct: float = 0.0        # Fraction on vertical surfaces
    boundary_spike: float = 0.0      # Height anomaly at mask edges
    far_pct: float = 0.0             # Background contamination
    # v8.2.2: Depth-aware ground subtraction metric
    depth_sub_saved_ratio: float = 0.0  # 1 - (true_floor_overlap / ground_overlap), for FP_GUARD skip


@dataclass
class LaneCResult:
    """Lane C: Scene Classification"""
    scene_type: SceneType = SceneType.UNKNOWN
    confidence: float = 0.0
    has_visible_floor: bool = False
    has_visible_walls: bool = False


@dataclass
class LaneDResult:
    """Lane D: Ground/Floor Mask (SegFormer)"""
    ground_mask_np: Optional[object] = None  # numpy array (H, W) boolean mask
    safe_bg_mask_np: Optional[object] = None  # sky, building, fence, person, car (always subtract)
    risky_bg_mask_np: Optional[object] = None  # vegetation (subtract only if NOT yard-waste)
    ground_area_ratio: float = 0.0
    model_used: str = ""  # "cityscapes" or "ade20k"
    labels_found: list[str] = field(default_factory=list)
    safe_bg_labels: list[str] = field(default_factory=list)
    risky_bg_labels: list[str] = field(default_factory=list)


@dataclass
class PerceptionResult:
    """Combined result from all perception lanes."""
    frame_id: str
    lane_a: LaneAResult
    lane_b: LaneBResult
    lane_c: LaneCResult
    lane_d: Optional[LaneDResult] = None  # Ground mask (optional)


def _generate_instance_id(label: str, bbox: tuple, frame_id: str) -> str:
    """Generate stable instance ID from label + position + frame."""
    key = f"{frame_id}:{label}:{bbox[0]}:{bbox[1]}:{bbox[2]}:{bbox[3]}"
    return hashlib.md5(key.encode()).hexdigest()[:12]


def _run_lane_a_yolo_seg(data_uri: str, frame_id: str, working_pil=None) -> LaneAResult:
    """
    Lane A: Instance Segmentation using LOCAL YOLO11-Seg.
    Detects high-value items and calibration anchors.
    No Replicate API - runs on local GPU/MPS/CPU.
    """
    from .yolo11_runner import get_yolo11_runner, InstanceMask as YoloMask
    import base64
    from io import BytesIO
    from PIL import Image
    
    result = LaneAResult()
    
    try:
        # Get or decode image
        if working_pil is not None:
            image = working_pil
        else:
            # Decode from data URI
            if "," in data_uri:
                b64_data = data_uri.split(",", 1)[1]
            else:
                b64_data = data_uri
            
            img_data = base64.b64decode(b64_data)
            image = Image.open(BytesIO(img_data)).convert("RGB")
        
        # Run local YOLO11
        runner = get_yolo11_runner()
        detections = runner.detect(image, conf_threshold=0.35)
        
        # Convert YOLO11 detections to our InstanceMask format
        for det in detections:
            # Generate stable instance ID
            instance_id = _generate_instance_id(det.label, det.bbox, frame_id)
            
            # Classify item type
            label_lower = det.label.lower()
            is_high_value = any(hv in label_lower for hv in HIGH_VALUE_ITEMS)
            is_anchor = any(anchor in label_lower for anchor in ANCHOR_ITEMS.keys())
            
            mask = InstanceMask(
                instance_id=instance_id,
                label=det.label,
                confidence=det.confidence,
                bbox=tuple(int(x) for x in det.bbox),
                mask_url=None,  # Local mask, no URL
                mask_data=None,
                area_ratio=det.area_ratio,
                is_anchor=is_anchor,
                is_high_value=is_high_value,
            )
            
            # Store numpy mask for volume calculations
            mask._mask_np = det.mask_np
            
            result.instances.append(mask)
            if is_anchor:
                result.anchors.append(mask)
        
        print(f"[Lane A] YOLO11 detected {len(result.instances)} items, {len(result.anchors)} anchors")
                
    except Exception as e:
        print(f"[Lane A] YOLO11 error: {e}")
        import traceback
        traceback.print_exc()
        
    return result


def _run_lane_b_bulk_segmentation(
    data_uri: str, 
    working_pil=None, 
    preproc_sha256: str = None,
    frame_id: str = None,
    job_id: str = None,
    ground_mask: "np.ndarray" = None
) -> LaneBResult:
    """
    Lane B: Bulk Segmentation using LOCAL Grounding DINO + SAM2.
    Same architecture as Lang-SAM but fully local GPU inference.
    
    v6.6.0: Uses cache when preproc_sha256 is provided.
    v7.2: Passes frame_id and job_id for DINO box overlay saving.
    v8.2: Accepts ground_mask for cleanup pipeline.
    """
    from .grounded_sam_runner import get_grounded_sam_runner
    import base64
    import numpy as np
    from PIL import Image
    from io import BytesIO
    
    result = LaneBResult()
    
    try:
        # Get or decode image
        if working_pil is not None:
            image = working_pil
        else:
            # Decode from data URI
            if "," in data_uri:
                b64_data = data_uri.split(",", 1)[1]
            else:
                b64_data = data_uri
            
            img_data = base64.b64decode(b64_data)
            image = Image.open(BytesIO(img_data)).convert("RGB")
        
        # Run local Grounding DINO + SAM2
        runner = get_grounded_sam_runner()
        
        # v6.6.0: Use cached segmentation when preproc_sha256 is available
        # v8.2: Pass ground_mask for cleanup pipeline
        if preproc_sha256:
            seg_result = runner.segment_cached(
                image, preproc_sha256, 
                frame_id=frame_id, job_id=job_id,
                ground_mask=ground_mask
            )
        else:
            seg_result = runner.segment(image, frame_id=frame_id, job_id=job_id, ground_mask=ground_mask)
        
        if seg_result.error:
            print(f"[Lane B] GroundedSAM error: {seg_result.error}")
            return result
        
        if seg_result.mask_np is not None:
            result.bulk_mask_np = seg_result.mask_np
            result.bulk_raw_np = seg_result.mask_raw_np  # v8.2.2: Store pre-ground-sub mask
            result.bulk_area_ratio = seg_result.area_ratio
            print(f"[Lane B] GroundedSAM mask: {seg_result.mask_np.shape}, area={seg_result.area_ratio:.1%}, conf={seg_result.confidence:.2f}")
        else:
            print(f"[Lane B] GroundedSAM returned no mask")
                
    except Exception as e:
        print(f"[Lane B] GroundedSAM error: {e}")
        import traceback
        traceback.print_exc()
        
    return result


def _run_lane_c_scene_classification(data_uri: str) -> LaneCResult:
    """
    Lane C: Scene Classification.
    Determines ground plane logic to use in Stage 3.
    """
    result = LaneCResult()
    model_id = "salesforce/blip:2e1dddc8621f72155f24cf2e0adbde548458d3cab9f00c0139eea840d0ac4746"
    raw_answer = ""
    
    # Simple heuristic-based classification
    # In production, this would use a dedicated classifier or LLM
    try:
        import replicate
        
        # Use BLIP for scene understanding
        output = replicate.run(
            model_id,
            input={
                "image": data_uri,
                "task": "visual_question_answering",
                "question": "Is this scene indoors or outdoors? Is the ground flat or uneven?",
            }
        )
        
        raw_answer = str(output).lower() if output else ""
        
        if "indoor" in raw_answer:
            result.scene_type = SceneType.INDOOR_FLAT
            result.has_visible_floor = True
            result.has_visible_walls = True
        elif "outdoor" in raw_answer and "uneven" in raw_answer:
            result.scene_type = SceneType.UNEVEN_GROUND
            result.has_visible_floor = True
        elif "outdoor" in raw_answer or "driveway" in raw_answer:
            result.scene_type = SceneType.OUTDOOR_DRIVEWAY
            result.has_visible_floor = True
        else:
            result.scene_type = SceneType.UNKNOWN
            
        result.confidence = 0.7  # Heuristic confidence
        
    except Exception as e:
        print(f"[Lane C] Scene classification error: {e}")
        result.scene_type = SceneType.UNKNOWN
        result.confidence = 0.0
    
    # Debug output
    print(f"[Lane C] scene_type: {result.scene_type.value}")
    print(f"[Lane C] scene_confidence: {result.confidence}")
    print(f"[Lane C] raw_answer: {raw_answer[:100]}")
    print(f"[Lane C] scene_model_id: {model_id.split(':')[0]}")
        
    return result


def _run_segformer_model(jpeg_bytes: bytes, model_id: str, floor_labels: set, h: int, w: int, hf_token: str) -> tuple:
    """
    Run a single SegFormer model and return (ground_mask, ground_area_pct, labels_found).
    Returns (None, 0.0, []) on timeout or error.
    """
    import requests
    import numpy as np
    from PIL import Image
    from io import BytesIO
    import base64
    
    try:
        api_url = f"https://router.huggingface.co/hf-inference/models/{model_id}"
        headers = {
            "Authorization": f"Bearer {hf_token}",
            "Content-Type": "image/jpeg",
        }
        
        response = requests.post(api_url, headers=headers, data=jpeg_bytes, timeout=90)
        
        if response.status_code != 200:
            return None, 0.0, []
        
        segments = response.json()
        if not segments or not isinstance(segments, list):
            return None, 0.0, []
        
        # Build ground mask from matching labels
        ground_mask = np.zeros((h, w), dtype=bool)
        labels_found = []
        
        for seg in segments:
            label = seg.get("label", "").lower()
            is_floor_like = any(fl in label for fl in floor_labels)
            
            if is_floor_like and "mask" in seg:
                mask_data = base64.b64decode(seg["mask"])
                mask_img = Image.open(BytesIO(mask_data)).convert("L")
                
                if mask_img.size != (w, h):
                    mask_img = mask_img.resize((w, h), Image.NEAREST)
                
                mask_np = np.array(mask_img) > 127
                ground_mask |= mask_np
                labels_found.append(label)
        
        total_pixels = h * w
        ground_area_pct = (float(np.sum(ground_mask)) / total_pixels) * 100 if total_pixels > 0 else 0.0
        
        return ground_mask, ground_area_pct, labels_found
        
    except Exception as e:
        return None, 0.0, []


def _run_lane_d_ground_mask(working_pil, scene_type: SceneType) -> LaneDResult:
    """
    Lane D: Ground/Floor Mask using LOCAL SegFormer on MPS.
    Runs both Cityscapes and ADE20K locally, chooses best per-frame.
    Falls back to HF API only if local inference fails.
    """
    import numpy as np
    from PIL import Image
    import hashlib
    
    result = LaneDResult()
    
    try:
        # Ensure RGB
        if working_pil.mode != "RGB":
            working_pil = working_pil.convert("RGB")
        
        h, w = working_pil.height, working_pil.width
        
        # Input debug
        print(f"[Lane D] input: {w}x{h}")
        
        # === TRY LOCAL INFERENCE FIRST ===
        from .segformer_runner import run_local_cityscapes, run_local_ade
        
        # Run Cityscapes locally
        print(f"[Lane D] Running Cityscapes (local)...")
        city_result = run_local_cityscapes(working_pil)
        city_pct = city_result.ground_area_pct if city_result.error is None else 0.0
        city_mask = city_result.ground_mask
        city_labels = city_result.labels_found
        print(f"[Lane D] ground_area_city: {city_pct:.1f}% labels={city_labels}")
        
        # Run ADE locally  
        print(f"[Lane D] Running ADE (local)...")
        ade_result = run_local_ade(working_pil)
        ade_pct = ade_result.ground_area_pct if ade_result.error is None else 0.0
        ade_mask = ade_result.ground_mask
        ade_labels = ade_result.labels_found
        print(f"[Lane D] ground_area_ade: {ade_pct:.1f}% labels={ade_labels}")
        
        # === CHOOSE MODEL PER-FRAME ===
        chosen_model = "none"
        chosen_mask = None
        chosen_pct = 0.0
        chosen_labels = []
        chosen_safe_bg = None
        chosen_risky_bg = None
        chosen_safe_labels = []
        chosen_risky_labels = []
        
        # Decision logic:
        # If city >= 5% AND city >= ade + 2% → use Cityscapes
        # Else if ade >= 5% → use ADE
        # Else → no semantic floor mask
        
        if city_pct >= 5.0 and city_pct >= (ade_pct + 2.0):
            chosen_model = "cityscapes_local"
            chosen_mask = city_mask
            chosen_pct = city_pct
            chosen_labels = city_labels
            chosen_safe_bg = city_result.safe_bg_mask
            chosen_risky_bg = city_result.risky_bg_mask
            chosen_safe_labels = city_result.safe_bg_labels
            chosen_risky_labels = city_result.risky_bg_labels
        elif ade_pct >= 5.0:
            chosen_model = "ade_local"
            chosen_mask = ade_mask
            chosen_pct = ade_pct
            chosen_labels = ade_labels
            chosen_safe_bg = ade_result.safe_bg_mask
            chosen_risky_bg = ade_result.risky_bg_mask
            chosen_safe_labels = ade_result.safe_bg_labels
            chosen_risky_labels = ade_result.risky_bg_labels
        else:
            # Neither model provides sufficient floor coverage
            chosen_model = "none"
            chosen_mask = np.zeros((h, w), dtype=bool)
            chosen_pct = 0.0
            chosen_labels = []
            chosen_safe_bg = np.zeros((h, w), dtype=bool)
            chosen_risky_bg = np.zeros((h, w), dtype=bool)
        
        # Set result
        result.model_used = chosen_model
        result.ground_mask_np = chosen_mask if chosen_mask is not None else np.zeros((h, w), dtype=bool)
        result.ground_area_ratio = chosen_pct / 100.0
        result.labels_found = chosen_labels
        result.safe_bg_mask_np = chosen_safe_bg if chosen_safe_bg is not None else np.zeros((h, w), dtype=bool)
        result.risky_bg_mask_np = chosen_risky_bg if chosen_risky_bg is not None else np.zeros((h, w), dtype=bool)
        result.safe_bg_labels = chosen_safe_labels
        result.risky_bg_labels = chosen_risky_labels
        
        # Debug output
        safe_pct = 100.0 * np.mean(result.safe_bg_mask_np)
        risky_pct = 100.0 * np.mean(result.risky_bg_mask_np)
        print(f"[Lane D] chosen_model: {chosen_model}")
        print(f"[Lane D] chosen_ground_area: {chosen_pct:.1f}%")
        print(f"[Lane D] safe_bg: {safe_pct:.1f}%, risky_bg: {risky_pct:.1f}%")
        
        # Assertion
        if result.ground_mask_np is not None:
            assert result.ground_mask_np.shape == (h, w), f"floor_mask.shape mismatch"
        
    except Exception as e:
        print(f"[Lane D] SegFormer error: {e}")
        import traceback
        traceback.print_exc()
    
    return result


def run_perception(
    frame_id: str, 
    data_uri: str, 
    working_pil=None, 
    preproc_sha256: str = None,
    job_id: str = None
) -> PerceptionResult:
    """
    Stage 2 Entry Point: Run all perception lanes.
    
    Args:
        frame_id: Unique identifier for this frame
        data_uri: Base64 data URI of the image
        working_pil: Optional PIL Image at working resolution (for Lane D)
        preproc_sha256: Optional hash for Lane B caching (v6.6.0)
        job_id: Job ID for overlay saving (v7.2)
        
    Returns:
        PerceptionResult with outputs from all lanes
    """
    # v8.2: Run lanes in correct order (Lane D before Lane B for ground mask)
    lane_a = _run_lane_a_yolo_seg(data_uri, frame_id, working_pil=working_pil)
    lane_c = _run_lane_c_scene_classification(data_uri)
    
    # Lane D: Ground segmentation (runs before Lane B)
    lane_d = None
    ground_mask = None
    if working_pil is not None:
        lane_d = _run_lane_d_ground_mask(working_pil, lane_c.scene_type)
        if lane_d and lane_d.ground_mask_np is not None:
            ground_mask = lane_d.ground_mask_np
    
    # Lane B: Bulk segmentation (now with ground mask for v8.2 cleanup)
    lane_b = _run_lane_b_bulk_segmentation(
        data_uri, working_pil=working_pil, preproc_sha256=preproc_sha256,
        frame_id=frame_id, job_id=job_id, ground_mask=ground_mask
    )
    
    return PerceptionResult(
        frame_id=frame_id,
        lane_a=lane_a,
        lane_b=lane_b,
        lane_c=lane_c,
        lane_d=lane_d,
    )


# =============================================================================
# v7.2: GEOMETRY-BASED MASK ENRICHMENT
# =============================================================================

def _detect_mask_leakage_geometry(
    mask: "np.ndarray",
    point_pixel_map: object,  # PointPixelMap from geometry.py
    ground_normal: "np.ndarray",
    far_depth_threshold: float = 8.0
) -> dict:
    """
    v7.2: Detect mask leakage using point cloud geometry.
    
    Uses boundary-focused normal estimation to detect:
    - vertical_pct: Fraction of boundary on vertical surfaces (walls)
    - far_pct: Fraction of mask on far background (>8m depth)
    - boundary_spike: Height anomaly ratio (boundary vs interior)
    
    Returns:
        dict with leakage signals and overall mask_risk (0-1)
    """
    import numpy as np
    from .normal_estimation import estimate_boundary_normals, compute_verticality
    
    result = {
        "vertical_pct": 0.0,
        "far_pct": 0.0,
        "boundary_spike": 1.0,
        "mask_risk": 0.0
    }
    
    if mask is None or point_pixel_map is None:
        return result
    
    points = point_pixel_map.points
    pixel_indices = point_pixel_map.pixel_indices
    pixel_to_point = point_pixel_map.pixel_to_point
    
    if len(points) == 0:
        return result
    
    try:
        # Get boundary normals
        boundary_pts, boundary_normals = estimate_boundary_normals(
            points, pixel_indices, mask, max_samples=3000
        )
        
        if len(boundary_normals) > 10:
            result["vertical_pct"] = compute_verticality(boundary_normals, ground_normal)
        
        # Far-clip contamination: % of mask at depth > threshold
        H, W = mask.shape
        mask_coords = np.argwhere(mask)
        far_count = 0
        total_valid = 0
        
        for r, c in mask_coords[::10]:  # Sample every 10th pixel for speed
            if 0 <= r < H and 0 <= c < W:
                pt_idx = pixel_to_point[r, c]
                if pt_idx >= 0:
                    depth = np.linalg.norm(points[pt_idx])  # Distance from origin
                    total_valid += 1
                    if depth > far_depth_threshold:
                        far_count += 1
        
        if total_valid > 0:
            result["far_pct"] = far_count / total_valid
        
        # Boundary spike: compare boundary heights to interior heights
        from scipy.ndimage import binary_erosion
        interior = binary_erosion(mask, iterations=5)
        
        if np.sum(interior) > 100:
            boundary_mask = mask & ~interior
            
            boundary_heights = []
            interior_heights = []
            
            boundary_coords = np.argwhere(boundary_mask)
            interior_coords = np.argwhere(interior)
            
            for r, c in boundary_coords[::5]:
                if 0 <= r < H and 0 <= c < W:
                    pt_idx = pixel_to_point[r, c]
                    if pt_idx >= 0:
                        boundary_heights.append(points[pt_idx, 1])  # Y is height
            
            for r, c in interior_coords[::5]:
                if 0 <= r < H and 0 <= c < W:
                    pt_idx = pixel_to_point[r, c]
                    if pt_idx >= 0:
                        interior_heights.append(points[pt_idx, 1])
            
            if len(boundary_heights) > 10 and len(interior_heights) > 10:
                boundary_p95 = np.percentile(boundary_heights, 95)
                interior_p95 = np.percentile(interior_heights, 95)
                if interior_p95 > 0.1:
                    result["boundary_spike"] = boundary_p95 / interior_p95
        
        # Combine into overall mask_risk (0-1)
        risk = 0.0
        risk += result["vertical_pct"] * 2.0       # Walls are bad
        risk += result["far_pct"] * 3.0            # Background is very bad
        risk += max(0, result["boundary_spike"] - 1.5) * 0.5  # Height spike
        result["mask_risk"] = min(1.0, risk)
        
    except Exception as e:
        print(f"[Leakage] Error in leakage detection: {e}")
        result["mask_risk"] = 0.0  # Fail-open
    
    return result


def enrich_perception_with_geometry(
    lane_b: LaneBResult,
    point_pixel_map: object,  # PointPixelMap from geometry.py
    ground_normal: "np.ndarray"
) -> LaneBResult:
    """
    v7.2: Enrich perception with geometry-based leakage signals.
    
    Called by orchestrator after geometry stage completes.
    Updates lane_b mask_risk fields in place.
    """
    import numpy as np
    
    if point_pixel_map is None or lane_b.bulk_mask_np is None:
        return lane_b
    
    leakage = _detect_mask_leakage_geometry(
        mask=lane_b.bulk_mask_np,
        point_pixel_map=point_pixel_map,
        ground_normal=ground_normal
    )
    
    lane_b.mask_risk = leakage["mask_risk"]
    lane_b.vertical_pct = leakage["vertical_pct"]
    lane_b.far_pct = leakage["far_pct"]
    lane_b.boundary_spike = leakage["boundary_spike"]
    
    print(f"[Enrichment] mask_risk={lane_b.mask_risk:.2f} "
          f"(vert={lane_b.vertical_pct:.2f}, far={lane_b.far_pct:.2f}, spike={lane_b.boundary_spike:.2f})")
    
    return lane_b


# =============================================================================
# v8.2.2: DEPTH-AWARE GROUND SUBTRACTION
# =============================================================================

def apply_depth_aware_ground_sub(
    bulk_mask: "np.ndarray",
    ground_mask: "np.ndarray",
    point_pixel_map: object,  # PointPixelMap from geometry.py
    t_floor_m: float = 0.05,  # 5cm threshold for "true floor"
) -> tuple:
    """
    v8.2.2: Geometry-aware ground subtraction.
    
    Only subtracts bulk pixels that are BOTH:
    1. Predicted as ground by SegFormer (ground_mask)
    2. Actually near the fitted floor plane (|Y| < t_floor_m)
    
    This prevents "tarp counted as floor" from deleting the pile.
    The RANSAC floor plane fitting already computed Y values (height above plane).
    
    Args:
        bulk_mask: Binary mask from Lane B (HxW bool)
        ground_mask: Binary mask from Lane D SegFormer (HxW bool)
        point_pixel_map: PointPixelMap with Y values from geometry.py
        t_floor_m: Threshold in meters for "true floor" (default 5cm)
    
    Returns:
        tuple: (refined_bulk_mask, saved_ratio) where:
            - refined_bulk_mask: mask with depth-aware ground subtraction applied
            - saved_ratio: 1 - (true_floor_overlap / ground_overlap), for FP_GUARD skip
    """
    import numpy as np
    import cv2

    
    if bulk_mask is None or ground_mask is None or point_pixel_map is None:
        print("[DEPTH_GROUND_SUB] Skipped: missing inputs")
        return bulk_mask, 0.0
    
    h, w = bulk_mask.shape
    points = point_pixel_map.points  # Nx3 (X, Y, Z) - Y is height above floor
    pixel_to_point = point_pixel_map.pixel_to_point  # HxW → point index or -1
    
    if len(points) == 0:
        print("[DEPTH_GROUND_SUB] Skipped: no points")
        return bulk_mask, 0.0
    
    # Resize pixel_to_point to match bulk_mask if needed
    ppm_h, ppm_w = pixel_to_point.shape
    if (ppm_h, ppm_w) != (h, w):
        # Simple nearest-neighbor resize
        pixel_to_point_resized = cv2.resize(
            pixel_to_point.astype(np.float32),
            (w, h),
            interpolation=cv2.INTER_NEAREST
        ).astype(np.int32)
    else:
        pixel_to_point_resized = pixel_to_point
    
    # Ensure ground_mask is same size
    if ground_mask.shape != (h, w):
        ground_mask = cv2.resize(
            ground_mask.astype(np.uint8),
            (w, h),
            interpolation=cv2.INTER_NEAREST
        ).astype(bool)
    
    # Build Y-map (height above floor plane) for each pixel
    y_map = np.full((h, w), np.nan, dtype=np.float32)
    valid_points = pixel_to_point_resized >= 0
    point_indices = pixel_to_point_resized[valid_points]
    y_map[valid_points] = points[point_indices, 1]  # Y is height above floor
    
    # "True floor" = pixels where |Y| < threshold (actually on the floor plane)
    # Use np.abs because sign may vary depending on floor orientation
    is_true_floor = np.abs(y_map) < t_floor_m
    # Handle NaN values (no point data)
    is_true_floor[np.isnan(y_map)] = False
    
    # Only subtract ground pixels that are truly on the floor plane
    # This prevents the "earth" label on the tarp/pile from being subtracted
    true_floor_ground = ground_mask & is_true_floor
    
    # Count statistics for logging
    ground_count = np.sum(ground_mask & bulk_mask)
    true_floor_count = np.sum(true_floor_ground & bulk_mask)
    saved_count = ground_count - true_floor_count
    
    # Apply depth-aware subtraction
    bulk_refined = bulk_mask & ~true_floor_ground
    
    # Calculate how much we saved vs. naive ground subtraction
    naive_sub_count = np.sum(ground_mask & bulk_mask)
    smart_sub_count = np.sum(true_floor_ground & bulk_mask)
    bulk_before = np.sum(bulk_mask)
    bulk_after = np.sum(bulk_refined)
    
    if naive_sub_count > 0:
        saved_pct = (saved_count / ground_count) * 100 if ground_count > 0 else 0
        print(f"[DEPTH_GROUND_SUB] t_floor={t_floor_m:.3f}m: "
              f"ground∩bulk={ground_count:,} → true_floor∩bulk={smart_sub_count:,} "
              f"(saved {saved_count:,} px, {saved_pct:.1f}%)")
    else:
        print(f"[DEPTH_GROUND_SUB] No ground/bulk overlap to process")
    
    area_before = (bulk_before / (h * w)) * 100
    area_after = (bulk_after / (h * w)) * 100
    print(f"[DEPTH_GROUND_SUB] bulk_mask: {area_before:.1f}% → {area_after:.1f}%")
    
    # v8.2.2: Compute saved_ratio for FP_GUARD skip logic
    # saved_ratio = 1 - (true_floor_overlap / ground_overlap)
    saved_ratio = 1.0 - (true_floor_count / max(ground_count, 1))
    
    return bulk_refined, saved_ratio


# =============================================================================
# v8.7: MULTI-FRAME MASK CONSENSUS (Root Cause Fix #2)
# =============================================================================

def compute_mask_consensus(masks: list, min_agreement: float = 0.5) -> tuple:
    """
    v8.7: Anti-contamination consensus - only keep pixels where frames agree.
    
    This stabilizes Lane B masks by rejecting pixels that only appear in a
    minority of frames (likely noise/background contamination).
    
    Args:
        masks: List of boolean numpy arrays (HxW) from multiple frames
        min_agreement: Minimum fraction of frames that must include a pixel (default 0.5)
        
    Returns:
        tuple: (consensus_mask, agreement_ratio)
            - consensus_mask: Boolean mask where majority of frames agree
            - agreement_ratio: Average IoU between consensus and individual masks
    """
    import numpy as np
    
    if not masks or len(masks) == 0:
        return None, 0.0
    
    if len(masks) == 1:
        return masks[0], 1.0
    
    # Find common shape (resize to smallest if needed)
    shapes = [m.shape for m in masks if m is not None]
    if not shapes:
        return None, 0.0
    
    target_h = min(s[0] for s in shapes)
    target_w = min(s[1] for s in shapes)
    
    # Resize masks to common shape
    import cv2
    resized_masks = []
    for m in masks:
        if m is None:
            continue
        if m.shape == (target_h, target_w):
            resized_masks.append(m.astype(np.float32))
        else:
            resized = cv2.resize(m.astype(np.uint8), (target_w, target_h), 
                                 interpolation=cv2.INTER_NEAREST)
            resized_masks.append(resized.astype(np.float32))
    
    if not resized_masks:
        return None, 0.0
    
    # Stack and vote
    stacked = np.stack(resized_masks, axis=0)  # NxHxW
    vote_count = np.sum(stacked, axis=0)  # HxW (count of frames that include each pixel)
    n_frames = len(resized_masks)
    
    # Majority vote: pixel included if >= min_agreement fraction of frames
    min_votes = max(1, int(n_frames * min_agreement))
    consensus = vote_count >= min_votes
    
    # Calculate agreement ratio (how well consensus matches individual frames)
    ious = []
    for m in resized_masks:
        intersection = np.sum(consensus & (m > 0.5))
        union = np.sum(consensus | (m > 0.5))
        if union > 0:
            ious.append(intersection / union)
    
    agreement_ratio = np.mean(ious) if ious else 0.0
    
    # Log consensus statistics
    original_areas = [np.sum(m > 0.5) for m in resized_masks]
    consensus_area = np.sum(consensus)
    print(f"[MASK_CONSENSUS] {n_frames} frames → consensus: "
          f"areas={[f'{a:,}' for a in original_areas]} → {consensus_area:,} pixels, "
          f"agreement={agreement_ratio:.2f}")
    
    return consensus.astype(bool), agreement_ratio
