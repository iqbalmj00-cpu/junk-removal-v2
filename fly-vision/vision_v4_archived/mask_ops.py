"""
v4.0 Mask Operations (P4 Implementation)

Provides mask algebra for union-based subtraction.
Fixes clamp triggers caused by overlapping area percentages.

Key features:
- Request-scoped caching (prevents duplicate fetches)
- Bbox fallback masks (for items without mask_url)
- Union + intersection for correct subtraction
"""

from typing import List, Dict, Optional, Tuple
import numpy as np
from io import BytesIO
import requests
from PIL import Image

from .utils import vlog

# Feature flag
USE_UNION_MASKS = True

# Cache timeout for mask fetches
MASK_FETCH_TIMEOUT = 0.5  # seconds


def mask_from_bbox(
    bbox: List[float], 
    shape: Tuple[int, int],
    inner_factor: float = 0.8
) -> np.ndarray:
    """
    Create synthetic mask from bbox (conservative inner area).
    
    Args:
        bbox: [x1, y1, x2, y2] normalized coordinates (0-1)
        shape: (height, width) of target mask
        inner_factor: Shrink bbox by this factor (default 0.8 = 80% inner)
    
    Returns:
        Boolean mask array
    """
    h, w = shape
    x1, y1, x2, y2 = bbox
    
    # Convert normalized to pixel coordinates
    px1 = int(x1 * w)
    py1 = int(y1 * h)
    px2 = int(x2 * w)
    py2 = int(y2 * h)
    
    # Shrink to inner area (conservative)
    cx, cy = (px1 + px2) / 2, (py1 + py2) / 2
    bw, bh = px2 - px1, py2 - py1
    inner_w, inner_h = bw * inner_factor, bh * inner_factor
    
    px1 = int(cx - inner_w / 2)
    py1 = int(cy - inner_h / 2)
    px2 = int(cx + inner_w / 2)
    py2 = int(cy + inner_h / 2)
    
    # Clamp to image bounds
    px1 = max(0, min(px1, w - 1))
    py1 = max(0, min(py1, h - 1))
    px2 = max(0, min(px2, w))
    py2 = max(0, min(py2, h))
    
    mask = np.zeros((h, w), dtype=bool)
    mask[py1:py2, px1:px2] = True
    
    return mask


def fetch_mask(
    url: str, 
    cache: Dict[str, np.ndarray],
    timeout: float = MASK_FETCH_TIMEOUT
) -> Optional[np.ndarray]:
    """
    Fetch mask image from URL with caching and timeout.
    
    Args:
        url: URL to mask image
        cache: Request-scoped cache dict
        timeout: Fetch timeout in seconds
    
    Returns:
        Boolean mask array, or None if fetch fails
    """
    if not url:
        return None
    
    # Check cache first
    if url in cache:
        return cache[url]
    
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        
        # Decode image
        img = Image.open(BytesIO(response.content))
        
        # Convert to grayscale if needed
        if img.mode in ('RGBA', 'LA'):
            # Use alpha channel if present
            arr = np.array(img.split()[-1]) > 127
        elif img.mode == 'L':
            arr = np.array(img) > 127
        else:
            # Convert to grayscale
            arr = np.array(img.convert('L')) > 127
        
        cache[url] = arr
        return arr
        
    except Exception as e:
        vlog(f"   ⚠️ Mask fetch failed: {url[:50]}... ({e})")
        cache[url] = None  # Cache failure to avoid retry
        return None


def union_masks(masks: List[np.ndarray]) -> np.ndarray:
    """
    Compute union (OR) of multiple masks.
    
    Args:
        masks: List of boolean mask arrays (same shape)
    
    Returns:
        Union mask
    """
    if not masks:
        return np.array([[False]])
    
    result = masks[0].copy()
    for mask in masks[1:]:
        result = np.logical_or(result, mask)
    
    return result


