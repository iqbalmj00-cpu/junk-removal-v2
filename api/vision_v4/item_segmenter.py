"""
v4.0 Item Segmenter (Step 5)

Optimized segmentation strategy:
- Skip segmentation for pile-like labels (save API calls)
- Only segment high-value discrete items
- Always fallback to bbox area if mask fails
"""

from typing import List
from .constants import LANG_SAM_VERSION, PILE_LABELS
from .utils import base64_to_replicate_file, bbox_area_ratio, extract_replicate_url, vlog


# Labels that DON'T need per-item segmentation (use bbox fallback)
SKIP_SEGMENTATION_LABELS = PILE_LABELS | {
    "debris", "junk", "trash", "garbage", "clutter",
    "wood debris", "metal scrap", "branches", "leaves"
}

# Minimum bbox area ratio to bother segmenting (skip tiny items)
MIN_AREA_FOR_SEGMENTATION = 0.01  # 1% of image


def should_segment_item(proposal: dict, image: dict) -> bool:
    """
    Determine if an item should go through Lang-SAM or just use bbox fallback.
    
    Skip segmentation for:
    - Pile-like labels (yard waste, debris pile, etc.)
    - Very small items (< 1% of image)
    - Low confidence detections (< 0.20)
    """
    label = proposal.get("raw_label", "").lower()
    score = proposal.get("score", 0)
    
    # Skip pile-like labels
    if label in SKIP_SEGMENTATION_LABELS:
        return False
    
    # Skip low confidence
    if score < 0.20:
        return False
    
    # Check min area
    bbox = proposal.get("bbox", [0, 0, 0, 0])
    area_ratio = bbox_area_ratio(bbox, image["width"], image["height"])
    if area_ratio < MIN_AREA_FOR_SEGMENTATION:
        return False
    
    return True


def run_item_segmentation(
    proposal: dict, 
    image: dict, 
    pile_mask_url: str = None
) -> dict:
    """
    Run Lang-SAM for a single proposal.
    Returns mask info with area ratio always computed (fallback to bbox).
    """
    import replicate  # Lazy import
    
    bbox = proposal.get("bbox", [0, 0, 0, 0])
    bbox_area = bbox_area_ratio(bbox, image["width"], image["height"])
    
    vlog(f"   🎭 Segmenting: {proposal['raw_label']} ({proposal['proposal_id'][:8]}...)")
    
    try:
        # Create data URI for image
        img_data = base64_to_replicate_file(image["base64"])
        
        # Run Lang-SAM
        output = replicate.run(
            LANG_SAM_VERSION,
            input={
                "image": img_data,
                "text_prompt": proposal["raw_label"],
            }
        )
        
        # Parse mask URL
        mask_url = extract_replicate_url(output)
        
        if mask_url:
            vlog(f"      ✅ Mask obtained")
            return {
                "mask_url": mask_url,
                "mask_area_ratio": bbox_area,  # Use bbox as proxy
                "pile_overlap": 0.3 if pile_mask_url else 0.0,
                "has_mask": True,
                "success": True
            }
        else:
            # Mask failed - use bbox fallback
            vlog(f"      ⚠️ No mask, using bbox fallback")
            return {
                "mask_url": None,
                "mask_area_ratio": bbox_area,  # ALWAYS use bbox as fallback
                "pile_overlap": 0.0,
                "has_mask": False,
                "success": False
            }
            
    except Exception as e:
        vlog(f"      ❌ Segmentation error: {e}")
        # Fallback to bbox area - NEVER return 0
        return {
            "mask_url": None,
            "mask_area_ratio": bbox_area,  # ALWAYS fallback
            "pile_overlap": 0.0,
            "has_mask": False,
            "success": False,
            "error": str(e)
        }


def segment_all_proposals(
    proposals: List[dict], 
    images: List[dict], 
    pile_masks: dict
) -> List[dict]:
    """
    Run item segmentation for proposals that need it.
    Skip pile-like labels to save API calls.
    """
    image_map = {img["image_id"]: img for img in images}
    
    success_count = 0
    skipped_count = 0
    
    for proposal in proposals:
        image = image_map.get(proposal["image_id"])
        if not image:
            continue
        
        # Get pile mask URL for this image
        pile_result = pile_masks.get(proposal["image_id"], {})
        pile_mask_url = pile_result.get("pile_mask_url")
        
        # Decide: segment or skip?
        if should_segment_item(proposal, image):
            # Run segmentation
            seg_result = run_item_segmentation(proposal, image, pile_mask_url)
            if seg_result.get("success"):
                success_count += 1
        else:
            # Skip segmentation - use bbox directly
            skipped_count += 1
            bbox = proposal.get("bbox", [0, 0, 0, 0])
            seg_result = {
                "mask_url": None,
                "mask_area_ratio": bbox_area_ratio(bbox, image["width"], image["height"]),
                "pile_overlap": 0.5,  # Assume high overlap for pile-like items
                "has_mask": False,
                "success": False
            }
        
        # Attach results
        proposal["mask_url"] = seg_result.get("mask_url")
        proposal["mask_area_ratio"] = seg_result.get("mask_area_ratio", 0)
        proposal["pile_overlap"] = seg_result.get("pile_overlap", 0)
        proposal["has_mask"] = seg_result.get("has_mask", False)
    
    vlog(f"🎭 Item segmentation: {success_count} masks, {skipped_count} skipped, {len(proposals)} total")
    return proposals
