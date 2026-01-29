"""
v4.0 Early Gating (Step 4)

Bbox validation and early filtering of proposals.
Only rejects truly degenerate bboxes - keeps big boxes as pile candidates.
"""

import math
from typing import List, Tuple
from .constants import MIN_CONFIDENCE
from .utils import vlog


def validate_bbox(bbox: list, image_width: int, image_height: int) -> Tuple[bool, str]:
    """
    Validate a bounding box.
    
    CORRECTED LOGIC:
    - Only reject truly degenerate bboxes
    - Big boxes are KEPT (they become pile candidates)
    - Do NOT reject based on size alone
    
    Args:
        bbox: [x0, y0, x1, y1]
        image_width: Image width in pixels
        image_height: Image height in pixels
        
    Returns:
        Tuple of (is_valid, rejection_reason)
    """
    x0, y0, x1, y1 = bbox
    w = x1 - x0
    h = y1 - y0
    
    # Rule 1: Degenerate dimensions (too small to be meaningful)
    if w < 2 or h < 2:
        return False, "degenerate_dimensions"
    
    # Rule 2: NaN values
    if any(math.isnan(v) for v in bbox):
        return False, "nan_values"
    
    # Rule 3: Completely outside image bounds (no overlap at all)
    if x1 <= 0 or y1 <= 0 or x0 >= image_width or y0 >= image_height:
        return False, "outside_bounds"
    
    # Rule 4: Negative dimensions (inverted bbox)
    if x1 < x0 or y1 < y0:
        return False, "inverted_bbox"
    
    # IMPORTANT: Big boxes are VALID
    # They will be classified as pile candidates in lane_splitter
    # Do NOT reject based on size here
    
    return True, None


def validate_proposal(proposal: dict, image: dict) -> Tuple[bool, str]:
    """
    Validate a complete proposal including bbox and score.
    
    Args:
        proposal: Proposal dict with bbox, score, etc.
        image: Image dict with width, height
        
    Returns:
        Tuple of (is_valid, rejection_reason)
    """
    # Validate bbox
    is_valid, reason = validate_bbox(
        proposal["bbox"], 
        image["width"], 
        image["height"]
    )
    
    if not is_valid:
        return False, reason
    
    # Rule: Extremely low confidence (noise)
    if proposal["score"] < MIN_CONFIDENCE:
        return False, "extremely_low_confidence"
    
    return True, None


def apply_early_gating(proposals: List[dict], images: List[dict]) -> List[dict]:
    """
    Apply early gating to filter obviously invalid proposals.
    
    Args:
        proposals: List of proposal dicts
        images: List of image dicts
        
    Returns:
        Filtered list of valid proposals
    """
    # Build image lookup by image_id
    image_map = {img["image_id"]: img for img in images}
    
    valid_proposals = []
    rejected = {"degenerate_dimensions": 0, "nan_values": 0, "outside_bounds": 0, 
                "inverted_bbox": 0, "extremely_low_confidence": 0, "unknown_image": 0}
    
    for proposal in proposals:
        image = image_map.get(proposal["image_id"])
        
        if not image:
            rejected["unknown_image"] += 1
            continue
        
        is_valid, reason = validate_proposal(proposal, image)
        
        if is_valid:
            valid_proposals.append(proposal)
        else:
            rejected[reason] = rejected.get(reason, 0) + 1
            vlog(f"   ⛔ Gating rejected: {proposal['raw_label']} - {reason}")
    
    # Log summary
    total_rejected = sum(rejected.values())
    if total_rejected > 0:
        vlog(f"🚦 Early gating: {len(valid_proposals)} passed, {total_rejected} rejected")
        for reason, count in rejected.items():
            if count > 0:
                vlog(f"      - {reason}: {count}")
    else:
        vlog(f"🚦 Early gating: all {len(valid_proposals)} proposals passed")
    
    return valid_proposals