def intersect_masks(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """
    Compute intersection (AND) of two masks.
    
    Args:
        a, b: Boolean mask arrays (same shape)
    
    Returns:
        Intersection mask
    """
    return np.logical_and(a, b)


def compute_area_ratio(mask: np.ndarray) -> float:
    """
    Compute area ratio (non-zero pixels / total pixels).
    
    Args:
        mask: Boolean mask array
    
    Returns:
        Ratio in range [0, 1]
    """
    total = mask.size
    if total == 0:
        return 0.0
    return np.sum(mask) / total


def compute_subtracted_area_per_image(
    fused_items: List[dict],
    pile_masks: dict,
    mask_cache: Dict[str, np.ndarray]
) -> Dict[str, dict]:
    """
    Compute per-image subtraction using union mask algebra.
    
    This is the core P4 fix: instead of summing percentage areas,
    we compute union of item masks and intersect with pile mask.
    
    Args:
        fused_items: List of fused items with owner_lane assignments
        pile_masks: Dict mapping image_id -> pile segmentation result
        mask_cache: Request-scoped cache for mask fetches
    
    Returns:
        Dict mapping image_id -> {pile_ratio, subtracted_ratio, residual_ratio}
    """
    results = {}
    
    # Group items by image
    items_by_image: Dict[str, List[dict]] = {}
    for item in fused_items:
        img_id = item.get("image_id", "unknown")
        if img_id not in items_by_image:
            items_by_image[img_id] = []
        items_by_image[img_id].append(item)
    
    for image_id, pile_result in pile_masks.items():
        pile_url = pile_result.get("pile_mask_url")
        pile_mask = fetch_mask(pile_url, mask_cache) if pile_url else None
        
        if pile_mask is None:
            # Fallback: use percentage-based subtraction
            pile_ratio = pile_result.get("pile_area_ratio", 0)
            results[image_id] = {
                "pile_ratio": pile_ratio,
                "subtracted_ratio": 0,
                "residual_ratio": pile_ratio,
                "fallback": True
            }
            continue
        
        image_shape = pile_mask.shape
        
        # Filter subtractable observations
        image_items = items_by_image.get(image_id, [])
        subtractable_obs = [
            i for i in image_items
            if i.get("owner_lane") in {"DISCRETE", "COUNTABLE", "UNCERTAIN_BLOB"}
            and i.get("ownership", "").endswith("SUBTRACTED")  # Only actually subtracted items
        ]
        
        # Build masks (real or bbox fallback)
        masks = []
        for obs in subtractable_obs:
            mask_url = obs.get("mask_url")
            bbox = obs.get("bbox")
            
            if mask_url:
                mask = fetch_mask(mask_url, mask_cache)
                if mask is not None:
                    # Ensure same shape
                    if mask.shape != image_shape:
                        # Resize mask to match pile
                        from PIL import Image
                        mask_img = Image.fromarray(mask.astype(np.uint8) * 255)
                        mask_img = mask_img.resize((image_shape[1], image_shape[0]), Image.NEAREST)
                        mask = np.array(mask_img) > 127
                    masks.append(mask)
            elif bbox and len(bbox) == 4:
                # Bbox fallback
                mask = mask_from_bbox(bbox, image_shape)
                masks.append(mask)
        
        # Compute union and intersection
        if masks:
            union = union_masks(masks)
            subtracted = intersect_masks(union, pile_mask)
            subtracted_ratio = compute_area_ratio(subtracted)
        else:
            subtracted_ratio = 0
        
        pile_ratio = compute_area_ratio(pile_mask)
        residual_ratio = max(0, pile_ratio - subtracted_ratio)
        
        results[image_id] = {
            "pile_ratio": pile_ratio,
            "subtracted_ratio": subtracted_ratio,
            "residual_ratio": residual_ratio,
            "mask_count": len(masks),
            "fallback": False
        }
        
        vlog(f"   📐 [{image_id}] pile={pile_ratio:.1%} - sub={subtracted_ratio:.1%} = res={residual_ratio:.1%} ({len(masks)} masks)")
    
    return results
