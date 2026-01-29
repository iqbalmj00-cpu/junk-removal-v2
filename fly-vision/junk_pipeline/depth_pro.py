"""
Depth Pro Runner - Supports Local (HuggingFace) and Replicate API modes.

Mode selection:
  - Set env var DEPTH_PRO_MODE=replicate to use Replicate API
  - Default: local HuggingFace inference (requires GPU)
  
Returns proper intrinsics (fx/fy/cx/cy) alongside metric depth.
"""

import os
import io
import base64
import numpy as np
from PIL import Image
from typing import Optional


# Mode: 'local' or 'replicate'
DEPTH_PRO_MODE = os.environ.get("DEPTH_PRO_MODE", "local").lower()


class DepthProRunner:
    """
    Runs Apple DepthPro for metric monocular depth estimation.
    
    Supports two backends:
      - local: HuggingFace Transformers (requires GPU)
      - replicate: Replicate API (no GPU needed)
    
    Returns:
      - depth_m: (H, W) float32 depth map in meters
      - intrinsics: fx/fy/cx/cy in pixel units
      - field_of_view: FOV in degrees
    """
    
    _instance: Optional["DepthProRunner"] = None
    
    def __init__(self, mode: str = DEPTH_PRO_MODE):
        self.mode = mode
        
        if mode == "local":
            self._init_local()
        elif mode == "replicate":
            self._init_replicate()
        else:
            raise ValueError(f"Unknown DEPTH_PRO_MODE: {mode}. Use 'local' or 'replicate'.")
    
    def _init_local(self):
        """Initialize local HuggingFace model."""
        import torch
        from transformers import DepthProImageProcessorFast, DepthProForDepthEstimation
        
        # Prefer: CUDA > MPS (Apple Silicon) > CPU
        if torch.cuda.is_available():
            device = "cuda"
        elif torch.backends.mps.is_available():
            device = "mps"
        else:
            device = "cpu"
        
        self.device = torch.device(device)
        print(f"[DepthPro] Loading LOCAL model on {self.device}...")
        
        model_id = "apple/DepthPro-hf"
        self.image_processor = DepthProImageProcessorFast.from_pretrained(model_id)
        self.model = DepthProForDepthEstimation.from_pretrained(model_id).to(self.device)
        self.model.eval()
        
        print(f"[DepthPro] Model loaded successfully on {self.device}")
    
    def _init_replicate(self):
        """Initialize Replicate API client."""
        print("[DepthPro] Using REPLICATE API mode")
        self.device = None
        self.model = None
        self.image_processor = None
    
    @classmethod
    def get_instance(cls) -> "DepthProRunner":
        """Singleton pattern - load/init once, reuse for all frames."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def infer(self, image: Image.Image) -> dict:
        """
        Run depth estimation on image.
        
        Args:
            image: PIL Image (RGB)
        
        Returns:
            dict with:
              - depth_m: (H, W) float32 depth in meters
              - intrinsics: dict with fx, fy, cx, cy in pixels
              - field_of_view: FOV in degrees
              - size: (H, W) tuple
        """
        if self.mode == "local":
            return self._infer_local(image)
        else:
            return self._infer_replicate(image)
    
    def _infer_local(self, image: Image.Image) -> dict:
        """Local HuggingFace inference."""
        import torch
        
        if image.mode != "RGB":
            image = image.convert("RGB")
        
        with torch.no_grad():
            inputs = self.image_processor(images=image, return_tensors="pt").to(self.device)
            outputs = self.model(**inputs)
            
            # Post-process to get depth at SAME resolution as input image
            post = self.image_processor.post_process_depth_estimation(
                outputs,
                target_sizes=[(image.height, image.width)],
            )[0]
        
        depth_t = post["predicted_depth"]
        depth_m = depth_t.detach().float().cpu().numpy().astype("float32")
        
        f_px = float(post["focal_length"])
        H, W = depth_m.shape
        cx = (W - 1) / 2.0
        cy = (H - 1) / 2.0
        
        fov = post.get("field_of_view", None)
        if fov is not None:
            fov = float(fov)
        
        print(f"[DepthPro] Output: {W}x{H}, f_px={f_px:.1f}, FOV={fov}°")
        
        return {
            "depth_m": depth_m,
            "intrinsics": {"fx": f_px, "fy": f_px, "cx": cx, "cy": cy},
            "field_of_view": fov,
            "size": (H, W),
        }
    
    def _infer_replicate(self, image: Image.Image) -> dict:
        """Replicate API inference."""
        import replicate
        import requests
        
        if image.mode != "RGB":
            image = image.convert("RGB")
        
        # Convert image to base64 data URI for Replicate
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        buffer.seek(0)
        b64 = base64.b64encode(buffer.read()).decode("utf-8")
        data_uri = f"data:image/png;base64,{b64}"
        
        print(f"[DepthPro] Calling Replicate API ({image.width}x{image.height})...")
        
        # Run DepthPro on Replicate
        # Model: garg-aayush/ml-depth-pro
        output = replicate.run(
            "garg-aayush/ml-depth-pro:93d5c6df46801fe20a tried128c4d0e3f5e8a92bed46fec7a21e7e15b2e99c58",
            input={"image": data_uri}
        )
        
        # The output is a URL to the depth map (typically 16-bit PNG or NPZ)
        depth_url = output
        
        # Download the depth map
        response = requests.get(depth_url, timeout=60)
        response.raise_for_status()
        
        # Parse depth map (Replicate returns 16-bit PNG or similar)
        depth_img = Image.open(io.BytesIO(response.content))
        depth_raw = np.array(depth_img, dtype=np.float32)
        
        # Convert to meters (Replicate model may return normalized or scaled values)
        # The ml-depth-pro model returns metric depth directly in the image values
        # Typically stored as 16-bit depth where value / 1000 = meters
        if depth_raw.max() > 100:  # Likely 16-bit scaled
            depth_m = depth_raw / 1000.0  # Convert mm to meters
        else:
            depth_m = depth_raw  # Already in meters
        
        H, W = depth_m.shape
        
        # Estimate focal length from image size (DepthPro assumes ~55° FOV)
        # FOV ≈ 55° → f_px = W / (2 * tan(27.5°)) ≈ W * 0.96
        fov = 55.0
        f_px = W / (2 * np.tan(np.radians(fov / 2)))
        cx = (W - 1) / 2.0
        cy = (H - 1) / 2.0
        
        print(f"[DepthPro] Replicate output: {W}x{H}, f_px={f_px:.1f}, FOV~{fov}°")
        
        return {
            "depth_m": depth_m,
            "intrinsics": {"fx": f_px, "fy": f_px, "cx": cx, "cy": cy},
            "field_of_view": fov,
            "size": (H, W),
        }
    
    @staticmethod
    def save_depth_debug_png(depth_m: np.ndarray, out_path: str) -> None:
        """
        Visualization ONLY. Normalizes to 8-bit for a PNG.
        Do NOT feed this into volumetrics.
        """
        d = depth_m.copy()
        d = np.nan_to_num(d, nan=0.0, posinf=0.0, neginf=0.0)
        
        valid = d[d > 0]
        if valid.size == 0:
            img = Image.fromarray(np.zeros_like(d, dtype=np.uint8))
            img.save(out_path)
            return
        
        lo, hi = np.percentile(valid, [2, 98])
        d = np.clip((d - lo) / (hi - lo + 1e-6), 0.0, 1.0)
        img = Image.fromarray((d * 255).astype(np.uint8))
        img.save(out_path)
