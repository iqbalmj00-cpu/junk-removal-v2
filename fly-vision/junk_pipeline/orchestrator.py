"""
Orchestrator: Main Pipeline Entry Point
Runs all 7 stages of the Robust Metric Pipeline v2.0
"""

import uuid
import numpy as np
from pathlib import Path
from typing import Optional

from .ingestion import run_ingestion, IngestionResult
from .perception import run_perception, PerceptionResult
from .geometry import run_geometry, GeometryResult
from .calibration import run_calibration, CalibrationResult
from .volumetrics import run_volumetrics, VolumetricResult
from .fusion import run_fusion, FusionResult
from .output import build_output


def run_pipeline(
    image_paths: list[str],
    job_id: Optional[str] = None
) -> dict:
    """
    Run the complete 7-stage pipeline.
    
    Args:
        image_paths: List of absolute paths to input images
        job_id: Optional job identifier (auto-generated if not provided)
        
    Returns:
        Final JSON payload matching v2.0 schema
    """
    if job_id is None:
        job_id = str(uuid.uuid4())[:8]
        
    print(f"[Pipeline] Starting job {job_id} with {len(image_paths)} images")
    
    # =========================================================================
    # STAGE 1: Hardened Ingestion
    # =========================================================================
    print("[Stage 1] Ingestion...")
    ingestion_result = run_ingestion(image_paths)
    
    print(f"  → Valid frames: {len(ingestion_result.frames)}")
    print(f"  → Rejected: {len(ingestion_result.rejected_frames)}")
    print(f"  → Uncalibrated mode: {ingestion_result.uncalibrated_mode}")
    
    if not ingestion_result.frames:
        return build_output(
            job_id=job_id,
            ingestion=ingestion_result,
            calibration=CalibrationResult(frame_id="none", confidence="LOW"),
            fusion=FusionResult(final_volume_cy=0, uncertainty_min_cy=0, uncertainty_max_cy=0),
            floor_quality="failed",
            depth_confidence_avg=0.0
        )
    
    # =========================================================================
    # STAGE 2 & 3: Perception + Geometry (per frame)
    # =========================================================================
    perception_results: list[PerceptionResult] = []
    geometry_results: list[GeometryResult] = []
    
    for frame in ingestion_result.frames:
        # Stage 2: Perception (pass working_pil for Lane D floor segmentation)
        print(f"[Stage 2] Perception for {frame.metadata.image_id[:8]}...")
        working_pil = frame.get_pil()
        perception = run_perception(frame.metadata.image_id, frame.data_uri, working_pil=working_pil)
        perception_results.append(perception)
        
        print(f"  → Lane A: {len(perception.lane_a.instances)} items, {len(perception.lane_a.anchors)} anchors")
        print(f"  → Lane B: bulk_mask={perception.lane_b.bulk_mask_url is not None}")
        print(f"  → Lane C: scene={perception.lane_c.scene_type.value}")
        if perception.lane_d:
            print(f"  → Lane D: ground={perception.lane_d.model_used}, labels={perception.lane_d.labels_found}, area={perception.lane_d.ground_area_ratio:.1%}")
        
        # === FIX 1: Floor Visibility Gate ===
        # Reject frames where there's no usable floor evidence
        floor_visible = True
        bulk_mask_np = perception.lane_b.bulk_mask_np
        
        if bulk_mask_np is not None:
            # Check 1: Bulk mask covers > 85% of image
            bulk_area_pct = np.mean(bulk_mask_np) * 100
            if bulk_area_pct > 85:
                floor_visible = False
                print(f"  ⚠️ Floor Visibility Gate FAILED: bulk_mask={bulk_area_pct:.1f}% > 85%")
            
            # Check 2: Bottom 35% of image has < 8% non-bulk pixels
            if floor_visible:
                bottom_start = int(bulk_mask_np.shape[0] * 0.65)
                bottom_band = bulk_mask_np[bottom_start:, :]
                clear_area_pct = (1 - np.mean(bottom_band)) * 100
                if clear_area_pct < 8:
                    floor_visible = False
                    print(f"  ⚠️ Floor Visibility Gate FAILED: bottom-35% clear={clear_area_pct:.1f}% < 8%")
        
        if not floor_visible:
            # Skip geometry for this frame - no floor to find
            print(f"[Stage 3] Geometry SKIPPED for {frame.metadata.image_id[:8]} (no floor visible)")
            geometry_results.append(GeometryResult(frame_id=frame.metadata.image_id, floor_quality="failed"))
            continue
        
        # Stage 3: Geometry (HuggingFace Depth Pro + SegFormer floor mask)
        print(f"[Stage 3] Geometry for {frame.metadata.image_id[:8]}...")
        floor_mask = perception.lane_d.ground_mask_np if perception.lane_d else None
        geometry = run_geometry(
            frame_id=frame.metadata.image_id,
            working_pil=working_pil,
            scene_type=perception.lane_c.scene_type,
            bulk_mask=perception.lane_b.bulk_mask_np,
            floor_mask=floor_mask
        )
        geometry_results.append(geometry)
        
        print(f"  → Depth confidence: {geometry.depth_confidence_score:.2f}")
        print(f"  → Floor quality: {geometry.floor_quality}")
        if geometry.rectified_cloud:
            print(f"  → Point cloud size: {len(geometry.rectified_cloud.points)}")
    
    # =========================================================================
    # STAGE 4: Calibration (use first frame with anchors, or aggregate)
    # =========================================================================
    print("[Stage 4] Calibration...")
    
    # Collect all anchors across frames
    all_anchors = []
    for p in perception_results:
        all_anchors.extend(p.lane_a.anchors)
    
    # Use first geometry result for calibration
    first_geo = geometry_results[0] if geometry_results else None
    first_frame = ingestion_result.frames[0]
    
    calibration = run_calibration(
        frame_id=first_frame.metadata.image_id,
        anchors=all_anchors,
        depth_map=first_geo.depth_map if first_geo else None,
        f_px=0.75 * first_frame.metadata.width,  # Conservative default, actual used in geometry
        image_width=first_frame.metadata.width,
        image_height=first_frame.metadata.height,
        exif_available=first_frame.metadata.exif_present,
        intrinsics_available=first_geo.intrinsics is not None if first_geo else False
    )
    
    print(f"  → Scale factor: {calibration.scale_factor:.3f}")
    print(f"  → Source: {calibration.calibration_source}")
    print(f"  → Confidence: {calibration.confidence}")
    
    # =========================================================================
    # STAGE 5: Volumetrics (per frame)
    # =========================================================================
    volumetric_results: list[VolumetricResult] = []
    
    for i, (perception, geometry, frame) in enumerate(zip(
        perception_results, geometry_results, ingestion_result.frames
    )):
        print(f"[Stage 5] Volumetrics for {frame.metadata.image_id[:8]}...")
        
        rectified = geometry.rectified_cloud.points if geometry.rectified_cloud else None
        pixel_indices = geometry.rectified_cloud.pixel_indices if geometry.rectified_cloud else None
        
        # Get ground mask from Lane D if available
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
            bulk_mask_np=perception.lane_b.bulk_mask_np,  # Lane B for foreground
            ground_mask_np=ground_mask,  # Lane D (kept for compatibility)
            pixel_indices=pixel_indices,  # Correct point-to-pixel mapping
            floor_flatness_p95=geometry.floor_flatness_p95  # From geometry RANSAC
        )
        volumetric_results.append(vol_result)
        
        print(f"  → Bulk raw: {vol_result.bulk_raw_cy:.2f} yd³")
        print(f"  → Bulk net: {vol_result.bulk_net_cy:.2f} yd³")
        print(f"  → Discrete: {vol_result.discrete_volume_cy:.2f} yd³")
        print(f"  → Frame total: {vol_result.frame_volume_cy:.2f} yd³")
    
    # =========================================================================
    # STAGE 6: Multi-View Fusion
    # =========================================================================
    print("[Stage 6] Fusion...")
    
    floor_qualities = {g.frame_id: g.floor_quality for g in geometry_results}
    depth_confidences = {g.frame_id: g.depth_confidence_score for g in geometry_results}
    floor_flatness_p95s = {g.frame_id: g.floor_flatness_p95 for g in geometry_results}
    inlier_ratios = {g.frame_id: g.ground_plane.inlier_ratio if g.ground_plane else 0.0 for g in geometry_results}
    # NEW: Pass mask coverages from Lane B to detect no-mask frames
    mask_coverages = {p.frame_id: p.lane_b.bulk_area_ratio for p in perception_results}
    
    fusion = run_fusion(
        frame_results=volumetric_results,
        floor_qualities=floor_qualities,
        depth_confidences=depth_confidences,
        floor_flatness_p95s=floor_flatness_p95s,
        inlier_ratios=inlier_ratios,
        mask_coverages=mask_coverages
    )
    
    print(f"  → Valid frames: {len(fusion.valid_frames)}")
    print(f"  → Viewpoint diversity: {fusion.viewpoint_diversity}")
    print(f"  → Fusion method: {fusion.fusion_method}")
    print(f"  → Final volume: {fusion.final_volume_cy:.1f} yd³")
    print(f"  → Range: [{fusion.uncertainty_min_cy:.1f}, {fusion.uncertainty_max_cy:.1f}]")
    
    # =========================================================================
    # STAGE 6.5: Foreman Audit (Optional GPT-based sanity check)
    # =========================================================================
    audit_result = None
    try:
        from .audit import run_foreman_audit, select_best_view_image
        
        # Only run if OPENAI_API_KEY is set
        import os
        if os.environ.get("OPENAI_API_KEY"):
            print("[Stage 6.5] Foreman Audit...")
            
            # Select best-view image
            best_image = select_best_view_image(
                frames=ingestion_result.frames,
                floor_qualities=floor_qualities,
                depth_confidences=depth_confidences
            )
            
            if best_image:
                # Collect detected items from all frames
                detected_items = []
                for p in perception_results:
                    for inst in p.lane_a.instances:
                        detected_items.append(inst.label)
                
                # Collect frame volumes
                frame_volumes = [v.frame_volume_cy for v in volumetric_results]
                
                # Collect flags
                flags = []
                if ingestion_result.uncalibrated_mode:
                    flags.append("uncalibrated")
                if fusion.viewpoint_diversity == "low":
                    flags.append("low_diversity")
                
                audit_result = run_foreman_audit(
                    best_image_path=best_image,
                    final_volume_cy=fusion.final_volume_cy,
                    uncertainty_min=fusion.uncertainty_min_cy,
                    uncertainty_max=fusion.uncertainty_max_cy,
                    frame_volumes=frame_volumes,
                    detected_items=list(set(detected_items)),  # Dedupe
                    flags=flags
                )
                
                print(f"  → Audit status: {audit_result.status}")
                if audit_result.flag_for_human_review:
                    print(f"  → ⚠️ FLAGGED FOR HUMAN REVIEW")
        else:
            print("[Stage 6.5] Foreman Audit skipped (no OPENAI_API_KEY)")
    except ImportError:
        print("[Stage 6.5] Foreman Audit skipped (module not available)")
    except Exception as e:
        print(f"[Stage 6.5] Foreman Audit failed: {e}")
    
    # =========================================================================
    # STAGE 7: Output
    # =========================================================================
    print("[Stage 7] Building output...")
    
    # Aggregate floor quality and depth confidence
    floor_quality = "good"
    if any(fq == "failed" for fq in floor_qualities.values()):
        floor_quality = "failed"
    elif any(fq == "noisy" for fq in floor_qualities.values()):
        floor_quality = "noisy"
        
    depth_conf_avg = sum(depth_confidences.values()) / len(depth_confidences) if depth_confidences else 0.0
    
    output = build_output(
        job_id=job_id,
        ingestion=ingestion_result,
        calibration=calibration,
        fusion=fusion,
        floor_quality=floor_quality,
        depth_confidence_avg=depth_conf_avg
    )
    
    # Add audit results to output if available
    if audit_result:
        output["audit"] = {
            "status": audit_result.status,
            "visual_volume_estimate": audit_result.visual_volume_estimate,
            "confidence_score": audit_result.confidence_score,
            "flag_for_human_review": audit_result.flag_for_human_review,
            "missing_items": audit_result.missing_items,
            "audit_reason": audit_result.audit_reason
        }
    
    print(f"\n[Pipeline] Complete!")
    print(f"  Final: {output['final_volume_cy']} yd³")
    print(f"  Confidence: {output['confidence_score']}")
    
    return output


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
