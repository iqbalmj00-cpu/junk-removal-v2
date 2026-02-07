"""
Orchestrator v9.0: Assembly-Line + Best-Frame Anchor Pipeline

This is a complete rewrite of the pipeline orchestration implementing:
1. Qwen VLM arbitration for frame ranking and box selection
2. Serial best-frame-first processing
3. Box-constrained SAM2 segmentation
4. Pile-blanked SegFormer ground detection
5. Unchanged geometry/volumetrics modules

Replaces the parallel "Tri-Lane" perception architecture.
"""

import os
import uuid
import numpy as np
from pathlib import Path
from typing import Optional
from PIL import Image, ImageDraw, ImageFont

from .ingestion import run_ingestion, IngestionResult
from .perception import run_ground_detection, SceneType, LaneDResult
from .geometry import run_geometry, GeometryResult
from .calibration import run_calibration, CalibrationResult
from .volumetrics import run_volumetrics, VolumetricResult
from .fusion import run_fusion, FusionResult
from .output import build_output
from .qwen_arbitration import rank_frames, select_pile_box, select_pile_boxes, select_pile_boxes_with_reference, MultiBoxSelectionResult
from .grounded_sam_runner import GroundedSAMRunner
from .florence_labeler import label_boxes  # v10.1: Florence-2 independent box labeling


# =============================================================================
# v9.0: OVERLAY SAVING UTILITIES
# =============================================================================

def _ensure_overlay_dir(job_id: str) -> str:
    """Create and return overlay directory path."""
    overlay_dir = f"/tmp/gate_overlays/{job_id}"
    os.makedirs(overlay_dir, exist_ok=True)
    return overlay_dir


def _save_dino_boxes_overlay(
    image_pil: Image.Image,
    boxes: list[dict],
    selected_indices: list[int],  # v9.1: Support multiple selected boxes
    frame_id: str,
    job_id: str
):
    """Save DINO bounding boxes overlay with selected boxes highlighted."""
    overlay_dir = _ensure_overlay_dir(job_id)
    img_copy = image_pil.copy()
    draw = ImageDraw.Draw(img_copy)
    
    # Colors: green for selected, red for others
    for i, box_info in enumerate(boxes):
        x1, y1, x2, y2 = box_info['box']
        is_selected = i in selected_indices
        color = '#00FF00' if is_selected else '#FF0000'
        width = 4 if is_selected else 2
        
        # Draw rectangle
        draw.rectangle([x1, y1, x2, y2], outline=color, width=width)
        
        # Draw label
        label = f"{i+1}: {box_info.get('label', '?')} ({box_info.get('confidence', 0):.2f})"
        text_y = y1 - 20 if y1 > 25 else y2 + 5
        draw.text((x1, text_y), label, fill=color)
    
    # Save
    path = f"{overlay_dir}/{frame_id[:8]}_dino_boxes.png"
    img_copy.save(path)
    print(f"[OVERLAY] Saved: {path}")


def _save_mask_overlay(
    image_pil: Image.Image,
    mask: np.ndarray,
    mask_name: str,
    frame_id: str,
    job_id: str,
    color: tuple = (0, 255, 0, 128)  # Semi-transparent green
):
    """Save mask overlay on original image."""
    overlay_dir = _ensure_overlay_dir(job_id)
    
    # Create RGBA overlay
    img_rgba = image_pil.convert("RGBA")
    overlay = Image.new("RGBA", img_rgba.size, (0, 0, 0, 0))
    
    # Resize mask if needed
    if mask.shape != (image_pil.height, image_pil.width):
        from PIL import Image as PILImage
        mask_img = PILImage.fromarray((mask * 255).astype(np.uint8))
        mask_img = mask_img.resize((image_pil.width, image_pil.height), PILImage.NEAREST)
        mask = np.array(mask_img) > 127
    
    # Apply color to mask region
    overlay_array = np.array(overlay)
    overlay_array[mask, :] = color
    overlay = Image.fromarray(overlay_array)
    
    # Composite
    result = Image.alpha_composite(img_rgba, overlay)
    
    # Save
    path = f"{overlay_dir}/{frame_id[:8]}_{mask_name}.png"
    result.save(path)
    print(f"[OVERLAY] Saved: {path}")


