"""
Stage 4: Calibration (The "Trust" Layer)
Goal: Ensure "1 meter" is actually 1 meter. Handle drift gracefully.
"""

from dataclasses import dataclass, field
from typing import Optional
import numpy as np

from .perception import InstanceMask, ANCHOR_ITEMS


@dataclass
class AnchorMeasurement:
    """A single anchor measurement for scale calibration."""
    anchor_id: str
    label: str
    expected_size_m: float  # Known real-world size
    measured_size_m: float  # Measured from depth/geometry
    scale_factor: float  # expected / measured
    confidence: float


@dataclass
class CalibrationResult:
    """Result of Stage 4 calibration."""
    frame_id: str
    scale_factor: float = 1.0  # Multiply all distances by this
    calibration_source: str = "unknown"  # "anchor_consensus", "exif", "fallback"
    confidence: str = "HIGH"  # "HIGH", "MEDIUM", "LOW"
    conservative_billing: bool = False
    review_required: bool = False
    anchor_measurements: list[AnchorMeasurement] = field(default_factory=list)
    conflict_detected: bool = False


# Conservative fallback focal length factor
FALLBACK_FOCAL_FACTOR = 0.75  # f ≈ 0.75 × image_width

# Anchor agreement tolerance
ANCHOR_AGREEMENT_TOLERANCE = 0.10  # 10% agreement threshold


def _measure_anchor_size(
    anchor: InstanceMask,
    depth_map: np.ndarray,
    f_px: float,
    image_width: int,
    image_height: int
) -> Optional[float]:
    """
    Measure the real-world size of an anchor item from depth.
    Returns size in meters or None if measurement failed.
    """
    x1, y1, x2, y2 = anchor.bbox
    
    # Clamp to image bounds
    x1 = max(0, min(x1, image_width - 1))
    x2 = max(0, min(x2, image_width - 1))
    y1 = max(0, min(y1, image_height - 1))
    y2 = max(0, min(y2, image_height - 1))
    
    if x2 <= x1 or y2 <= y1:
        return None
        
    # Get depth values in bbox region
    bbox_depth = depth_map[y1:y2, x1:x2]
    if bbox_depth.size == 0:
        return None
        
    # Use median depth to be robust to outliers
    median_depth = np.median(bbox_depth[bbox_depth > 0.1])
    if np.isnan(median_depth) or median_depth <= 0:
        return None
        
    # Calculate physical size from pixel size and depth
    # size_m = (pixel_size / f_px) * depth
    bbox_height_px = y2 - y1
    bbox_width_px = x2 - x1
    
    # For vertical anchors (doors, bins), use height
    # For horizontal anchors (tires), use width
    if "door" in anchor.label.lower():
        measured_size = (bbox_height_px / f_px) * median_depth
    elif "tire" in anchor.label.lower():
        # Tire diameter - use max of width/height
        measured_size = (max(bbox_height_px, bbox_width_px) / f_px) * median_depth
    else:
        # Default to height
        measured_size = (bbox_height_px / f_px) * median_depth
        
    return measured_size


def _compute_anchor_consensus(
    measurements: list[AnchorMeasurement]
) -> tuple[float, bool]:
    """
    Compute scale factor from multiple anchor measurements.
    Uses median and detects conflicts.
    
    Returns (scale_factor, conflict_detected).
    """
    if not measurements:
        return 1.0, False
        
    scale_factors = [m.scale_factor for m in measurements]
    
    if len(scale_factors) == 1:
        return scale_factors[0], False
        
    median_scale = np.median(scale_factors)
    
    # Check for conflicts (any anchor disagrees by more than tolerance)
    conflict = False
    for sf in scale_factors:
        deviation = abs(sf - median_scale) / median_scale
        if deviation > ANCHOR_AGREEMENT_TOLERANCE:
            conflict = True
            break
            
    # If conflict, reject outliers and recalculate
    if conflict:
        # Keep only scales within tolerance of median
        valid_scales = [
            sf for sf in scale_factors 
            if abs(sf - median_scale) / median_scale <= ANCHOR_AGREEMENT_TOLERANCE
        ]
        if valid_scales:
            median_scale = np.median(valid_scales)
            
    return float(median_scale), conflict


