
"""
Local SegFormer Runner for Apple Silicon (MPS).

Provides deterministic, low-latency floor/ground segmentation using 
locally-loaded SegFormer models instead of HuggingFace API calls.
"""

import torch
import numpy as np
from PIL import Image
from typing import Optional, Tuple, Dict
from dataclasses import dataclass
import time


@dataclass
class SegFormerResult:
    """Result from local SegFormer inference."""
    ground_mask: Optional[np.ndarray] = None  # (H, W) bool array
    ground_area_pct: float = 0.0
    labels_found: list = None
    model_used: str = "none"
    inference_time_ms: float = 0.0
    error: Optional[str] = None
    
    def __post_init__(self):
        if self.labels_found is None:
            self.labels_found = []


# Cityscapes class IDs for ground-like surfaces
# Reference: https://github.com/mcordts/cityscapesScripts/blob/master/cityscapesscripts/helpers/labels.py
CITYSCAPES_GROUND_CLASSES = {
    0: "road",
    1: "sidewalk", 
    9: "terrain",  # grass, soil, sand
}

# ADE20K floor-like classes (id -> label)
# Reference: https://huggingface.co/nvidia/segformer-b0-finetuned-ade-512-512
ADE20K_GROUND_CLASSES = {
    3: "floor",
    6: "road",
    11: "sidewalk",
    13: "earth",
    29: "rug",
    52: "path",
    # Note: IDs may vary, we'll also do label matching
}


