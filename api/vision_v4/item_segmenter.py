"""
v4.0 Item Segmenter (Step 5)

Lang-SAM per-item segmentation with direct bbox ownership.
Each proposal gets its OWN Lang-SAM call - no global mask pool matching.
"""

from typing import List
from .constants import LANG_SAM_VERSION
from .utils import base64_to_replicate_file, bbox_area_ratio, extract_replicate_url, vlog


def run_item_segmentation(
    proposal: dict, 
    image: dict, 
    pile_mask_url: str = None
) -> dict:
    """
    Run Lang-SAM for a single proposal using its label.
    
    CORRECTED LOGIC:
    - Each proposal gets its OWN Lang-SAM call
    - Mask is OWNED by this proposal directly
    - No label matching, no IoU matching across global pool
    
    Args:
        proposal: Proposal dict with raw_label, bbox
        image: Image dict with base64, width, height
        pile_mask_url: Optional URL to pile mask for overlap computation
        
    Returns:
        Dict with mask_url, mask_area_ratio, pile_overlap, has_mask
    """
    import replicate  # Lazy import
    
    vlog(f"   🎭 Segmenting: {proposal['raw_label']} ({proposal['proposal_id'][:8]}...)")
    
    try:
        # Upload image to Replicate
        img_file = base64_to_replicate_file(image["base64"])
        
        # Use proposal's label as prompt
        text_prompt = proposal["raw_label"]
        
        # Run Lang-SAM
        output = replicate.run(
            LANG_SAM_VERSION,
            input={
                "image": img_file,
                "text_prompt": text_prompt,
            }
        )
        
        # Parse mask URL using robust helper
        mask_url = extract_replicate_url(output)
        
        if mask_url:
            # Calculate mask area ratio
            # In production, we'd download and analyze the mask
            # For now, estimate based on bbox
            bbox = proposal["bbox"]
            area_ratio = bbox_area_ratio(bbox, image["width"], image["height"])
            
            # Estimate pile overlap (would require actual mask analysis)
            pile_overlap = 0.3 if pile_mask_url else 0.0
            
            return {
                "mask_url": mask_url,
                "mask_area_ratio": area_ratio,
                "pile_overlap": pile_overlap,
                "has_mask": True,
                "success": True
            }
        else:
            # Fallback: estimate from bbox
            bbox = proposal["bbox"]
            area_ratio = bbox_area_ratio(bbox, image["width"], image["height"])
            
            return {
                "mask_url": None,
                "mask_area_ratio": area_ratio,
                "pile_overlap": 0.0,
                "has_mask": False,
                "success": False
            }
            
    except Exception as e:
        vlog(f"      ⚠️ Segmentation failed: {e}")
        # Fallback to bbox-based estimation
        bbox = proposal["bbox"]
        area_ratio = bbox_area_ratio(bbox, image["width"], image["height"])
        
        return {
            "mask_url": None,
            "mask_area_ratio": area_ratio,
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
    Run item segmentation for all proposals.
    
    Args:
        proposals: List of proposal dicts
        images: List of image dicts
        pile_masks: Dict mapping image_id -> pile segmentation result
        
    Returns:
        Updated proposals with mask information attached
    """
    # Build image lookup
    image_map = {img["image_id"]: img for img in images}
    
    success_count = 0
    
    for proposal in proposals:
        image = image_map.get(proposal["image_id"])
        if not image:
            continue
        
        # Get pile mask URL for this image
        pile_result = pile_masks.get(proposal["image_id"], {})
        pile_mask_url = pile_result.get("pile_mask_url")
        
        # Run segmentation
        seg_result = run_item_segmentation(proposal, image, pile_mask_url)
        
        # Attach results directly to proposal (OWNERSHIP)
        proposal["mask_url"] = seg_result.get("mask_url")
        proposal["mask_area_ratio"] = seg_result.get("mask_area_ratio", 0)
        proposal["pile_overlap"] = seg_result.get("pile_overlap", 0)
        proposal["has_mask"] = seg_result.get("has_mask", False)
        
        if seg_result.get("success"):
            success_count += 1
    
    vlog(f"🎭 Item segmentation complete: {success_count}/{len(proposals)} successful")
    return proposals
