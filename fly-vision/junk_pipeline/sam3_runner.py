"""
SAM3 Runner: Meta Segment Anything Model 3 for Bulk Segmentation
Uses HuggingFace Transformers API (no GitHub install needed)
"""

from dataclasses import dataclass
from typing import Optional, List
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
    Uses HuggingFace Transformers API.
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
        """Load SAM3 model from HuggingFace."""
        try:
            import torch
            from transformers import Sam3Processor, Sam3Model
            
            # Determine device
            if torch.cuda.is_available():
                self._device = "cuda"
            elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                self._device = "mps"
            else:
                self._device = "cpu"
            
            print(f"[SAM3] Loading facebook/sam3 on {self._device}...")
            
            self._processor = Sam3Processor.from_pretrained("facebook/sam3")
            self._model = Sam3Model.from_pretrained("facebook/sam3").to(self._device)
            
            print(f"[SAM3] Model loaded successfully")
            
        except ImportError as e:
            print(f"[SAM3] Import error: {e}")
            self._model = None
            
        except Exception as e:
            print(f"[SAM3] Failed to load model: {e}")
            import traceback
            traceback.print_exc()
            self._model = None
    
    def _run_single_prompt(self, image: Image.Image, prompt: str, h: int, w: int):
        """Run SAM3 with a single prompt, return masks and scores."""
        import torch
        
        inputs = self._processor(
            images=image, 
            text=prompt, 
            return_tensors="pt"
        ).to(self._device)
        
        with torch.no_grad():
            outputs = self._model(**inputs)
        
        # Use lower thresholds for better recall
        results = self._processor.post_process_instance_segmentation(
            outputs,
            threshold=0.3,  # Lower threshold
            mask_threshold=0.3,  # Lower mask threshold
            target_sizes=inputs.get("original_sizes").tolist()
        )[0]
        
        return results.get("masks", []), results.get("scores", [])
    
    def segment(
        self, 
        image: Image.Image, 
        prompts: List[str] = None
    ) -> BulkMaskResult:
        """
        Run SAM3 text-prompted segmentation with multiple prompts.
        
        Args:
            image: PIL Image to process
            prompts: List of text prompts to try (uses defaults if None)
            
        Returns:
            BulkMaskResult with combined mask from all prompts
        """
        if self._model is None or self._processor is None:
            return BulkMaskResult(
                mask_np=None,
                area_ratio=0.0,
                confidence=0.0,
                error="SAM3 model not loaded"
            )
        
        # Default prompts to try - broad categories that work for junk/debris
        if prompts is None:
            prompts = [
                "pile",
                "debris",
                "branches",
                "wood",
                "leaves",
                "brush",
                "yard waste",
                "trash",
                "junk",
            ]
        
        try:
            import torch
            from scipy import ndimage
            
            # Ensure RGB
            if image.mode != "RGB":
                image = image.convert("RGB")
            
            h, w = image.height, image.width
            
            # Combine masks from all prompts
            combined_mask = np.zeros((h, w), dtype=bool)
            max_score = 0.0
            total_masks_found = 0
            
            for prompt in prompts:
                try:
                    masks, scores = self._run_single_prompt(image, prompt, h, w)
                    
                    if len(masks) > 0:
                        print(f"[SAM3] '{prompt}' found {len(masks)} masks")
                        total_masks_found += len(masks)
                        
                        for i, mask in enumerate(masks):
                            if isinstance(mask, torch.Tensor):
                                mask = mask.cpu().numpy()
                            
                            # Ensure 2D
                            if mask.ndim > 2:
                                mask = mask.squeeze()
                            
                            # Resize if needed
                            if mask.shape != (h, w):
                                from PIL import Image as PILImage
                                mask_pil = PILImage.fromarray((mask * 255).astype(np.uint8))
                                mask_pil = mask_pil.resize((w, h), PILImage.NEAREST)
                                mask = np.array(mask_pil) > 127
                            
                            combined_mask |= mask.astype(bool)
                            
                            if i < len(scores):
                                score = scores[i]
                                if isinstance(score, torch.Tensor):
                                    score = float(score.cpu())
                                max_score = max(max_score, score)
                                
                except Exception as e:
                    print(f"[SAM3] Error with prompt '{prompt}': {e}")
                    continue
            
            if total_masks_found == 0:
                print(f"[SAM3] No masks found with any prompt")
                return BulkMaskResult(
                    mask_np=np.zeros((h, w), dtype=bool),
                    area_ratio=0.0,
                    confidence=0.0,
                    error=None
                )
            
            # Apply morphological dilation for recall bias (8px radius)
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
            
            print(f"[SAM3] Combined {total_masks_found} regions, area={area_ratio:.1%}")
            
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
