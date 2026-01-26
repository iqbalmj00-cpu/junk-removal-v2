"""
v4.0 Pile Segmenter (Step 2)

Runs Lang-SAM BEFORE YOLO to establish pile boundary.
This is critical for stable remainder mask computation.
"""

from typing import Optional
from .constants import LANG_SAM_VERSION, PILE_PROMPTS
from .utils import base64_to_replicate_file, extract_replicate_url, vlog


def run_pile_segmentation(image: dict) -> dict:
    """
    Run Lang-SAM to get coarse pile boundary BEFORE item detection.
    
    This is Step 2 in the pipeline and must run BEFORE YOLO.
    The pile mask establishes the overall debris region, which is later
    used to compute pile_overlap for lane splitting.
    
    Args:
        image: Dict with image_id, base64, width, height
        
    Returns:
        Dict with pile_mask_url, pile_area_ratio, success flag
    """
    import replicate  # Lazy import
    
    vlog(f"🗻 Running pile segmentation for {image['image_id']}")
    
    try:
        # Upload image to Replicate
        img_file = base64_to_replicate_file(image["base64"])
        
        # Run Lang-SAM with pile-specific prompts
        output = replicate.run(
            LANG_SAM_VERSION,
            input={
                "image": img_file,
                "text_prompt": PILE_PROMPTS,
            }
        )
        
        # Parse output using robust helper
        mask_url = extract_replicate_url(output)
        vlog(f"   DEBUG: output type={type(output)}, extracted={mask_url is not None}")
        
        if mask_url:
            vlog(f"   ✅ Pile mask obtained: {mask_url[:60]}...")
            
            # Estimate pile area ratio from mask (rough estimate based on typical results)
            # In production, we'd download and analyze the mask image
            # For now, assume pile covers ~40-60% of image
            estimated_pile_ratio = 0.50
            
            return {
                "success": True,
                "pile_mask_url": mask_url,
                "pile_area_ratio": estimated_pile_ratio,
                "image_id": image["image_id"]
            }
        else:
            vlog(f"   ⚠️ Pile segmentation returned no mask")
            return {
                "success": False,
                "pile_mask_url": None,
                "pile_area_ratio": 0.0,
                "image_id": image["image_id"]
            }
            
    except Exception as e:
        vlog(f"   ❌ Pile segmentation failed: {e}")
        return {
            "success": False,
            "pile_mask_url": None,
            "pile_area_ratio": 0.0,
            "image_id": image["image_id"],
            "error": str(e)
        }


def segment_pile_for_all_images(images: list) -> dict:
    """
    Run pile segmentation for all images.
    
    Args:
        images: List of image dicts
        
    Returns:
        Dict mapping image_id -> pile segmentation result
    """
    pile_masks = {}
    
    for image in images:
        result = run_pile_segmentation(image)
        pile_masks[image["image_id"]] = result
    
    success_count = sum(1 for r in pile_masks.values() if r.get("success"))
    vlog(f"🗻 Pile segmentation complete: {success_count}/{len(images)} successful")
    
    return pile_masks
