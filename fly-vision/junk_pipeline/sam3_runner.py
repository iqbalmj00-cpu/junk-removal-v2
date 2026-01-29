"""
SAM3 Runner: Meta Segment Anything Model 3 for Bulk Segmentation
Replaces Replicate Lang-SAM for Lane B
"""

from dataclasses import dataclass
from typing import Optional
import numpy as np
from PIL import Image


@dataclass
class BulkMaskResult:
    """Result from SAM3 bulk segmentation."""
    mask_np: Optional[np.ndarray]  # (H, W) boolean mask
    area_ratio: float
    confidence: float
    error: Optional[str] = None


class SAM3Runner:
    """
    Singleton SAM3 runner for text-prompted segmentation.
    
    Uses Meta's SAM3 for open-vocabulary segmentation.
    """
    _instance = None
    _model = None
    _processor = None
    _device = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._model is None:
            self._load_model()
    
    def _load_model(self):
        """Load SAM3 model (downloads on first run)."""
        try:
            import torch
            
            # Determine device
            if torch.cuda.is_available():
                self._device = "cuda"
            elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                self._device = "mps"
            else:
                self._device = "cpu"
            
            print(f"[SAM3] Loading model on {self._device}...")
            
            # Import SAM3 components
            from sam3.model_builder import build_sam3_image_model
            from sam3.model.sam3_image_processor import Sam3Processor
            
            self._model = build_sam3_image_model()
            self._model.to(self._device)
            self._processor = Sam3Processor(self._model)
            
            print(f"[SAM3] Model loaded successfully")
            
        except ImportError as e:
            print(f"[SAM3] SAM3 not installed: {e}")
            print("[SAM3] Install with: pip install sam3")
            self._model = None
            
        except Exception as e:
            print(f"[SAM3] Failed to load model: {e}")
            self._model = None
    
    def segment(
        self, 
        image: Image.Image, 
        prompt: str = "pile of junk, debris, garbage bags, cardboard boxes"
    ) -> BulkMaskResult:
        """
        Run SAM3 text-prompted segmentation.
        
        Args:
            image: PIL Image to process
            prompt: Text prompt describing what to segment
            
        Returns:
            BulkMaskResult with combined mask
        """
        if self._model is None or self._processor is None:
            return BulkMaskResult(
                mask_np=None,
                area_ratio=0.0,
                confidence=0.0,
                error="SAM3 model not loaded"
            )
        
        try:
            import torch
            from scipy import ndimage
            
            # Ensure RGB
            if image.mode != "RGB":
                image = image.convert("RGB")
            
            h, w = image.height, image.width
            
            # Run SAM3 with text prompt
            inference_state = self._processor.set_image(image)
            output = self._processor.set_text_prompt(
                state=inference_state,
                prompt=prompt
            )
            
            # Extract masks
            masks = output.get("masks", [])
            scores = output.get("scores", [])
            
            if len(masks) == 0:
                return BulkMaskResult(
                    mask_np=np.zeros((h, w), dtype=bool),
                    area_ratio=0.0,
                    confidence=0.0,
                    error=None
                )
            
            # Combine masks with score > 0.5
            combined_mask = np.zeros((h, w), dtype=bool)
            max_score = 0.0
            
            for i, (mask, score) in enumerate(zip(masks, scores)):
                if isinstance(mask, torch.Tensor):
                    mask = mask.cpu().numpy()
                if isinstance(score, torch.Tensor):
                    score = float(score.cpu())
                
                # Ensure mask is 2D
                if mask.ndim > 2:
                    mask = mask.squeeze()
                
                # Resize if needed
                if mask.shape != (h, w):
                    from PIL import Image as PILImage
                    mask_pil = PILImage.fromarray((mask * 255).astype(np.uint8))
                    mask_pil = mask_pil.resize((w, h), PILImage.NEAREST)
                    mask = np.array(mask_pil) > 127
                
                if score > 0.5:
                    combined_mask |= mask.astype(bool)
                    max_score = max(max_score, score)
            
            # Apply morphological dilation for recall bias (12px radius)
            DILATION_RADIUS = 12
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
            
            print(f"[SAM3] Segmented {len(masks)} regions, combined area={area_ratio:.1%}")
            
            return BulkMaskResult(
                mask_np=dilated_mask,
                area_ratio=area_ratio,
                confidence=max_score,
                error=None
            )
            
        except Exception as e:
            print(f"[SAM3] Segmentation error: {e}")
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

def get_sam3_runner() -> SAM3Runner:
    """Get or create the SAM3 runner instance."""
    global _runner_instance
    if _runner_instance is None:
        _runner_instance = SAM3Runner()
    return _runner_instance
