"""
Stage 7: Deployment Output (The Decision Gate)
Goal: Operational clarity with structured JSON output.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, Any
import json

from .ingestion import IngestionResult
from .calibration import CalibrationResult  
from .fusion import FusionResult
from .volumetrics import DiscreteItem


# Conservative billing rounding
CONSERVATIVE_ROUND_TIER = 0.5  # Round UP to next 0.5 yd³


@dataclass
class LineItem:
    """A billable line item in the quote."""
    name: str
    qty: int
    vol_cy: float
    source: str  # "Discrete_Database", "Measured_Terrain"
    surcharges: list[str] = field(default_factory=list)
    note: Optional[str] = None


@dataclass
class DiagnosticsPayload:
    """Diagnostic information for debugging."""
    valid_frames: int
    rejected_frames: list[str]
    floor_quality: str
    depth_confidence_avg: float
    calibration_source: str
    fusion_method: str


@dataclass
class FlagsPayload:
    """Operational flags for review/routing."""
    review_required: bool
    calibration_source: str
    viewpoint_diversity: str
    conservative_billing: bool


@dataclass 
class OutputPayload:
    """Final JSON output structure."""
    job_id: str
    final_volume_cy: float
    uncertainty_range: list[float]  # [min, max]
    confidence_score: str  # "HIGH", "MEDIUM", "LOW"
    flags: FlagsPayload
    diagnostics: DiagnosticsPayload
    line_items: list[LineItem]


def _round_conservative(volume: float) -> float:
    """Round UP to next 0.5 yd³ tier for conservative billing."""
    import math
    return math.ceil(volume / CONSERVATIVE_ROUND_TIER) * CONSERVATIVE_ROUND_TIER


def _determine_overall_confidence(
    calibration_conf: str,
    floor_quality: str,
    viewpoint_diversity: str,
    valid_frame_count: int
) -> str:
    """Determine overall confidence score."""
    score = 3  # Start at HIGH
    
    if calibration_conf == "LOW":
        score -= 2
    elif calibration_conf == "MEDIUM":
        score -= 1
        
    if floor_quality == "failed":
        score -= 2
    elif floor_quality == "noisy":
        score -= 1
        
    if viewpoint_diversity == "low":
        score -= 1
        
    if valid_frame_count < 2:
        score -= 1
        
    if score >= 3:
        return "HIGH"
    elif score >= 1:
        return "MEDIUM"
    else:
        return "LOW"


def _build_line_items(
    fusion_result: FusionResult,
    bulk_volume: float
) -> list[LineItem]:
    """Build line items from fused results."""
    items = []
    
    # Add discrete items
    discrete_total = 0.0
    for di in fusion_result.fused_discrete_items:
        if di.volume_cy > 0:
            item = LineItem(
                name=di.label.title(),
                qty=1,
                vol_cy=round(di.volume_cy, 2),
                source="Discrete_Database",
                surcharges=di.surcharges
            )
            items.append(item)
            discrete_total += di.volume_cy
    
    # Add bulk debris line
    bulk_cy = max(0, fusion_result.final_volume_cy - discrete_total)
    if bulk_cy > 0.1:
        # Count low-confidence items included in bulk
        low_conf_count = sum(
            1 for di in fusion_result.fused_discrete_items 
            if di.source == "bulk_included"
        )
        
        note = None
        if low_conf_count > 0:
            note = f"Includes {low_conf_count} low-confidence items"
            
        items.append(LineItem(
            name="Mixed Bulk Debris",
            qty=1,
            vol_cy=round(bulk_cy, 1),
            source="Measured_Terrain",
            note=note
        ))
    
    return items


def build_output(
    job_id: str,
    ingestion: IngestionResult,
    calibration: CalibrationResult,
    fusion: FusionResult,
    floor_quality: str,
    depth_confidence_avg: float
) -> dict[str, Any]:
    """
    Stage 7 Entry Point: Build final JSON output.
    
    Args:
        job_id: Unique job identifier
        ingestion: Result from Stage 1
        calibration: Result from Stage 4
        fusion: Result from Stage 6
        floor_quality: Aggregate floor quality
        depth_confidence_avg: Average depth confidence
        
    Returns:
        Dict matching the v2.0 JSON schema
    """
    # Apply conservative billing if needed
    final_volume = fusion.final_volume_cy
    uncertainty_min = fusion.uncertainty_min_cy
    uncertainty_max = fusion.uncertainty_max_cy
    
    if calibration.conservative_billing:
        final_volume = _round_conservative(final_volume)
        uncertainty_max = _round_conservative(uncertainty_max)
    
    # Determine if review is required
    review_required = (
        calibration.review_required or
        calibration.confidence == "LOW" or
        floor_quality == "failed" or
        len(fusion.valid_frames) < 2
    )
    
    # Calculate confidence
    confidence = _determine_overall_confidence(
        calibration.confidence,
        floor_quality,
        fusion.viewpoint_diversity,
        len(fusion.valid_frames)
    )
    
    # Build flags
    flags = FlagsPayload(
        review_required=review_required,
        calibration_source=calibration.calibration_source,
        viewpoint_diversity=fusion.viewpoint_diversity,
        conservative_billing=calibration.conservative_billing
    )
    
    # Build diagnostics
    rejected_ids = [m.original_path.split("/")[-1] for m in ingestion.rejected_frames]
    rejected_ids.extend(fusion.rejected_frames)
    
    diagnostics = DiagnosticsPayload(
        valid_frames=len(fusion.valid_frames),
        rejected_frames=rejected_ids,
        floor_quality=floor_quality,
        depth_confidence_avg=round(depth_confidence_avg, 2),
        calibration_source=calibration.calibration_source,
        fusion_method=fusion.fusion_method
    )
    
    # Build line items
    line_items = _build_line_items(fusion, final_volume)
    
    # Construct payload
    payload = OutputPayload(
        job_id=job_id,
        final_volume_cy=final_volume,
        uncertainty_range=[uncertainty_min, uncertainty_max],
        confidence_score=confidence,
        flags=flags,
        diagnostics=diagnostics,
        line_items=line_items
    )
    
    # Convert to dict for JSON serialization
    def convert_numpy(obj):
        """Recursively convert numpy types to Python natives."""
        import numpy as np
        if isinstance(obj, dict):
            return {k: convert_numpy(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_numpy(i) for i in obj]
        elif isinstance(obj, (np.floating, np.float32, np.float64)):
            return float(obj)
        elif isinstance(obj, (np.integer, np.int32, np.int64)):
            return int(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        else:
            return obj
    
    # First convert dataclass to dict, then clean up numpy types
    raw_dict = asdict(payload)
    return convert_numpy(raw_dict)
