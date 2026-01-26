"""
v4.0 Pile Segmenter (Step 2)

Runs Lang-SAM BEFORE YOLO to establish pile boundary.
Estimates pile area dynamically based on mask analysis.
"""

from typing import Optional
import io
import requests
from .constants import LANG_SAM_VERSION, PILE_PROMPTS
from .utils import base64_to_replicate_file, extract_replicate_url, vlog


def estimate_pile_ratio_from_mask(mask_url: str) -> float:
    """
    Download mask image and estimate pile coverage ratio.
    
    The mask is typically a black/white PNG where white = detected pile.
    We calculate: white_pixels / total_pixels = coverage ratio.
    
    Args:
        mask_url: URL to the mask image
        
    Returns:
        Estimated pile coverage ratio (0.0 to 1.0)
    """
    try:
        from PIL import Image
        
        # Download mask image
        response = requests.get(mask_url, timeout=10)
        response.raise_for_status()
        
        # Load as PIL image
        mask_img = Image.open(io.BytesIO(response.content))
        
        # Convert to grayscale
        mask_gray = mask_img.convert('L')
        
        # Count pixels
        total_pixels = mask_gray.width * mask_gray.height
        
        # Count white-ish pixels (above threshold 127)
        white_pixels = sum(1 for pixel in mask_gray.getdata() if pixel > 127)
        
        # Calculate ratio
        ratio = white_pixels / total_pixels if total_pixels > 0 else 0.0
        
        vlog(f"      Mask analysis: {white_pixels}/{total_pixels} pixels = {ratio*100:.1f}%")
        return ratio
        
    except Exception as e:
        vlog(f"      ⚠️ Mask analysis failed: {e}, using fallback")
        # Fallback to reasonable estimate
        return 0.55


def run_pile_segmentation(image: dict) -> dict:
    """
    Run Lang-SAM to get coarse pile boundary BEFORE item detection.
    
    Args:
        image: Dict with image_id, base64, width, height
        
    Returns:
        Dict with pile_mask_url, pile_area_ratio, success flag
    """
    import replicate
    
    vlog(f"🗻 Running pile segmentation for {image['image_id']}")
    
    try:
        # Create data URI for image
        img_data = base64_to_replicate_file(image["base64"])
        
        # Run Lang-SAM with pile-specific prompts
        output = replicate.run(
            LANG_SAM_VERSION,
            input={
                "image": img_data,
                "text_prompt": PILE_PROMPTS,
            }
        )
        
        # Parse mask URL
        mask_url = extract_replicate_url(output)
        
        if mask_url:
            vlog(f"   ✅ Pile mask obtained")
            
            # ACTUALLY analyze the mask to get real coverage
            pile_ratio = estimate_pile_ratio_from_mask(mask_url)
            
            # Apply minimum floor (if mask found, at least 30% coverage)
            pile_ratio = max(pile_ratio, 0.30)
            
            return {
                "success": True,
                "pile_mask_url": mask_url,
                "pile_area_ratio": round(pile_ratio, 3),
                "image_id": image["image_id"]
            }
        else:
            vlog(f"   ⚠️ No pile mask, using fallback estimate")
            # Fallback: assume moderate pile (better than 0)
            return {
                "success": False,
                "pile_mask_url": None,
                "pile_area_ratio": 0.40,  # Non-zero fallback
                "image_id": image["image_id"]
            }
            
    except Exception as e:
        vlog(f"   ❌ Pile segmentation error: {e}")
        return {
            "success": False,
            "pile_mask_url": None,
            "pile_area_ratio": 0.40,  # Non-zero fallback
            "image_id": image["image_id"],
            "error": str(e)
        }


def segment_pile_for_all_images(images: list) -> dict:
    """
    Run pile segmentation for all images.
    
    Returns:
        Dict mapping image_id -> pile segmentation result
    """
    pile_masks = {}
    
    for image in images:
        result = run_pile_segmentation(image)
        pile_masks[image["image_id"]] = result
    
    # Summary stats
    success_count = sum(1 for r in pile_masks.values() if r.get("success"))
    avg_ratio = sum(r.get("pile_area_ratio", 0) for r in pile_masks.values()) / len(images) if images else 0
    
    vlog(f"🗻 Pile segmentation: {success_count}/{len(images)} masks, avg coverage={avg_ratio*100:.1f}%")
    
    return pile_masks
