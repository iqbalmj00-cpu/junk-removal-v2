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
    bulk_mask_np: Optional[object] = None  # numpy array (H, W) boolean mask
    bulk_area_ratio: float = 0.0
    clipped_by_wall: bool = False  # True if geometric sanity check applied


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
    ground_area_ratio: float = 0.0
    model_used: str = ""  # "cityscapes" or "ade20k"
    labels_found: list[str] = field(default_factory=list)


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


def _run_lane_b_bulk_segmentation(data_uri: str, working_pil=None) -> LaneBResult:
    """
    Lane B: Bulk Segmentation using LOCAL SAM3.
    Segments "junk" with text prompting.
    No Replicate API - runs on local GPU/MPS/CPU.
    """
    from .sam3_runner import get_sam3_runner
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
        
        # Run local SAM3
        runner = get_sam3_runner()
        sam_result = runner.segment(
            image, 
            prompt="pile of junk, debris, garbage bags, cardboard boxes"
        )
        
        if sam_result.error:
            print(f"[Lane B] SAM3 error: {sam_result.error}")
            return result
        
        if sam_result.mask_np is not None:
            result.bulk_mask_np = sam_result.mask_np
            result.bulk_area_ratio = sam_result.area_ratio
            print(f"[Lane B] SAM3 mask: {sam_result.mask_np.shape}, area={sam_result.area_ratio:.1%}, conf={sam_result.confidence:.2f}")
        else:
            print(f"[Lane B] SAM3 returned no mask")
                
    except Exception as e:
        print(f"[Lane B] SAM3 error: {e}")
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
        
        # Decision logic:
        # If city >= 5% AND city >= ade + 2% → use Cityscapes
        # Else if ade >= 5% → use ADE
        # Else → no semantic floor mask
        
        if city_pct >= 5.0 and city_pct >= (ade_pct + 2.0):
            chosen_model = "cityscapes_local"
            chosen_mask = city_mask
            chosen_pct = city_pct
            chosen_labels = city_labels
        elif ade_pct >= 5.0:
            chosen_model = "ade_local"
            chosen_mask = ade_mask
            chosen_pct = ade_pct
            chosen_labels = ade_labels
        else:
            # Neither model provides sufficient floor coverage
            chosen_model = "none"
            chosen_mask = np.zeros((h, w), dtype=bool)
            chosen_pct = 0.0
            chosen_labels = []
        
        # Set result
        result.model_used = chosen_model
        result.ground_mask_np = chosen_mask if chosen_mask is not None else np.zeros((h, w), dtype=bool)
        result.ground_area_ratio = chosen_pct / 100.0
        result.labels_found = chosen_labels
        
        # Debug output
        print(f"[Lane D] chosen_model: {chosen_model}")
        print(f"[Lane D] chosen_ground_area: {chosen_pct:.1f}%")
        print(f"[Lane D] floor_mask_area_pct_final: {chosen_pct:.1f}%")
        
        # Assertion
        if result.ground_mask_np is not None:
            assert result.ground_mask_np.shape == (h, w), f"floor_mask.shape mismatch"
        
    except Exception as e:
        print(f"[Lane D] SegFormer error: {e}")
        import traceback
        traceback.print_exc()
    
    return result


def run_perception(frame_id: str, data_uri: str, working_pil=None) -> PerceptionResult:
    """
    Stage 2 Entry Point: Run all perception lanes.
    
    Args:
        frame_id: Unique identifier for this frame
        data_uri: Base64 data URI of the image
        working_pil: Optional PIL Image at working resolution (for Lane D)
        
    Returns:
        PerceptionResult with outputs from all lanes
    """
    # Run lanes (in production, run in parallel)
    lane_a = _run_lane_a_yolo_seg(data_uri, frame_id, working_pil=working_pil)
    lane_b = _run_lane_b_bulk_segmentation(data_uri, working_pil=working_pil)
    lane_c = _run_lane_c_scene_classification(data_uri)
    
    # Lane D depends on Lane C scene type and needs the PIL image
    lane_d = None
    if working_pil is not None:
        lane_d = _run_lane_d_ground_mask(working_pil, lane_c.scene_type)
    
    return PerceptionResult(
        frame_id=frame_id,
        lane_a=lane_a,
        lane_b=lane_b,
        lane_c=lane_c,
        lane_d=lane_d,
    )