def _save_combined_overlay(
    image_pil: Image.Image,
    pile_mask: np.ndarray,
    ground_mask: np.ndarray,
    frame_id: str,
    job_id: str
):
    """Save combined pile (green) + ground (blue) overlay."""
    overlay_dir = _ensure_overlay_dir(job_id)
    
    img_rgba = image_pil.convert("RGBA")
    overlay = Image.new("RGBA", img_rgba.size, (0, 0, 0, 0))
    overlay_array = np.array(overlay)
    
    # Resize masks if needed
    h, w = image_pil.height, image_pil.width
    
    if pile_mask is not None and pile_mask.shape != (h, w):
        from PIL import Image as PILImage
        mask_img = PILImage.fromarray((pile_mask * 255).astype(np.uint8))
        mask_img = mask_img.resize((w, h), PILImage.NEAREST)
        pile_mask = np.array(mask_img) > 127
    
    if ground_mask is not None and ground_mask.shape != (h, w):
        from PIL import Image as PILImage
        mask_img = PILImage.fromarray((ground_mask * 255).astype(np.uint8))
        mask_img = mask_img.resize((w, h), PILImage.NEAREST)
        ground_mask = np.array(mask_img) > 127
    
    # Ground = blue (apply first, so pile overlays it)
    if ground_mask is not None:
        overlay_array[ground_mask, :] = (0, 100, 255, 100)
    
    # Pile = green (apply second)  
    if pile_mask is not None:
        overlay_array[pile_mask, :] = (0, 255, 0, 150)
    
    overlay = Image.fromarray(overlay_array)
    result = Image.alpha_composite(img_rgba, overlay)
    
    path = f"{overlay_dir}/{frame_id[:8]}_combined.png"
    result.save(path)
    print(f"[OVERLAY] Saved: {path}")


def _create_reference_overlay(
    image_pil: Image.Image,
    pile_mask: np.ndarray,
    alpha: int = 180
) -> Image.Image:
    """
    v9.2: Create reference overlay showing pile mask in green.
    
    Used to guide secondary frame box selection - shows Qwen
    what was identified as junk in the best frame.
    
    Args:
        image_pil: Original image
        pile_mask: Binary pile mask
        alpha: Overlay transparency (0-255)
        
    Returns:
        RGB image with green mask overlay
    """
    img_rgba = image_pil.convert("RGBA")
    h, w = image_pil.height, image_pil.width
    
    # Resize mask if needed
    if pile_mask.shape != (h, w):
        from PIL import Image as PILImage
        mask_img = PILImage.fromarray((pile_mask * 255).astype(np.uint8))
        mask_img = mask_img.resize((w, h), PILImage.NEAREST)
        pile_mask = np.array(mask_img) > 127
    
    # Create green overlay
    overlay = Image.new("RGBA", img_rgba.size, (0, 0, 0, 0))
    overlay_array = np.array(overlay)
    overlay_array[pile_mask, :] = (0, 255, 0, alpha)  # Bright green
    overlay = Image.fromarray(overlay_array)
    
    # Composite and convert to RGB (required for VLM)
    result = Image.alpha_composite(img_rgba, overlay)
    return result.convert("RGB")


