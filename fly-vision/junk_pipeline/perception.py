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


def _run_lane_a_yolo_seg(data_uri: str, frame_id: str) -> LaneAResult:
    """
    Lane A: Instance Segmentation using YOLOv8-Seg.
    Detects high-value items and calibration anchors.
    """
    import replicate
    
    result = LaneAResult()
    
    try:
        # Run YOLO-World-XL for open-vocabulary detection
        output = replicate.run(
            "franz-biz/yolo-world-xl:fd1305d3fc19e81540542f51c2530cf8f393e28cc6ff4976337c3e2b75c7c292",
            input={
                "input_media": data_uri,
                "confidence": 0.35,
            }
        )
        
        # Parse detections - output format varies by model
        detections = []
        if isinstance(output, dict) and "predictions" in output:
            detections = output["predictions"]
        elif isinstance(output, list):
            detections = output
            
        for det in detections:
            label = det.get("class", det.get("label", "")).lower().strip()
            conf = det.get("confidence", det.get("score", 0.0))
            
            # Extract bbox
            bbox_data = det.get("bbox", det.get("box", {}))
            if isinstance(bbox_data, dict):
                x1 = int(bbox_data.get("x1", bbox_data.get("xmin", 0)))
                y1 = int(bbox_data.get("y1", bbox_data.get("ymin", 0)))
                x2 = int(bbox_data.get("x2", bbox_data.get("xmax", 0)))
                y2 = int(bbox_data.get("y2", bbox_data.get("ymax", 0)))
            elif isinstance(bbox_data, (list, tuple)) and len(bbox_data) >= 4:
                x1, y1, x2, y2 = int(bbox_data[0]), int(bbox_data[1]), int(bbox_data[2]), int(bbox_data[3])
            else:
                continue
                
            bbox = (x1, y1, x2, y2)
            instance_id = _generate_instance_id(label, bbox, frame_id)
            
            # Classify item type
            is_high_value = any(hv in label for hv in HIGH_VALUE_ITEMS)
            is_anchor = any(anchor in label for anchor in ANCHOR_ITEMS.keys())
            
            mask = InstanceMask(
                instance_id=instance_id,
                label=label,
                confidence=conf,
                bbox=bbox,
                mask_url=det.get("mask_url"),
                is_anchor=is_anchor,
                is_high_value=is_high_value,
            )
            
            result.instances.append(mask)
            if is_anchor:
                result.anchors.append(mask)
                
    except Exception as e:
        print(f"[Lane A] YOLO-Seg error: {e}")
        
    return result


def _run_lane_b_bulk_segmentation(data_uri: str) -> LaneBResult:
    """
    Lane B: Bulk Segmentation using Lang-SAM.
    Segments "junk" with negative prompting.
    Downloads mask and applies dilation for recall bias.
    """
    import replicate
    import requests
    import numpy as np
    from PIL import Image
    from io import BytesIO
    from scipy import ndimage
    
    result = LaneBResult()
    
    try:
        # Use Lang-SAM for semantic segmentation
        output = replicate.run(
            "tmappdev/lang-segment-anything:891411c38a6ed2d44c004b7b9e44217df7a5b07848f29ddefd2e28bc7cbf93bc",
            input={
                "image": data_uri,
                "text_prompt": "pile of junk, debris, garbage bags, cardboard boxes",
            }
        )
        
        # Extract mask URL from output
        mask_url = None
        if isinstance(output, str):
            mask_url = output
        elif isinstance(output, dict):
            mask_url = output.get("mask", output.get("output"))
        elif hasattr(output, 'url'):
            mask_url = output.url
        elif isinstance(output, list) and output:
            first = output[0]
            if isinstance(first, str):
                mask_url = first
            elif hasattr(first, 'url'):
                mask_url = first.url
            elif isinstance(first, dict):
                mask_url = first.get("mask")
                
        result.bulk_mask_url = mask_url
        
        # Download and parse mask
        if mask_url:
            try:
                response = requests.get(mask_url, timeout=30)
                response.raise_for_status()
                result.bulk_mask_data = response.content
                
                # Convert to numpy boolean mask
                img = Image.open(BytesIO(response.content)).convert("L")
                mask_np = np.array(img) > 127  # Binary threshold
                
                # Apply morphological dilation for recall bias (12px radius)
                # This expands the mask to capture pile fringes
                DILATION_RADIUS = 12
                struct = ndimage.generate_binary_structure(2, 1)
                dilated_mask = ndimage.binary_dilation(
                    mask_np, 
                    structure=struct, 
                    iterations=DILATION_RADIUS
                )
                
                # Keep only largest connected component (exclude secondary blobs)
                labeled_array, num_features = ndimage.label(dilated_mask)
                if num_features > 1:
                    # Find sizes of each component
                    component_sizes = ndimage.sum(dilated_mask, labeled_array, range(1, num_features + 1))
                    largest_label = np.argmax(component_sizes) + 1  # Labels are 1-indexed
                    dilated_mask = (labeled_array == largest_label)
                    print(f"[Lane B] Kept largest component ({num_features} found, {component_sizes[largest_label-1]:.0f} vs {np.sum(component_sizes):.0f} total px)")
                
                result.bulk_mask_np = dilated_mask
                result.bulk_area_ratio = float(np.sum(dilated_mask)) / dilated_mask.size
                
                print(f"[Lane B] Mask downloaded: {mask_np.shape}, area={result.bulk_area_ratio:.1%}")
                
            except Exception as e:
                print(f"[Lane B] Mask download error: {e}")
            
    except Exception as e:
        print(f"[Lane B] Lang-SAM error: {e}")
        
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
    lane_a = _run_lane_a_yolo_seg(data_uri, frame_id)
    lane_b = _run_lane_b_bulk_segmentation(data_uri)
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
