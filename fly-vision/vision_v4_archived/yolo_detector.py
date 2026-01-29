"""
v4.0 YOLO Detector (Step 3)

YOLO-World open-vocabulary detection.
Runs AFTER pile segmentation to find discrete item proposals.
"""

import json
from typing import List
from .constants import (
    YOLO_WORLD_VERSION, 
    YOLO_VOCAB_TIER_1, 
    YOLO_VOCAB_TIER_2, 
    YOLO_VOCAB_TIER_3,
    YOLO_VOCAB_ALL
)
from .utils import base64_to_replicate_file, generate_proposal_id, vlog


def run_yolo_detection(
    image: dict, 
    vocab: List[str], 
    conf_thresh: float = 0.25
) -> List[dict]:
    """
    Run YOLO-World open-vocab detection on a single image.
    
    Args:
        image: Dict with image_id, base64, width, height
        vocab: List of class names to detect
        conf_thresh: Confidence threshold
        
    Returns:
        List of proposal dicts with proposal_id, bbox, raw_label, score
    """
    import replicate  # Lazy import
    
    vlog(f"🎯 YOLO detecting {len(vocab)} classes (conf>{conf_thresh}) on {image['image_id']}")
    
    try:
        # Upload image to Replicate
        img_file = base64_to_replicate_file(image["base64"])
        
        # Build comma-separated class string
        classes_str = ", ".join(vocab)
        
        # Run YOLO-World
        output = replicate.run(
            YOLO_WORLD_VERSION,
            input={
                "input_media": img_file,
                "class_names": classes_str,
                "score_thr": conf_thresh,
                "return_json": True,
                "max_num_boxes": 100,
            }
        )
        
        # Parse json_str from output
        if not isinstance(output, dict) or "json_str" not in output:
            vlog(f"   ⚠️ Unexpected YOLO output format: {type(output)}")
            return []
        
        parsed = json.loads(output["json_str"])
        
        # Extract Det-* keys
        det_keys = [k for k in parsed.keys() if k.startswith("Det-")]
        
        if not det_keys:
            vlog(f"   ⚠️ YOLO found no detections")
            return []
        
        vlog(f"   🔍 YOLO raw: {len(det_keys)} detections")
        
        # Build proposals
        proposals = []
        for k in sorted(det_keys):
            det = parsed[k]
            
            # Extract bbox using franz-biz format: x0, y0, x1, y1
            if not all(key in det for key in ("x0", "y0", "x1", "y1")):
                continue
                
            bbox = [
                float(det["x0"]),
                float(det["y0"]),
                float(det["x1"]),
                float(det["y1"])
            ]
            
            # Extract label and score
            raw_label = (det.get("cls") or det.get("class") or det.get("label") or "").strip().lower()
            score = float(det.get("score") or det.get("confidence") or 0.0)
            
            # Generate proposal_id - THIS IS THE PRIMARY KEY
            proposal_id = generate_proposal_id(image["image_id"], bbox, raw_label)
            
            proposals.append({
                "proposal_id": proposal_id,  # PRIMARY KEY
                "image_id": image["image_id"],
                "bbox": bbox,
                "raw_label": raw_label,
                "score": score,
                # These will be set later in the pipeline
                "mask": None,
                "mask_url": None,
                "mask_area_ratio": None,
                "pile_overlap": None,
                "has_mask": False,
                "lane": None,
                "verdict": None,
                "canonical_label": None,
                "category": None,
                "size_bucket": None,
                "add_on_flags": [],
                "classifier_confidence": None,
            })
        
        vlog(f"   ✅ YOLO proposals: {len(proposals)}")
        return proposals
        
    except Exception as e:
        vlog(f"   ❌ YOLO detection failed: {e}")
        import traceback
        traceback.print_exc()
        return []


def run_tiered_yolo_detection(image: dict) -> List[dict]:
    """
    Run YOLO-World with tiered vocabulary for progressive detection.
    
    - Tier 1: Common junk items (always run)
    - Tier 2: Construction/yard items (if Tier 1 sparse)
    - Tier 3: Rare big-ticket items (if still sparse)
    
    Args:
        image: Dict with image_id, base64, width, height
        
    Returns:
        Combined list of proposals from all tiers
    """
    all_proposals = []
    
    # Tier 1: Always run
    tier1 = run_yolo_detection(image, YOLO_VOCAB_TIER_1, conf_thresh=0.25)
    all_proposals.extend(tier1)
    
    # Tier 2: If Tier 1 sparse
    if len(tier1) < 3:
        vlog(f"   📈 Tier 1 sparse ({len(tier1)}), adding Tier 2...")
        tier2 = run_yolo_detection(image, YOLO_VOCAB_TIER_2, conf_thresh=0.20)
        all_proposals.extend(tier2)
        
        # Tier 3: If still sparse
        if len(tier1) + len(tier2) < 5:
            vlog(f"   📈 Tier 2 sparse, adding Tier 3...")
            tier3 = run_yolo_detection(image, YOLO_VOCAB_TIER_3, conf_thresh=0.15)
            all_proposals.extend(tier3)
    
    vlog(f"🎯 YOLO total: {len(all_proposals)} proposals for {image['image_id']}")
    return all_proposals


def detect_all_images(images: list) -> List[dict]:
    """
    Run YOLO detection for all images.
    
    Args:
        images: List of image dicts
        
    Returns:
        Combined list of all proposals from all images
    """
    all_proposals = []
    
    for image in images:
        proposals = run_tiered_yolo_detection(image)
        all_proposals.extend(proposals)
    
    vlog(f"🎯 YOLO complete: {len(all_proposals)} total proposals from {len(images)} images")
    return all_proposals