def run_pipeline(
    image_paths: list[str],
    job_id: Optional[str] = None,
    exif_data: Optional[list[dict]] = None
) -> dict:
    """
    v9.0: Run the complete Assembly-Line + Best-Frame Anchor pipeline.
    
    Args:
        image_paths: List of absolute paths to input images
        job_id: Optional job identifier (auto-generated if not provided)
        exif_data: Optional list of frontend-extracted EXIF dicts
        
    Returns:
        Final JSON payload matching v2.0 schema
    """
    if job_id is None:
        job_id = str(uuid.uuid4())[:8]
        
    print(f"[Pipeline v9.0] Starting job {job_id} with {len(image_paths)} images")
    
    # =========================================================================
    # STAGE 1: Hardened Ingestion (UNCHANGED)
    # =========================================================================
    print("[Stage 1] Ingestion...")
    ingestion_result = run_ingestion(image_paths, exif_data=exif_data)
    frames = ingestion_result.frames
    
    print(f"  → Valid frames: {len(frames)}")
    print(f"  → Rejected: {len(ingestion_result.rejected_frames)}")
    
    if not frames:
        return _build_empty_output(job_id, ingestion_result)
    
    # =========================================================================
    # STAGE 2: Frame Triage (Qwen)
    # =========================================================================
    print("[Stage 2] Frame Triage (Qwen)...")
    ranking = rank_frames(frames)
    best_frame_id = ranking.best_frame_id
    best_frame = next(f for f in frames if f.metadata.image_id == best_frame_id)
    secondary_frames = [f for f in frames if f.metadata.image_id != best_frame_id]
    
    print(f"  → Best frame: {best_frame_id[:8]} (confidence={ranking.confidence:.2f})")
    print(f"  → Secondary frames: {len(secondary_frames)}")
    
    # Unload Qwen to free VRAM for DINO/SAM2
    from .qwen_local import unload_qwen
    unload_qwen()
    
    # =========================================================================
    # STAGE 3: Pile Detection (DINO) — Best Frame
    # =========================================================================
    print(f"[Stage 3] Pile Detection (DINO) for {best_frame_id[:8]}...")
    dino_runner = GroundedSAMRunner()
    candidate_boxes = dino_runner.run_detection(best_frame.get_pil())
    
    print(f"  → Detected {len(candidate_boxes)} candidate boxes")
    
    # v10.1: Florence-2 labels each box crop independently
    if candidate_boxes:
        candidate_boxes = label_boxes(best_frame.get_pil(), candidate_boxes)
    
    if not candidate_boxes:
        print("  ⚠️ No boxes detected — cannot proceed")
        return _build_empty_output(job_id, ingestion_result)
    
    # =========================================================================
    # STAGE 4: Box Selection (Qwen) — v9.7: Direct from DINO, no pre-classifier
    # =========================================================================
    print(f"[Stage 4] Box Selection (Qwen) for {best_frame_id[:8]}...")
    
    # v9.7: Pass DINO boxes directly to Qwen - it handles classification + selection
    box_result = select_pile_boxes(best_frame.get_pil(), candidate_boxes)
    
    selected_indices = [b['index'] for b in box_result.selected_boxes]
    print(f"  → Selected {len(box_result.selected_boxes)} box(es): {[i+1 for i in selected_indices]}")
    print(f"  → Multi-pile: {box_result.multi_pile}")
    print(f"  → Reason: {box_result.reason[:80]}...")
    
    # v9.9: Guard against Qwen rejecting ALL boxes (no junk in image)
    if not box_result.selected_boxes:
        print("  ⚠️ Qwen rejected all boxes — no junk detected")
        return _build_empty_output(job_id, ingestion_result)
    
    # v9.1: Save DINO boxes overlay (all selected boxes highlighted)
    _save_dino_boxes_overlay(
        best_frame.get_pil(), candidate_boxes, 
        selected_indices, best_frame_id, job_id
    )
    
    # v9.8: Unload Qwen to free VRAM for SAM2/DepthPro
    from .qwen_local import unload_qwen, is_loaded
    if is_loaded():
        unload_qwen()
    
    # =========================================================================
    # STAGE 5: Pile Segmentation (SAM2) — Best Frame (v9.1: Union masks)
    # =========================================================================
    print(f"[Stage 5] Pile Segmentation (SAM2) for {best_frame_id[:8]}...")
    
    # v9.1: Segment each selected box and union the masks
    if len(box_result.selected_boxes) == 1:
        # Single box - simple case
        best_box = box_result.selected_boxes[0]['box']
        best_pile_mask = dino_runner.run_segmentation_on_box(best_frame.get_pil(), best_box)
    else:
        # Multiple boxes - union masks
        best_pile_mask = None
        for box_info in box_result.selected_boxes:
            mask = dino_runner.run_segmentation_on_box(best_frame.get_pil(), box_info['box'])
            if best_pile_mask is None:
                best_pile_mask = mask.astype(bool)
            else:
                best_pile_mask = np.logical_or(best_pile_mask, mask)
        print(f"  → Merged {len(box_result.selected_boxes)} masks (multi-pile)")
    
    pile_area_pct = np.mean(best_pile_mask) * 100
    
    print(f"  → Pile mask area: {pile_area_pct:.1f}%")
    
    # v9.0: Save pile mask overlay
    _save_mask_overlay(
        best_frame.get_pil(), best_pile_mask, "pile_mask",
        best_frame_id, job_id, color=(0, 255, 0, 150)  # Green
    )
    
    # v9.2: Create reference overlay for secondary frame guidance
    reference_overlay = _create_reference_overlay(best_frame.get_pil(), best_pile_mask)
    
    # =========================================================================
    # STAGE 6: Ground Segmentation (SegFormer) — Pile Blanked
    # =========================================================================
    print(f"[Stage 6] Ground Segmentation (SegFormer) for {best_frame_id[:8]}...")
    best_ground_result = run_ground_detection(
        working_pil=best_frame.get_pil(),
        pile_mask=best_pile_mask  # <-- PILE BLANKED
    )
    
    print(f"  → Ground mask area: {best_ground_result.ground_area_ratio:.1%}")
    print(f"  → Model used: {best_ground_result.model_used}")
    
    # v9.0: Save ground mask overlay
    _save_mask_overlay(
        best_frame.get_pil(), best_ground_result.ground_mask_np, "ground_mask",
        best_frame_id, job_id, color=(0, 100, 255, 120)  # Blue
    )
    
    # v9.0: Save combined overlay (pile + ground)
    _save_combined_overlay(
        best_frame.get_pil(), best_pile_mask, best_ground_result.ground_mask_np,
        best_frame_id, job_id
    )
    
    # =========================================================================
    # STAGE 7: Geometry (DepthPro + RANSAC) — Best Frame
    # =========================================================================
    print(f"[Stage 7] Geometry for {best_frame_id[:8]}...")
    best_geometry = run_geometry(
        frame_id=best_frame_id,
        working_pil=best_frame.get_pil(),
        scene_type=SceneType.UNKNOWN,  # Not using BLIP anymore
        bulk_mask=best_pile_mask,
        floor_mask=best_ground_result.ground_mask_np,
        calibration_bundle=best_frame.calibration_bundle
    )
    
    print(f"  → Floor quality: {best_geometry.floor_quality}")
    print(f"  → Depth confidence: {best_geometry.depth_confidence_score:.2f}")
    
    # =========================================================================
    # PHASE 2: SECONDARY FRAMES (v9.2: with reference context)
    # =========================================================================
    all_results = [(best_frame, best_pile_mask, best_ground_result, best_geometry)]
    
    for frame in secondary_frames:
        # v9.2: Pass reference overlay and mask to guide secondary frame processing
        result = _process_secondary_frame(
            frame, dino_runner, job_id,
            reference_overlay=reference_overlay,
            reference_mask=best_pile_mask
        )
        if result:
            all_results.append(result)
        else:
            print(f"  → Frame {frame.metadata.image_id[:8]} skipped (no valid box)")
    
    # =========================================================================
    # STAGE 8: Volumetrics (per frame)
    # =========================================================================
    volumetric_results = []
    pile_masks = {}  # For fusion mask_coverages
    
    for frame, pile_mask, ground_result, geometry in all_results:
        frame_id = frame.metadata.image_id
        print(f"[Stage 8] Volumetrics for {frame_id[:8]}...")
        
        pile_masks[frame_id] = pile_mask
        
        # Get point cloud data
        rectified = geometry.rectified_cloud.points if geometry.rectified_cloud else None
        pixel_indices = geometry.rectified_cloud.pixel_indices if geometry.rectified_cloud else None
        
        # v10.4: No scale factor needed - using DepthPro intrinsics consistently
        # (intrinsics ratio is used for gating, not scaling)
        
        vol_result = run_volumetrics(
            frame_id=frame_id,
            instances=[],  # YOLO deprecated — no discrete items
            rectified_cloud=rectified,
            depth_map=geometry.depth_map,
            scale_factor=1.0,  # v10.4: No scaling - consistent intrinsics
            image_width=frame.metadata.width,
            image_height=frame.metadata.height,
            bulk_mask_np=pile_mask,
            ground_mask_np=ground_result.ground_mask_np,
            pixel_indices=pixel_indices,
            floor_flatness_p95=geometry.floor_flatness_p95,
            support_plane_selected=geometry.support_plane_selected,
            sr_yfl95=geometry.sr_yfl95,
            sr_inlier_ratio=geometry.sr_inlier_ratio
        )
        volumetric_results.append(vol_result)
        
        print(f"  → Frame volume: {vol_result.frame_volume_cy:.2f} yd³")
    
    # =========================================================================
    # STAGE 9: Fusion
    # =========================================================================
    print("[Stage 9] Fusion...")
    
    # Compute mask coverages from pile_masks (not from PerceptionResult)
    mask_coverages = {
        fid: float(np.mean(mask)) 
        for fid, mask in pile_masks.items()
    }
    
    # Collect geometry metrics
    geometry_map = {r[0].metadata.image_id: r[3] for r in all_results}
    floor_qualities = {fid: g.floor_quality for fid, g in geometry_map.items()}
    depth_confidences = {fid: g.depth_confidence_score for fid, g in geometry_map.items()}
    floor_flatness_p95s = {fid: g.floor_flatness_p95 for fid, g in geometry_map.items()}
    inlier_ratios = {
        fid: g.ground_plane.inlier_ratio if g.ground_plane else 0.0 
        for fid, g in geometry_map.items()
    }
    support_plane_selected = {fid: g.support_plane_selected for fid, g in geometry_map.items()}
    sr_inlier_ratios = {fid: g.sr_inlier_ratio for fid, g in geometry_map.items()}
    sr_yfl95s = {fid: g.sr_yfl95 for fid, g in geometry_map.items()}
    
    # v10.4: Intrinsics data for gating
    intrinsics_fx_ratios = {fid: g.intrinsics_fx_ratio for fid, g in geometry_map.items()}
    intrinsics_derived = {fid: g.intrinsics_derived for fid, g in geometry_map.items()}
    
    fusion = run_fusion(
        frame_results=volumetric_results,
        floor_qualities=floor_qualities,
        depth_confidences=depth_confidences,
        floor_flatness_p95s=floor_flatness_p95s,
        inlier_ratios=inlier_ratios,
        mask_coverages=mask_coverages,
        support_plane_selected=support_plane_selected,
        sr_inlier_ratios=sr_inlier_ratios,
        sr_yfl95s=sr_yfl95s,
        intrinsics_fx_ratios=intrinsics_fx_ratios,
        intrinsics_derived=intrinsics_derived
    )
    
    print(f"  → Valid frames: {len(fusion.valid_frames)}")
    print(f"  → Fusion method: {fusion.fusion_method}")
    print(f"  → Final volume: {fusion.final_volume_cy:.1f} yd³")
    print(f"  → Range: [{fusion.uncertainty_min_cy:.1f}, {fusion.uncertainty_max_cy:.1f}]")
    
    # =========================================================================
    # STAGE 10: Output
    # =========================================================================
    print("[Stage 10] Building output...")
    
    # Aggregate floor quality
    floor_quality = _aggregate_floor_quality(floor_qualities)
    depth_conf_avg = sum(depth_confidences.values()) / len(depth_confidences) if depth_confidences else 0.0
    
    # Build calibration result (simplified for v9.0)
    calibration = CalibrationResult(
        frame_id=best_frame_id,
        confidence="MEDIUM",
        scale_factor=1.0,
        calibration_source="exif_default"
    )
    
    output = build_output(
        job_id=job_id,
        ingestion=ingestion_result,
        calibration=calibration,
        fusion=fusion,
        floor_quality=floor_quality,
        depth_confidence_avg=depth_conf_avg
    )
    
    print(f"\n[Pipeline v9.0] Complete!")
    print(f"  Final: {output['final_volume_cy']} yd³")
    print(f"  Confidence: {output.get('confidence_score', 'N/A')}")
    
    return output