def run_calibration(
    frame_id: str,
    anchors: list[InstanceMask],
    depth_map: Optional[np.ndarray],
    f_px: float,
    image_width: int,
    image_height: int,
    exif_available: bool,
    intrinsics_available: bool
) -> CalibrationResult:
    """
    Stage 4 Entry Point: Calibrate scale using anchors or fallbacks.
    
    Args:
        frame_id: Unique frame identifier
        anchors: List of anchor items detected in Stage 2
        depth_map: Depth map from Stage 3
        f_px: Focal length in pixels (estimated or from EXIF)
        image_width, image_height: Image dimensions
        exif_available: Whether EXIF metadata was extracted
        intrinsics_available: Whether Depth Pro provided intrinsics
        
    Returns:
        CalibrationResult with scale factor and confidence
    """
    result = CalibrationResult(frame_id=frame_id)
    reason_codes = []
    
    # Track why decisions are made
    if not exif_available:
        reason_codes.append("missing_exif")
    if not intrinsics_available:
        reason_codes.append("depthpro_intrinsics_unavailable")
    if not anchors:
        reason_codes.append("no_anchors_detected")
    
    # Try anchor consensus first (most accurate)
    if anchors and depth_map is not None:
        for anchor in anchors:
            label_lower = anchor.label.lower()
            
            # Find matching anchor type
            expected_size = None
            for anchor_name, size in ANCHOR_ITEMS.items():
                if anchor_name in label_lower:
                    expected_size = size
                    break
                    
            if expected_size is None:
                continue
                
            # Measure actual size from depth
            measured_size = _measure_anchor_size(
                anchor, depth_map, f_px, image_width, image_height
            )
            
            if measured_size and measured_size > 0:
                scale_factor = expected_size / measured_size
                
                measurement = AnchorMeasurement(
                    anchor_id=anchor.instance_id,
                    label=anchor.label,
                    expected_size_m=expected_size,
                    measured_size_m=measured_size,
                    scale_factor=scale_factor,
                    confidence=anchor.confidence
                )
                result.anchor_measurements.append(measurement)
    
    # Compute consensus from anchors
    if result.anchor_measurements:
        scale, conflict = _compute_anchor_consensus(result.anchor_measurements)
        result.scale_factor = scale
        result.conflict_detected = conflict
        result.calibration_source = "anchor_consensus"
        result.confidence = "MEDIUM" if conflict else "HIGH"
        if conflict:
            reason_codes.append("anchor_conflict_detected")
        _log_calibration_trace(result, f_px, image_width, image_height, reason_codes)
        return result
        
    # Fallback to EXIF intrinsics
    if exif_available or intrinsics_available:
        result.scale_factor = 1.0  # Trust the camera intrinsics
        result.calibration_source = "exif" if exif_available else "intrinsics"
        result.confidence = "MEDIUM"
        if not exif_available:
            reason_codes.append("exif_unavailable_using_intrinsics")
        _log_calibration_trace(result, f_px, image_width, image_height, reason_codes)
        return result
        
    # Ultimate fallback: uncalibrated mode
    result.scale_factor = 1.0
    result.calibration_source = "fallback"
    result.confidence = "LOW"
    result.conservative_billing = True
    result.review_required = True
    reason_codes.append("uncalibrated_mode")
    
    _log_calibration_trace(result, f_px, image_width, image_height, reason_codes)
    return result


def _log_calibration_trace(
    result: CalibrationResult,
    f_px: float,
    image_width: int,
    image_height: int,
    reason_codes: list
):
    """
    v6.5.1: Calibration Trace logging.
    
    Explains WHY calibration chose exif vs intrinsics vs fallback.
    """
    # Compute cx, cy (assume principal point at center)
    cx = image_width / 2.0
    cy = image_height / 2.0
    
    print(f"\n[CALIB_TRACE] === Frame {result.frame_id[:8]} ===")
    print(f"[CALIB_TRACE] Decision:")
    print(f"  calib_mode_selected: {result.calibration_source}")
    print(f"  reason_codes: {reason_codes}")
    print(f"[CALIB_TRACE] Intrinsics Used:")
    print(f"  fx: {f_px:.1f}")
    print(f"  fy: {f_px:.1f}")
    print(f"  cx: {cx:.1f}")
    print(f"  cy: {cy:.1f}")
    print(f"  f_px: {f_px:.1f}")
    print(f"[CALIB_TRACE] Output:")
    print(f"  scale_factor: {result.scale_factor:.4f}")
    print(f"  confidence: {result.confidence}")
    if result.anchor_measurements:
        print(f"  anchors_used: {len(result.anchor_measurements)}")
        for m in result.anchor_measurements:
            print(f"    - {m.label}: expected={m.expected_size_m:.2f}m, measured={m.measured_size_m:.2f}m, scale={m.scale_factor:.3f}")
    print(f"[CALIB_TRACE] ==============================\n")

