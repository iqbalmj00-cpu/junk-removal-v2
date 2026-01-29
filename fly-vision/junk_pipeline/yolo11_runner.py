"""
YOLO11 Runner: Local YOLO11-Seg Inference
Replaces Replicate API for discrete object detection (Lane A)
"""

from dataclasses import dataclass
from typing import Optional
import numpy as np
from PIL import Image


@dataclass
class InstanceMask:
    """Detected object with segmentation mask."""
    instance_id: str
    label: str
    confidence: float
    bbox: tuple  # (x1, y1, x2, y2)
    mask_np: np.ndarray  # (H, W) boolean mask
    area_ratio: float
    is_anchor: bool = False
    is_high_value: bool = False


# Anchor items for scale calibration (known real-world heights)
ANCHOR_ITEMS = {
    "door", "person", "trash can", "garbage bin", "tire", 
    "refrigerator", "washing machine", "dryer"
}

# High-value items that may need special handling
HIGH_VALUE_ITEMS = {
    "refrigerator", "washing machine", "dryer", "sofa", "couch",
    "mattress", "tv", "television", "piano"
}


class YOLO11Runner:
    """
    Singleton YOLO11-Seg runner for local GPU inference.
    
    Uses yolo11m-seg.pt for best speed/accuracy balance.
    """
    _instance = None
    _model = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._model is None:
            self._load_model()
    
    def _load_model(self):
        """Load YOLO11 model (downloads on first run)."""
        try:
            from ultralytics import YOLO
            import torch
            
            # Determine device
            if torch.cuda.is_available():
                device = "cuda"
            elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                device = "mps"
            else:
                device = "cpu"
            
            print(f"[YOLO11] Loading yolo11m-seg.pt on {device}...")
            self._model = YOLO("yolo11m-seg.pt")
            self._model.to(device)
            print(f"[YOLO11] Model loaded successfully")
            
        except Exception as e:
            print(f"[YOLO11] Failed to load model: {e}")
            self._model = None
    
    def detect(self, image: Image.Image, conf_threshold: float = 0.25) -> list[InstanceMask]:
        """
        Run YOLO11-Seg on image.
        
        Args:
            image: PIL Image to process
            conf_threshold: Minimum confidence threshold
            
        Returns:
            List of InstanceMask objects with detections
        """
        if self._model is None:
            print("[YOLO11] Model not loaded, returning empty detections")
            return []
        
        try:
            # Convert PIL to numpy if needed
            if isinstance(image, Image.Image):
                image_np = np.array(image)
            else:
                image_np = image
            
            # Run inference
            results = self._model(image_np, conf=conf_threshold, verbose=False)
            
            if not results or len(results) == 0:
                return []
            
            result = results[0]
            detections = []
            
            # Get image dimensions for area ratio
            h, w = image_np.shape[:2]
            image_area = h * w
            
            # Parse detections
            if result.boxes is not None and len(result.boxes) > 0:
                boxes = result.boxes.xyxy.cpu().numpy()
                classes = result.boxes.cls.cpu().numpy()
                confidences = result.boxes.conf.cpu().numpy()
                names = result.names
                
                # Get masks if available
                masks = None
                if result.masks is not None:
                    masks = result.masks.data.cpu().numpy()
                
                for i in range(len(boxes)):
                    # Get class label
                    class_id = int(classes[i])
                    label = names.get(class_id, f"class_{class_id}")
                    confidence = float(confidences[i])
                    bbox = tuple(boxes[i].tolist())
                    
                    # Get mask or create from bbox
                    if masks is not None and i < len(masks):
                        mask_np = masks[i].astype(bool)
                        # Resize mask to image dimensions if needed
                        if mask_np.shape != (h, w):
                            from PIL import Image as PILImage
                            mask_pil = PILImage.fromarray(mask_np.astype(np.uint8) * 255)
                            mask_pil = mask_pil.resize((w, h), PILImage.NEAREST)
                            mask_np = np.array(mask_pil) > 127
                    else:
                        # Create mask from bounding box
                        mask_np = np.zeros((h, w), dtype=bool)
                        x1, y1, x2, y2 = map(int, bbox)
                        mask_np[y1:y2, x1:x2] = True
                    
                    # Calculate area ratio
                    mask_area = np.sum(mask_np)
                    area_ratio = mask_area / image_area
                    
                    # Check if anchor or high-value
                    label_lower = label.lower()
                    is_anchor = any(anchor in label_lower for anchor in ANCHOR_ITEMS)
                    is_high_value = any(hv in label_lower for hv in HIGH_VALUE_ITEMS)
                    
                    detection = InstanceMask(
                        instance_id=f"yolo_{i}",
                        label=label,
                        confidence=confidence,
                        bbox=bbox,
                        mask_np=mask_np,
                        area_ratio=area_ratio,
                        is_anchor=is_anchor,
                        is_high_value=is_high_value,
                    )
                    detections.append(detection)
            
            print(f"[YOLO11] Detected {len(detections)} objects")
            return detections
            
        except Exception as e:
            print(f"[YOLO11] Inference error: {e}")
            return []


# Global instance getter
_runner_instance = None

def get_yolo11_runner() -> YOLO11Runner:
    """Get or create the YOLO11 runner instance."""
    global _runner_instance
    if _runner_instance is None:
        _runner_instance = YOLO11Runner()
    return _runner_instance
