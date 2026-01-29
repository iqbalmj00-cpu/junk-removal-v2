"""
v4.0 Pipeline Orchestrator

Main entry point for the v4 vision pipeline.
Orchestrates all steps in the correct order with error handling.
"""

import uuid
import time
from typing import List
import io

from .utils import (
    base64_to_bytes,
    generate_image_id,
    get_image_metadata,
    load_image_from_base64,
    vlog
)
from .pile_segmenter import segment_pile_for_all_images
from .yolo_detector import detect_all_images
from .gating import apply_early_gating
from .item_segmenter import segment_all_proposals
from .lane_splitter import apply_lane_split
from .classifier import run_gpt_classifier, filter_by_verdict
from .fusion import fuse_across_images
from .remainder import compute_remainder_stats
from .volume_engine import compute_two_lane_volume
from .audit import run_gpt_audit
from .response_builder import build_response, build_error_response


def ingest_images(base64_images: List[str]) -> List[dict]:
    """
    Step 1: Ingest and normalize images.
    
    Args:
        base64_images: List of base64-encoded image strings
        
    Returns:
        List of image dicts with metadata
    """
    vlog(f"📥 Ingesting {len(base64_images)} images...")
    
    images = []
    for i, b64 in enumerate(base64_images):
        try:
            # Load and normalize image
            img = load_image_from_base64(b64)
            metadata = get_image_metadata(img)
            
            image_dict = {
                "image_id": generate_image_id(i),
                "index": i,
                "base64": b64,
                "width": metadata["width"],
                "height": metadata["height"],
                "aspect": metadata["aspect"],
            }
            images.append(image_dict)
            vlog(f"   ✅ Image {i+1}: {metadata['width']}x{metadata['height']}")
            
        except Exception as e:
            vlog(f"   ❌ Image {i+1} failed: {e}")
            continue
    
    return images


def process_quote_v4(base64_images: List[str], mode: str = "pile") -> dict:
    """
    v4.0 Vision Pipeline Main Entry Point
    
    Pipeline Order:
    1. Ingest & normalize images
    2. Lang-SAM pile segmentation (BEFORE YOLO)
    3. YOLO-World detection
    4. Early gating (bbox validation)
    5. Lang-SAM item segmentation (per proposal)
    6. Lane split (pile vs discrete)
    7. GPT classifier
    8. Cross-image fusion
    9. Remainder computation
    10. Two-lane volume calculation
    11. GPT audit
    12. Response builder
    
    Args:
        base64_images: List of base64-encoded image strings
        mode: Processing mode ("pile" or other)
        
    Returns:
        Complete quote response dict
    """
    request_id = uuid.uuid4().hex[:8]
    start_time = time.time()
    
    vlog("=" * 60)
    vlog(f"🚀 v4.0 PIPELINE START | request_id={request_id} | images={len(base64_images)}")
    vlog("=" * 60)
    
    try:
        # ================================================================
        # STEP 1: INGEST & NORMALIZE
        # ================================================================
        images = ingest_images(base64_images)
        
        if not images:
            return build_error_response(request_id, "No valid images to process", [])
        
        
        # ================================================================
        # STEP 2: PILE SEGMENTATION (BEFORE YOLO) ★ CRITICAL ORDER
        # ================================================================
        vlog("\n📍 Step 2: Pile Segmentation (Lang-SAM)")
        pile_masks = segment_pile_for_all_images(images)
        
        
        # ================================================================
        # STEP 3: YOLO-WORLD DETECTION
        # ================================================================
        vlog("\n📍 Step 3: YOLO-World Detection")
        all_proposals = detect_all_images(images)
        
        if not all_proposals:
            vlog("⚠️ No proposals from YOLO, using fallback")
            return build_error_response(request_id, "No objects detected", images)
        
        
        # ================================================================
        # STEP 4: EARLY GATING
        # ================================================================
        vlog("\n📍 Step 4: Early Gating")
        gated_proposals = apply_early_gating(all_proposals, images)
        
        if not gated_proposals:
            vlog("⚠️ All proposals filtered, using fallback")
            return build_error_response(request_id, "All proposals filtered", images)
        
        
        # ================================================================
        # STEP 5: ITEM SEGMENTATION (per proposal)
        # ================================================================
        vlog("\n📍 Step 5: Item Segmentation (Lang-SAM)")
        segmented_proposals = segment_all_proposals(gated_proposals, images, pile_masks)
        
        
        # ================================================================
        # STEP 6: LANE SPLIT
        # ================================================================
        vlog("\n📍 Step 6: Lane Split")
        discrete_items, pile_regions, dropped = apply_lane_split(segmented_proposals)
        
        if not discrete_items:
            vlog("⚠️ No discrete items after lane split, using pile-only estimation")
            # Even if no discrete items, we can compute from pile
        
        
        # ================================================================
        # STEP 7: GPT CLASSIFIER
        # ================================================================
        vlog("\n📍 Step 7: GPT Classifier")
        if discrete_items:
            classified_items = run_gpt_classifier(discrete_items)
            classified_items = filter_by_verdict(classified_items)
        else:
            classified_items = []
        
        
        # ================================================================
        # STEP 8: CROSS-IMAGE FUSION
        # ================================================================
        vlog("\n📍 Step 8: Cross-Image Fusion")
        fused_items = fuse_across_images(classified_items, images)
        
        
        # ================================================================
        # STEP 9: REMAINDER COMPUTATION
        # ================================================================
        vlog("\n📍 Step 9: Remainder Computation")
        remainder_stats = compute_remainder_stats(pile_masks, fused_items, images)
        
        
        # ================================================================
        # STEP 10: TWO-LANE VOLUME
        # ================================================================
        vlog("\n📍 Step 10: Two-Lane Volume")
        volumes = compute_two_lane_volume(fused_items, remainder_stats)
        
        
        # ================================================================
        # STEP 11: GPT AUDIT
        # ================================================================
        vlog("\n📍 Step 11: GPT Audit")
        trust_metrics = {
            "mask_coverage_pct": volumes.get("mask_coverage_pct", 0),
            "items_with_masks": volumes.get("items_with_masks", 0),
            "remainder_ratio": remainder_stats.get("avg_remainder_ratio", 0),
        }
        audit_result = run_gpt_audit(fused_items, volumes, trust_metrics)
        
        
        # ================================================================
        # STEP 12: BUILD RESPONSE
        # ================================================================
        vlog("\n📍 Step 12: Build Response")
        response = build_response(
            fused_items=fused_items,
            volumes=volumes,
            audit=audit_result,
            request_id=request_id,
            images=images
        )
        
        # Add timing
        elapsed = time.time() - start_time
        response["elapsed_seconds"] = round(elapsed, 2)
        
        vlog("=" * 60)
        vlog(f"✅ v4.0 PIPELINE COMPLETE | {elapsed:.2f}s | {len(fused_items)} items | {volumes['final_volume']} yd³")
        vlog("=" * 60)
        
        return response
        
    except Exception as e:
        elapsed = time.time() - start_time
        vlog(f"❌ PIPELINE FAILED after {elapsed:.2f}s: {e}")
        import traceback
        traceback.print_exc()
        return build_error_response(request_id, str(e), images if 'images' in dir() else [])
