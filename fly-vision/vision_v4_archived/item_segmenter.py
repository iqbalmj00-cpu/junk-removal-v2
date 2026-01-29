"""
v4.0 Item Segmenter (Step 5)

Optimized segmentation strategy:
- STABLE MULTI-KEY SORT for deterministic selection
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

# High-value discrete items that should be prioritized for segmentation
HIGH_VALUE_ITEMS = {
    "couch", "sofa", "mattress", "refrigerator", "freezer",
    "washer", "dryer", "exercise equipment", "treadmill", "scooter",
    "hot tub", "piano", "pool table", "safe", "motorcycle"
}


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


def get_stable_sort_key(proposal: dict, image_map: dict) -> tuple:
    """
    Generate a DETERMINISTIC sort key for proposal selection.
    
    Key order:
    1. High-value item bonus (discrete items get priority)
    2. Confidence score (descending)
    3. Bbox area (descending)
    4. Class name (alphabetical)
    5. Bbox coordinates (x1, y1) for determinism
    6. Image index for cross-image stability
    """
    img = image_map.get(proposal["image_id"], {})
    label = proposal.get("raw_label", "").lower()
    score = proposal.get("score", 0.5)
    bbox = proposal.get("bbox", [0, 0, 0, 0])
    
    # Compute area
    width = img.get("width", 1)
    height = img.get("height", 1)
    area = bbox_area_ratio(bbox, width, height)
    
    # High-value items get priority bonus
    is_high_value = 1 if any(hv in label for hv in HIGH_VALUE_ITEMS) else 0
    
    # Image index for stability
    image_index = img.get("index", 0)
    
    return (
        -is_high_value,     # High-value items first (negative for descending)
        -score,              # Higher confidence first
        -area,               # Larger items first
        label,               # Alphabetical tie-break
        bbox[0],             # X1 coordinate
        bbox[1],             # Y1 coordinate
        image_index,         # Image order
        proposal.get("proposal_id", "")  # Final tie-break on ID
    )


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
    Run item segmentation for TOP proposals only.
    
    P3: Uses PER-IMAGE budget instead of overall top-N.
    This ensures each view contributes consistently regardless of upload order.
    """
    image_map = {img["image_id"]: img for img in images}
    
    # P3: Per-image segmentation budget
    # k=2 per image ensures consistent contribution from each view
    SEGMENTS_PER_IMAGE = 2
    
    # Separate items that need segmentation
    segmentable = [p for p in proposals if should_segment_item(p, image_map.get(p["image_id"], {}))]
    non_segmentable = [p for p in proposals if not should_segment_item(p, image_map.get(p["image_id"], {}))]
    
    # P3: Group by image and select top-k from each
    from collections import defaultdict
    by_image = defaultdict(list)
    for p in segmentable:
        by_image[p["image_id"]].append(p)
    
    to_segment = []
    to_skip = []
    
    for img_id, img_proposals in by_image.items():
        # STABLE MULTI-KEY SORT within each image
        sorted_proposals = sorted(
            img_proposals,
            key=lambda p: get_stable_sort_key(p, image_map)
        )
        
        # Take top-k from this image
        to_segment.extend(sorted_proposals[:SEGMENTS_PER_IMAGE])
        to_skip.extend(sorted_proposals[SEGMENTS_PER_IMAGE:])
    
    vlog(f"🎭 P3: Segmenting {len(to_segment)} items ({SEGMENTS_PER_IMAGE}/image × {len(images)} images)")
    
    success_count = 0
    
    # Segment top priority items
    for proposal in to_segment:
        image = image_map.get(proposal["image_id"])
        if not image:
            continue
        
        pile_result = pile_masks.get(proposal["image_id"], {})
        pile_mask_url = pile_result.get("pile_mask_url")
        
        seg_result = run_item_segmentation(proposal, image, pile_mask_url)
        if seg_result.get("success"):
            success_count += 1
        
        # Attach results
        proposal["mask_url"] = seg_result.get("mask_url")
        proposal["mask_area_ratio"] = seg_result.get("mask_area_ratio", 0)
        proposal["pile_overlap"] = seg_result.get("pile_overlap", 0)
        proposal["has_mask"] = seg_result.get("has_mask", False)
    
    # Use bbox fallback for remaining items (both skipped and over-limit)
    for proposal in to_skip + non_segmentable:
        image = image_map.get(proposal["image_id"])
        if not image:
            continue
        
        bbox = proposal.get("bbox", [0, 0, 0, 0])
        proposal["mask_url"] = None
        proposal["mask_area_ratio"] = bbox_area_ratio(bbox, image["width"], image["height"])
        proposal["pile_overlap"] = 0.5 if proposal in non_segmentable else 0.0
        proposal["has_mask"] = False
    
    vlog(f"🎭 Item segmentation: {success_count} masks, {len(to_skip) + len(non_segmentable)} bbox-fallback")
    return proposals