def _process_secondary_frame(
    frame,
    dino_runner: GroundedSAMRunner,
    job_id: str,
    reference_overlay: Image.Image,  # v9.2: visual reference for Qwen
    reference_mask: np.ndarray       # v9.2: mask hint for SAM2
) -> Optional[tuple]:
    """
    Process a single secondary frame using reference-guided arbitration.
    
    v9.2: Uses best frame's mask overlay to guide Qwen box selection,
    and passes mask hint to SAM2 for tighter segmentation.
    
    Returns:
        Tuple of (frame, pile_mask, ground_result, geometry) or None if failed.
    """
    frame_id = frame.metadata.image_id
    print(f"[Secondary] Processing {frame_id[:8]}...")
    
    # Stage A: Detection
    boxes = dino_runner.run_detection(frame.get_pil())
    if not boxes:
        print(f"  → No boxes detected, skipping")
        return None
    
    # v10.1: Florence-2 labels each box crop independently
    boxes = label_boxes(frame.get_pil(), boxes)
    
    # Stage B: Box Selection (Qwen) — v9.7: Direct from DINO
    box_result = select_pile_boxes_with_reference(
        reference_image=reference_overlay,
        target_image=frame.get_pil(),
        target_boxes=boxes
    )
    
    # v10: Qwen's selection itself is the validation - if boxes were selected, they're valid
    # Skip only if Qwen returned no boxes (already handled by falling back to highest conf)
    if not box_result.selected_boxes:
        print(f"  → No boxes selected by Qwen, skipping")
        return None
    
    # v9.2: Save DINO boxes overlay for secondary frame
    selected_indices = [b['index'] for b in box_result.selected_boxes]
    _save_dino_boxes_overlay(
        frame.get_pil(), boxes,
        selected_indices, frame_id, job_id
    )
    
    # v9.8: Unload Qwen to free VRAM for SAM2
    from .qwen_local import unload_qwen, is_loaded
    if is_loaded():
        unload_qwen()
    
    # Stage C: Segmentation — v9.2: Union masks with mask hints
    if len(box_result.selected_boxes) == 1:
        pile_mask = dino_runner.run_segmentation_on_box(
            frame.get_pil(), 
            box_result.selected_boxes[0]['box'],
            mask_hint=reference_mask  # v9.2: pass reference mask
        )
    else:
        # Multiple boxes - union masks with hints
        pile_mask = None
        for box_info in box_result.selected_boxes:
            mask = dino_runner.run_segmentation_on_box(
                frame.get_pil(), 
                box_info['box'],
                mask_hint=reference_mask  # v9.2: pass reference mask
            )
            if pile_mask is None:
                pile_mask = mask.astype(bool)
            else:
                pile_mask = np.logical_or(pile_mask, mask)
        print(f"  → Merged {len(box_result.selected_boxes)} masks (multi-pile)")
    
    # v9.0: Save pile mask overlay for secondary frame
    _save_mask_overlay(
        frame.get_pil(), pile_mask, "pile_mask",
        frame_id, job_id, color=(0, 255, 0, 150)
    )
    
    # Stage D: Ground Segmentation (pile blanked)
    ground_result = run_ground_detection(
        working_pil=frame.get_pil(),
        pile_mask=pile_mask
    )
    
    # v9.0: Save ground and combined overlays for secondary frame
    _save_mask_overlay(
        frame.get_pil(), ground_result.ground_mask_np, "ground_mask",
        frame_id, job_id, color=(0, 100, 255, 120)
    )
    _save_combined_overlay(
        frame.get_pil(), pile_mask, ground_result.ground_mask_np,
        frame_id, job_id
    )
    
    # Stage E: Geometry
    geometry = run_geometry(
        frame_id=frame_id,
        working_pil=frame.get_pil(),
        scene_type=SceneType.UNKNOWN,
        bulk_mask=pile_mask,
        floor_mask=ground_result.ground_mask_np,
        calibration_bundle=frame.calibration_bundle
    )
    
    print(f"  → Complete: mask={np.mean(pile_mask)*100:.1f}%, floor={geometry.floor_quality}")
    
    return (frame, pile_mask, ground_result, geometry)