class SegFormerRunner:
    """
    Local SegFormer inference on MPS/CUDA/CPU.
    Singleton pattern - model loaded once and reused.
    """
    
    _instance = None
    _cityscapes_model = None
    _cityscapes_processor = None
    _ade_model = None
    _ade_processor = None
    _device = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._device is None:
            # Determine device
            if torch.backends.mps.is_available():
                self._device = torch.device("mps")
            elif torch.cuda.is_available():
                self._device = torch.device("cuda")
            else:
                self._device = torch.device("cpu")
            print(f"[SegFormerRunner] Device: {self._device}")
    
    def _load_cityscapes_model(self):
        """Load Cityscapes SegFormer model (lazy loading)."""
        if self._cityscapes_model is not None:
            return
        
        from transformers import AutoImageProcessor, AutoModelForSemanticSegmentation
        
        # Use B1 for better accuracy (B0 is fastest but misses more ground)
        model_id = "nvidia/segformer-b1-finetuned-cityscapes-1024-1024"
        
        print(f"[SegFormerRunner] Loading Cityscapes model: {model_id}")
        start = time.time()
        
        self._cityscapes_processor = AutoImageProcessor.from_pretrained(model_id)
        self._cityscapes_model = AutoModelForSemanticSegmentation.from_pretrained(model_id)
        self._cityscapes_model.to(self._device)
        self._cityscapes_model.eval()
        
        elapsed = (time.time() - start) * 1000
        print(f"[SegFormerRunner] Cityscapes model loaded in {elapsed:.0f}ms")
    
    def _load_ade_model(self):
        """Load ADE20K SegFormer model (lazy loading)."""
        if self._ade_model is not None:
            return
        
        from transformers import AutoImageProcessor, AutoModelForSemanticSegmentation
        
        model_id = "nvidia/segformer-b0-finetuned-ade-512-512"
        
        print(f"[SegFormerRunner] Loading ADE model: {model_id}")
        start = time.time()
        
        self._ade_processor = AutoImageProcessor.from_pretrained(model_id)
        self._ade_model = AutoModelForSemanticSegmentation.from_pretrained(model_id)
        self._ade_model.to(self._device)
        self._ade_model.eval()
        
        elapsed = (time.time() - start) * 1000
        print(f"[SegFormerRunner] ADE model loaded in {elapsed:.0f}ms")
    
    def run_cityscapes(self, image: Image.Image, timeout_ms: float = 5000) -> SegFormerResult:
        """
        Run Cityscapes SegFormer on image and return ground mask.
        
        Args:
            image: PIL Image (RGB)
            timeout_ms: Max inference time before treating as timeout
            
        Returns:
            SegFormerResult with ground_mask and stats
        """
        result = SegFormerResult(model_used="cityscapes_local")
        
        try:
            self._load_cityscapes_model()
            
            # Ensure RGB
            if image.mode != "RGB":
                image = image.convert("RGB")
            
            h, w = image.height, image.width
            
            start = time.time()
            
            # Preprocess
            inputs = self._cityscapes_processor(images=image, return_tensors="pt")
            inputs = {k: v.to(self._device) for k, v in inputs.items()}
            
            # Inference
            with torch.no_grad():
                outputs = self._cityscapes_model(**inputs)
            
            # Get predicted class per pixel
            logits = outputs.logits  # (1, num_classes, H', W')
            
            # Upsample to original size
            upsampled = torch.nn.functional.interpolate(
                logits, size=(h, w), mode="bilinear", align_corners=False
            )
            
            # Get class predictions
            pred_classes = upsampled.argmax(dim=1).squeeze(0).cpu().numpy()  # (H, W)
            
            elapsed_ms = (time.time() - start) * 1000
            result.inference_time_ms = elapsed_ms
            
            if elapsed_ms > timeout_ms:
                result.error = f"Timeout: {elapsed_ms:.0f}ms > {timeout_ms}ms"
                return result
            
            # Build ground mask from Cityscapes ground classes
            ground_mask = np.zeros((h, w), dtype=bool)
            labels_found = []
            
            for class_id, label in CITYSCAPES_GROUND_CLASSES.items():
                class_mask = pred_classes == class_id
                if np.any(class_mask):
                    ground_mask |= class_mask
                    labels_found.append(label)
            
            result.ground_mask = ground_mask
            result.ground_area_pct = 100.0 * np.mean(ground_mask)
            result.labels_found = labels_found
            
            print(f"[SegFormerRunner] Cityscapes: {result.ground_area_pct:.1f}% ground, labels={labels_found}, {elapsed_ms:.0f}ms")
            
        except Exception as e:
            result.error = str(e)
            print(f"[SegFormerRunner] Cityscapes error: {e}")
        
        return result
    
    def run_ade(self, image: Image.Image, timeout_ms: float = 5000) -> SegFormerResult:
        """
        Run ADE20K SegFormer on image and return ground mask.
        
        Args:
            image: PIL Image (RGB)
            timeout_ms: Max inference time before treating as timeout
            
        Returns:
            SegFormerResult with ground_mask and stats
        """
        result = SegFormerResult(model_used="ade_local")
        
        try:
            self._load_ade_model()
            
            if image.mode != "RGB":
                image = image.convert("RGB")
            
            h, w = image.height, image.width
            
            start = time.time()
            
            # Preprocess
            inputs = self._ade_processor(images=image, return_tensors="pt")
            inputs = {k: v.to(self._device) for k, v in inputs.items()}
            
            # Inference
            with torch.no_grad():
                outputs = self._ade_model(**inputs)
            
            logits = outputs.logits
            
            # Upsample to original size
            upsampled = torch.nn.functional.interpolate(
                logits, size=(h, w), mode="bilinear", align_corners=False
            )
            
            pred_classes = upsampled.argmax(dim=1).squeeze(0).cpu().numpy()
            
            elapsed_ms = (time.time() - start) * 1000
            result.inference_time_ms = elapsed_ms
            
            if elapsed_ms > timeout_ms:
                result.error = f"Timeout: {elapsed_ms:.0f}ms > {timeout_ms}ms"
                return result
            
            # Build ground mask - also check by label name from model config
            ground_mask = np.zeros((h, w), dtype=bool)
            labels_found = []
            
            # Get label mapping from model
            id2label = self._ade_model.config.id2label
            
            floor_keywords = {"floor", "road", "path", "sidewalk", "ground", "earth", "rug", "carpet"}
            
            for class_id, label in id2label.items():
                label_lower = label.lower()
                if any(kw in label_lower for kw in floor_keywords):
                    class_mask = pred_classes == class_id
                    if np.any(class_mask):
                        ground_mask |= class_mask
                        labels_found.append(label_lower)
            
            result.ground_mask = ground_mask
            result.ground_area_pct = 100.0 * np.mean(ground_mask)
            result.labels_found = labels_found
            
            print(f"[SegFormerRunner] ADE: {result.ground_area_pct:.1f}% ground, labels={labels_found}, {elapsed_ms:.0f}ms")
            
        except Exception as e:
            result.error = str(e)
            print(f"[SegFormerRunner] ADE error: {e}")
        
        return result


# Module-level singleton instance
_runner: Optional[SegFormerRunner] = None


def get_runner() -> SegFormerRunner:
    """Get or create the singleton SegFormer runner."""
    global _runner
    if _runner is None:
        _runner = SegFormerRunner()
    return _runner


def run_local_cityscapes(image: Image.Image) -> SegFormerResult:
    """Convenience function to run Cityscapes inference."""
    return get_runner().run_cityscapes(image)


def run_local_ade(image: Image.Image) -> SegFormerResult:
    """Convenience function to run ADE inference."""
    return get_runner().run_ade(image)
