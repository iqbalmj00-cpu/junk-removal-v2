"""
GroundedSAM Runner: Grounding DINO + SAM2 for Open-Vocab Segmentation
Same architecture as Lang-SAM but fully local GPU inference.
"""

from dataclasses import dataclass
from typing import Optional, List
import numpy as np
from PIL import Image


@dataclass
class BulkMaskResult:
    """Result from bulk segmentation."""
    mask_np: Optional[np.ndarray]  # (H, W) boolean mask
    area_ratio: float
    confidence: float
    error: Optional[str] = None


class GroundedSAMRunner:
    """
    Grounding DINO + SAM2 for open-vocabulary segmentation.
    Uses HuggingFace Transformers API.
    """
    _instance = None
    _gdino_model = None
    _gdino_processor = None
    _sam_model = None
    _sam_processor = None
    _device = None
    
    # Detection threshold (lowered for better recall)
    BOX_THRESHOLD = 0.10
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._gdino_model is None:
            self._load_models()
    
    def _load_models(self):
        """Load Grounding DINO and SAM2 models."""
        try:
            import torch
            from transformers import (
                AutoProcessor, 
                AutoModelForZeroShotObjectDetection,
                SamModel,
                SamProcessor,
            )
            
            # Determine device
            if torch.cuda.is_available():
                self._device = "cuda"
            elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                self._device = "mps"
            else:
                self._device = "cpu"
            
            # Load Grounding DINO
            print(f"[GroundedSAM] Loading Grounding DINO on {self._device}...")
            gdino_id = "IDEA-Research/grounding-dino-base"
            self._gdino_processor = AutoProcessor.from_pretrained(gdino_id)
            self._gdino_model = AutoModelForZeroShotObjectDetection.from_pretrained(gdino_id).to(self._device)
            print(f"[GroundedSAM] Grounding DINO loaded")
            
            # Load SAM2
            print(f"[GroundedSAM] Loading SAM2...")
            sam_id = "facebook/sam-vit-base"
            self._sam_processor = SamProcessor.from_pretrained(sam_id)
            self._sam_model = SamModel.from_pretrained(sam_id).to(self._device)
            print(f"[GroundedSAM] SAM2 loaded successfully")
            
        except ImportError as e:
            print(f"[GroundedSAM] Import error: {e}")
            self._gdino_model = None
            
        except Exception as e:
            print(f"[GroundedSAM] Failed to load models: {e}")
            import traceback
            traceback.print_exc()
            self._gdino_model = None
    
    def _run_detection(self, image: Image.Image, prompts: List[str]):
        """Run Grounding DINO detection with given prompts."""
        import torch
        
        # Format prompts: "pile. debris. branches." (lowercase + dot)
        text_prompt = " ".join([f"{p.lower()}." for p in prompts])
        
        gdino_inputs = self._gdino_processor(
            images=image, 
            text=text_prompt, 
            return_tensors="pt"
        ).to(self._device)
        
        with torch.no_grad():
            gdino_outputs = self._gdino_model(**gdino_inputs)
        
        # Post-process detections
        results = self._gdino_processor.post_process_grounded_object_detection(
            gdino_outputs,
            gdino_inputs.input_ids,
            target_sizes=[image.size[::-1]]  # (height, width)
        )[0]
        
        boxes = results["boxes"]
        scores = results["scores"]
        labels = results["labels"]
        
        # Filter by threshold
        mask = scores >= self.BOX_THRESHOLD
        boxes = boxes[mask]
        scores = scores[mask]
        labels = [l for l, m in zip(labels, mask.tolist()) if m]
        
        return boxes, scores, labels
    
    def segment(
        self, 
        image: Image.Image, 
        prompts: List[str] = None
    ) -> BulkMaskResult:
        """
        Run Grounding DINO + SAM2 segmentation.
        
        Args:
            image: PIL Image to process
            prompts: List of text prompts (will be combined with ".")
            
        Returns:
            BulkMaskResult with combined mask
        """
        if self._gdino_model is None or self._sam_model is None:
            return BulkMaskResult(
                mask_np=None,
                area_ratio=0.0,
                confidence=0.0,
                error="Models not loaded"
            )
        
        # Primary prompts for junk/debris - use phrases like Lang-SAM
        primary_prompts = prompts if prompts else [
            "pile of junk",
            "debris pile",
            "garbage bags",
            "branches and wood",
            "yard waste",
            "trash pile",
            "cardboard boxes",
        ]
        
        # Fallback prompts if primary fails
        fallback_prompts = [
            "objects",
            "stuff",
            "items",
            "material",
            "clutter",
        ]
        
        try:
            import torch
            from scipy import ndimage
            
            # Ensure RGB
            if image.mode != "RGB":
                image = image.convert("RGB")
            
            h, w = image.height, image.width
            
            # Try primary prompts
            print(f"[GroundedSAM] Trying primary prompts (threshold={self.BOX_THRESHOLD})...")
            boxes, scores, labels = self._run_detection(image, primary_prompts)
            
            # If no detections, try fallback
            if len(boxes) == 0:
                print(f"[GroundedSAM] Primary failed, trying fallback prompts...")
                boxes, scores, labels = self._run_detection(image, fallback_prompts)
            
            print(f"[GroundedSAM] DINO detected {len(boxes)} objects: {labels[:5]}...")
            
            if len(boxes) == 0:
                print(f"[GroundedSAM] No detections with any prompts")
                return BulkMaskResult(
                    mask_np=np.zeros((h, w), dtype=bool),
                    area_ratio=0.0,
                    confidence=0.0,
                    error=None
                )
            
            # Convert boxes to SAM format
            boxes_list = boxes.cpu().tolist()
            max_score = float(scores.max().cpu())
            
            # Run SAM2 with detected boxes
            combined_mask = np.zeros((h, w), dtype=bool)
            
            for i, box in enumerate(boxes_list):
                try:
                    # Format box for SAM: [[box]] for batch=1, num_boxes=1
                    sam_inputs = self._sam_processor(
                        image,
                        input_boxes=[[[box]]],
                        return_tensors="pt"
                    ).to(self._device)
                    
                    with torch.no_grad():
                        sam_outputs = self._sam_model(**sam_inputs)
                    
                    # Get mask
                    masks = self._sam_processor.image_processor.post_process_masks(
                        sam_outputs.pred_masks.cpu(),
                        sam_inputs["original_sizes"].cpu(),
                        sam_inputs["reshaped_input_sizes"].cpu()
                    )[0]
                    
                    # Take best mask
                    if len(masks) > 0:
                        mask = masks[0].squeeze().numpy()
                        if mask.ndim == 3:
                            mask = mask[0]
                        combined_mask |= (mask > 0.5)
                except Exception as e:
                    print(f"[GroundedSAM] SAM error for box {i}: {e}")
                    continue
            
            # Apply morphological dilation (8px)
            DILATION_RADIUS = 8
            struct = ndimage.generate_binary_structure(2, 1)
            dilated_mask = ndimage.binary_dilation(
                combined_mask, 
                structure=struct, 
                iterations=DILATION_RADIUS
            )
            
            # Keep only largest connected component
            labeled_array, num_features = ndimage.label(dilated_mask)
            if num_features > 1:
                component_sizes = ndimage.sum(dilated_mask, labeled_array, range(1, num_features + 1))
                largest_label = np.argmax(component_sizes) + 1
                dilated_mask = (labeled_array == largest_label)
            
            # Calculate area ratio
            area_ratio = float(np.sum(dilated_mask)) / (h * w)
            
            print(f"[GroundedSAM] Combined mask area={area_ratio:.1%}, conf={max_score:.2f}")
            
            return BulkMaskResult(
                mask_np=dilated_mask,
                area_ratio=area_ratio,
                confidence=max_score,
                error=None
            )
            
        except Exception as e:
            print(f"[GroundedSAM] Error: {e}")
            import traceback
            traceback.print_exc()
            
            return BulkMaskResult(
                mask_np=None,
                area_ratio=0.0,
                confidence=0.0,
                error=str(e)
            )


# Global instance getter
_runner_instance = None

def get_grounded_sam_runner() -> GroundedSAMRunner:
    """Get or create the GroundedSAM runner instance."""
    global _runner_instance
    if _runner_instance is None:
        _runner_instance = GroundedSAMRunner()
    return _runner_instance
