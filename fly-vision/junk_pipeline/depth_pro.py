"""
Depth Pro Runner - Supports Local (Apple Original) and Replicate API modes.

Mode selection:
  - Set env var DEPTH_PRO_MODE=replicate to use Replicate API
  - Default: local Apple ml-depth-pro inference (requires GPU)

v11.0: Switched from HuggingFace port to Apple's original ml-depth-pro package.
  Key advantage: supports passing known focal length (f_px) to produce correctly
  scaled metric depth when EXIF intrinsics are available.
  
Returns proper intrinsics (fx/fy/cx/cy) alongside metric depth.
"""

import os
import io
import math
import base64
import numpy as np
from PIL import Image
from typing import Optional, Union


# Mode: 'local' or 'replicate'
DEPTH_PRO_MODE = os.environ.get("DEPTH_PRO_MODE", "local").lower()

# Checkpoint path for Apple's original model
# Modal: baked into container image at build time
# Local dev: override via env var or download to default path
DEPTH_PRO_CHECKPOINT = os.environ.get(
    "DEPTH_PRO_CHECKPOINT",
    "/opt/depth_pro/depth_pro.pt"
)


class DepthProRunner:
    """
    Runs Apple DepthPro for metric monocular depth estimation.
    
    Supports two backends:
      - local: Apple's original ml-depth-pro (requires GPU)
      - replicate: Replicate API (no GPU needed)
    
    v11.0: Local mode now uses Apple's original package which supports
    passing known focal length (f_px) for EXIF-corrected metric depth.
    
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
        """Initialize Apple's original DepthPro model."""
        import torch
        import depth_pro
        
        # Prefer: CUDA > MPS (Apple Silicon) > CPU
        if torch.cuda.is_available():
            device = "cuda"
        elif torch.backends.mps.is_available():
            device = "mps"
        else:
            device = "cpu"
        
        self.device = torch.device(device)
        print(f"[DepthPro] Loading APPLE model on {self.device}...")
        
        # Configure checkpoint path
        config = depth_pro.depth_pro.DEFAULT_MONODEPTH_CONFIG_DICT
        config.checkpoint_uri = DEPTH_PRO_CHECKPOINT
        
        self.model, self.transform = depth_pro.create_model_and_transforms(
            config=config, device=self.device
        )
        self.model.eval()
        
        print(f"[DepthPro] Apple model loaded successfully on {self.device}")
    
    def _init_replicate(self):
        """Initialize Replicate API client."""
        print("[DepthPro] Using REPLICATE API mode")
        self.device = None
        self.model = None
        self.transform = None
    
    @classmethod
    def get_instance(cls) -> "DepthProRunner":
        """Singleton pattern - load/init once, reuse for all frames."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def infer(self, image: Image.Image, f_px: Optional[float] = None) -> dict:
        """
        Run depth estimation on image.
        
        Args:
            image: PIL Image (RGB)
            f_px: Optional known focal length in pixels (from EXIF/CalibrationBundle).
                  When provided, DepthPro skips its own FOV estimation and uses this
                  value to scale canonical inverse depth → metric depth. This produces
                  correctly scaled depth when camera intrinsics are known.
                  Must be in the same pixel space as the input image width.
        
        Returns:
            dict with:
              - depth_m: (H, W) float32 depth in meters
              - intrinsics: dict with fx, fy, cx, cy in pixels
              - field_of_view: FOV in degrees
              - size: (H, W) tuple
        """
        if self.mode == "local":
            return self._infer_local(image, f_px=f_px)
        else:
            if f_px is not None:
                print("[DepthPro] WARNING: Replicate mode does not support f_px override, ignoring")
            return self._infer_replicate(image)
    
    def _infer_local(self, image: Image.Image, f_px: Optional[float] = None) -> dict:
        """
        Apple DepthPro local inference.
        
        v11.0: Uses Apple's original API which supports passing known f_px.
        When f_px is provided, the model's internal FOV estimation is bypassed
        and the known focal length is used to scale depth → metric.
        """
        import torch
        
        if image.mode != "RGB":
            image = image.convert("RGB")
        
        # Apply Apple's preprocessing transform (PIL → normalized tensor)
        image_tensor = self.transform(image)
        
        # Run inference with optional known focal length
        # Apple's infer() calls f_px.squeeze(), so it must be a tensor, not a float
        f_px_input = torch.tensor(f_px, dtype=torch.float32) if f_px is not None else None
        with torch.no_grad():
            prediction = self.model.infer(image_tensor, f_px=f_px_input)
        
        depth = prediction["depth"].cpu().numpy().astype("float32")
        focal_px = float(prediction["focallength_px"])
        
        H, W = depth.shape
        cx = (W - 1) / 2.0
        cy = (H - 1) / 2.0
        
        # Compute FOV from focal length
        fov = 2 * math.degrees(math.atan(W / (2 * focal_px)))
        
        mode_str = "EXIF-provided" if f_px is not None else "model-estimated"
        print(f"[DepthPro] Output: {W}x{H}, f_px={focal_px:.1f} ({mode_str}), FOV={fov:.1f}°")
        
        return {
            "depth_m": depth,
            "intrinsics": {"fx": focal_px, "fy": focal_px, "cx": cx, "cy": cy},
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
