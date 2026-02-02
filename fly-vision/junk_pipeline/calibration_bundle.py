"""
Calibration Bundle - Production-grade camera intrinsics for web uploads.

Core invariant: Intrinsics live in the same pixel space as DepthPro input.

Dimension chain:
    decoded_raw → ROTATE PIXELS → decoded_oriented (intrinsics base) → model_input
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CalibrationBundle:
    """Complete calibration state for a single frame."""
    
    # =========================================================================
    # DIMENSION CHAIN
    # =========================================================================
    decoded_raw_width: int = 0
    decoded_raw_height: int = 0
    decoded_oriented_width: int = 0   # After physical rotation
    decoded_oriented_height: int = 0
    model_input_width: int = 0        # What DepthPro sees
    model_input_height: int = 0
    orientation: int = 1              # EXIF orientation tag
    
    # =========================================================================
    # BASE INTRINSICS (at decoded_oriented resolution)
    # =========================================================================
    fx_base: float = 0.0
    fy_base: float = 0.0
    cx_base: float = 0.0
    cy_base: float = 0.0
    
    # =========================================================================
    # MODEL INTRINSICS (at model_input resolution - what DepthPro uses)
    # =========================================================================
    fx: float = 0.0
    fy: float = 0.0
    cx: float = 0.0
    cy: float = 0.0
    
    # =========================================================================
    # CAMERA + LENS IDENTITY
    # =========================================================================
    make: Optional[str] = None
    model: Optional[str] = None
    lens_model: Optional[str] = None
    
    # Lens identification
    lens_id: str = "main"             # main | ultra | tele | unknown
    lens_id_reason: str = ""          # Human-readable explanation
    lens_id_source: str = "fallback"  # lens_model | focal_35mm | focal_mm_device | fallback
    
    # =========================================================================
    # OPTICS
    # =========================================================================
    focal_length_mm: Optional[float] = None
    focal_length_35mm: Optional[float] = None
    digital_zoom_ratio: float = 1.0
    
    # =========================================================================
    # CALIBRATION QUALITY
    # =========================================================================
    anchoring_mult: float = 1.0       # Soft penalty for zoom unknown
    calib_source: str = "fallback"    # exif | device_db | fallback
    calib_confidence: str = "LOW"     # HIGH | MED | LOW
    calib_warnings: list[str] = field(default_factory=list)
    
    # Extraction provenance
    exif_from_server: bool = False    # Server ExifTool succeeded
    exif_from_frontend: bool = False  # Used frontend fallback
    
    def log_chain(self, frame_id: str = "") -> None:
        """Print CALIB_CHAIN diagnostic log."""
        print(f"[CALIB_CHAIN] {frame_id[:8] if frame_id else 'frame'}")
        print(f"  raw: {self.decoded_raw_width}x{self.decoded_raw_height}")
        print(f"  oriented: {self.decoded_oriented_width}x{self.decoded_oriented_height}")
        print(f"  model: {self.model_input_width}x{self.model_input_height}")
        print(f"  fx_base: {self.fx_base:.1f} @ oriented")
        print(f"  fx: {self.fx:.1f} @ model (DepthPro input)")
        print(f"  lens: {self.lens_id} ({self.lens_id_reason}) src={self.lens_id_source}")
        print(f"  anchoring: {self.anchoring_mult:.2f}x")
        print(f"  conf: {self.calib_confidence}, src: {self.calib_source}")
        if self.calib_warnings:
            print(f"  warnings: {self.calib_warnings}")


def scale_intrinsics(
    fx_base: float, fy_base: float,
    cx_base: float, cy_base: float,
    oriented_width: int, oriented_height: int,
    model_width: int, model_height: int
) -> tuple[float, float, float, float]:
    """Scale intrinsics from oriented resolution to model resolution."""
    scale_x = model_width / oriented_width if oriented_width > 0 else 1.0
    scale_y = model_height / oriented_height if oriented_height > 0 else 1.0
    
    return (
        fx_base * scale_x,
        fy_base * scale_y,
        cx_base * scale_x,
        cy_base * scale_y
    )
