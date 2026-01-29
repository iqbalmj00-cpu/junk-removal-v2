"""
v4.0 Lane Splitter (Step 6)

Classifies proposals into Pile vs Discrete Item lanes.
Pile regions are not billable - they contribute to remainder.
Discrete items go through classifier for pricing.
"""

from typing import List, Tuple
from .constants import (
    PILE_AREA_THRESHOLD,
    NOISE_AREA_THRESHOLD,
    PILE_OVERLAP_HIGH,
    PILE_LABELS
)
from .utils import vlog


def classify_lane(proposal: dict) -> str:
    """
    Assign proposal to a lane category.
    
    Lane Categories:
    - PILE_PROMPT_ONLY: Large regions or pile-like labels (not billable)
    - DROP_NOISE: Tiny detections that are just noise
    - DISCRETE_ITEM: Normal items for classification and pricing
    
    Args:
        proposal: Proposal dict with mask_area_ratio, raw_label, etc.
        
    Returns:
        Lane classification string
    """
    area_ratio = proposal.get("mask_area_ratio") or 0
    label = proposal.get("raw_label", "").lower()
    score = proposal.get("score", 0)
    pile_overlap = proposal.get("pile_overlap", 0)
    
    # Rule 1: Huge mask = pile region (not billable discrete item)
    if area_ratio > PILE_AREA_THRESHOLD:
        return "PILE_PROMPT_ONLY"
    
    # Rule 2: Pile-like labels are not billable discrete items
    if label in PILE_LABELS:
        return "PILE_PROMPT_ONLY"
    
    # Rule 3: Tiny mask = noise, drop
    if area_ratio < NOISE_AREA_THRESHOLD:
        return "DROP_NOISE"
    
    # Rule 4: High pile overlap + low confidence = likely pile remnant
    if pile_overlap > PILE_OVERLAP_HIGH and score < 0.35:
        return "PILE_PROMPT_ONLY"
    
    # Default: discrete item candidate for classification
    return "DISCRETE_ITEM"


def apply_lane_split(proposals: List[dict]) -> Tuple[List[dict], List[dict], List[dict]]:
    """
    Split proposals into lanes.
    
    Args:
        proposals: List of proposal dicts with mask info attached
        
    Returns:
        Tuple of (discrete_items, pile_regions, dropped_noise)
    """
    discrete_items = []
    pile_regions = []
    dropped_noise = []
    
    for proposal in proposals:
        lane = classify_lane(proposal)
        proposal["lane"] = lane  # Record the classification
        
        if lane == "DISCRETE_ITEM":
            discrete_items.append(proposal)
        elif lane == "PILE_PROMPT_ONLY":
            pile_regions.append(proposal)
        elif lane == "DROP_NOISE":
            dropped_noise.append(proposal)
    
    # Log summary
    vlog(f"🔀 Lane split results:")
    vlog(f"   - Discrete items: {len(discrete_items)} (→ classifier)")
    vlog(f"   - Pile regions: {len(pile_regions)} (→ remainder)")
    vlog(f"   - Dropped noise: {len(dropped_noise)}")
    
    # Log some examples
    if discrete_items:
        examples = discrete_items[:3]
        labels = [p["raw_label"] for p in examples]
        vlog(f"   - Discrete examples: {', '.join(labels)}")
    
    if pile_regions:
        examples = pile_regions[:2]
        labels = [p["raw_label"] for p in examples]
        vlog(f"   - Pile examples: {', '.join(labels)}")
    
    return discrete_items, pile_regions, dropped_noise