def _aggregate_floor_quality(floor_qualities: dict) -> str:
    """Aggregate floor quality across frames."""
    if any(fq == "failed" for fq in floor_qualities.values()):
        return "failed"
    if any(fq == "noisy" for fq in floor_qualities.values()):
        return "noisy"
    return "good"


def _build_empty_output(job_id: str, ingestion: IngestionResult) -> dict:
    """Build output for failed pipeline (no valid frames)."""
    return build_output(
        job_id=job_id,
        ingestion=ingestion,
        calibration=CalibrationResult(frame_id="none", confidence="LOW"),
        fusion=FusionResult(final_volume_cy=0, uncertainty_min_cy=0, uncertainty_max_cy=0),
        floor_quality="failed",
        depth_confidence_avg=0.0
    )


# =============================================================================
# LEGACY: Keep old run_pipeline for A/B testing (renamed)
# =============================================================================

def run_pipeline_v8(
    image_paths: list[str],
    job_id: Optional[str] = None,
    exif_data: Optional[list[dict]] = None
) -> dict:
    """
    v8.x: Legacy parallel perception pipeline.
    
    Kept for A/B comparison testing. Uses old run_perception() flow.
    """
    from .perception import run_perception, PerceptionResult
    
    if job_id is None:
        job_id = str(uuid.uuid4())[:8]
        
    print(f"[Pipeline v8] Starting job {job_id} with {len(image_paths)} images")
    
    # Stage 1: Ingestion
    ingestion_result = run_ingestion(image_paths, exif_data=exif_data)
    
    if not ingestion_result.frames:
        return _build_empty_output(job_id, ingestion_result)
    
    # Stage 2 & 3: Perception + Geometry (per frame, parallel style)
    perception_results = []
    geometry_results = []
    
    for frame in ingestion_result.frames:
        working_pil = frame.get_pil()
        perception = run_perception(frame.metadata.image_id, frame.data_uri, working_pil=working_pil)
        perception_results.append(perception)
        
        # Check floor visibility
        floor_visible = True
        bulk_mask_np = perception.lane_b.bulk_mask_np
        if bulk_mask_np is not None:
            bulk_area_pct = np.mean(bulk_mask_np) * 100
            if bulk_area_pct > 85:
                floor_visible = False
        
        if not floor_visible:
            geometry_results.append(GeometryResult(frame_id=frame.metadata.image_id, floor_quality="failed"))
            continue
        
        floor_mask = perception.lane_d.ground_mask_np if perception.lane_d else None
        geometry = run_geometry(
            frame_id=frame.metadata.image_id,
            working_pil=working_pil,
            scene_type=perception.lane_c.scene_type,
            bulk_mask=perception.lane_b.bulk_mask_np,
            floor_mask=floor_mask,
            calibration_bundle=frame.calibration_bundle
        )
        geometry_results.append(geometry)
    
    # Stage 4: Calibration
    all_anchors = []
    for p in perception_results:
        all_anchors.extend(p.lane_a.anchors)
    
    first_geo = geometry_results[0] if geometry_results else None
    first_frame = ingestion_result.frames[0]
    
    calibration = run_calibration(
        frame_id=first_frame.metadata.image_id,
        anchors=all_anchors,
        depth_map=first_geo.depth_map if first_geo else None,
        f_px=0.75 * first_frame.metadata.width,
        image_width=first_frame.metadata.width,
        image_height=first_frame.metadata.height,
        exif_available=first_frame.metadata.exif_present,
        intrinsics_available=first_geo.intrinsics is not None if first_geo else False
    )
    
    # Stage 5: Volumetrics (per frame)
    volumetric_results = []
    
    for i, (perception, geometry, frame) in enumerate(zip(
        perception_results, geometry_results, ingestion_result.frames
    )):
        rectified = geometry.rectified_cloud.points if geometry.rectified_cloud else None
        pixel_indices = geometry.rectified_cloud.pixel_indices if geometry.rectified_cloud else None
        ground_mask = None
        if perception.lane_d and perception.lane_d.ground_mask_np is not None:
            ground_mask = perception.lane_d.ground_mask_np
        
        vol_result = run_volumetrics(
            frame_id=frame.metadata.image_id,
            instances=perception.lane_a.instances,
            rectified_cloud=rectified,
            depth_map=geometry.depth_map,
            scale_factor=calibration.scale_factor,
            image_width=frame.metadata.width,
            image_height=frame.metadata.height,
            bulk_mask_np=perception.lane_b.bulk_mask_np,
            ground_mask_np=ground_mask,
            pixel_indices=pixel_indices,
            floor_flatness_p95=geometry.floor_flatness_p95,
            support_plane_selected=geometry.support_plane_selected,
            sr_yfl95=geometry.sr_yfl95,
            sr_inlier_ratio=geometry.sr_inlier_ratio
        )
        volumetric_results.append(vol_result)
    
    # Stage 6: Fusion
    floor_qualities = {g.frame_id: g.floor_quality for g in geometry_results}
    depth_confidences = {g.frame_id: g.depth_confidence_score for g in geometry_results}
    floor_flatness_p95s = {g.frame_id: g.floor_flatness_p95 for g in geometry_results}
    inlier_ratios = {g.frame_id: g.ground_plane.inlier_ratio if g.ground_plane else 0.0 for g in geometry_results}
    mask_coverages = {p.frame_id: p.lane_b.bulk_area_ratio for p in perception_results}
    support_plane_selected = {g.frame_id: g.support_plane_selected for g in geometry_results}
    sr_inlier_ratios = {g.frame_id: g.sr_inlier_ratio for g in geometry_results}
    sr_yfl95s = {g.frame_id: g.sr_yfl95 for g in geometry_results}
    
    fusion = run_fusion(
        frame_results=volumetric_results,
        floor_qualities=floor_qualities,
        depth_confidences=depth_confidences,
        floor_flatness_p95s=floor_flatness_p95s,
        inlier_ratios=inlier_ratios,
        mask_coverages=mask_coverages,
        support_plane_selected=support_plane_selected,
        sr_inlier_ratios=sr_inlier_ratios,
        sr_yfl95s=sr_yfl95s
    )
    
    # Stage 7: Output
    floor_quality = "good"
    if any(fq == "failed" for fq in floor_qualities.values()):
        floor_quality = "failed"
    elif any(fq == "noisy" for fq in floor_qualities.values()):
        floor_quality = "noisy"
    
    depth_conf_avg = sum(depth_confidences.values()) / len(depth_confidences) if depth_confidences else 0.0
    
    return build_output(
        job_id=job_id,
        ingestion=ingestion_result,
        calibration=calibration,
        fusion=fusion,
        floor_quality=floor_quality,
        depth_confidence_avg=depth_conf_avg
    )


if __name__ == "__main__":
    import sys
    import json
    
    if len(sys.argv) < 2:
        print("Usage: python orchestrator.py <image1> [image2] ...")
        sys.exit(1)
        
    paths = sys.argv[1:]
    result = run_pipeline(paths)
    
    print("\n" + "="*60)
    print("FINAL OUTPUT:")
    print("="*60)
    print(json.dumps(result, indent=2))
