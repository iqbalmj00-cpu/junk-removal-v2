"""
v4.0 Lane Splitter (Step 6)

Classifies proposals into Pile vs Discrete Item lanes.
Uses ALLOWLIST for pile regions - all other items default to DISCRETE.

Key principle: Only known pile-type classes route to pile_region.
"""

from typing import List, Tuple
from .constants import (
    PILE_AREA_THRESHOLD,
    NOISE_AREA_THRESHOLD,
    PILE_OVERLAP_HIGH,
)
from .utils import vlog


# ==============================================================================
# PILE REGION ALLOWLIST (STRICT)
# Only these classes can be routed to pile_region lane
# ==============================================================================

PILE_REGION_ALLOWLIST = {
    # Explicit pile/debris labels
    "yard waste", "debris pile", "debris", "trash pile",
    "clutter", "junk pile", "mixed debris", "garbage pile",
    "construction debris", "wood scraps", "brush", "leaves",
    "soil", "mulch", "dirt", "gravel", "rocks",
    
    # Bulk materials (not discrete items)
    "wood debris", "metal scrap", "branches", "lumber pile",
}

# ==============================================================================
# DISCRETE ITEMS (NEVER route to pile_region)
# These are billable discrete items even if they overlap with pile
# ==============================================================================

DISCRETE_FORCE_LIST = {
    # Furniture
    "couch", "sofa", "mattress", "chair", "table", "dresser", "desk",
    
    # Appliances
    "refrigerator", "freezer", "washer", "dryer", "dishwasher",
    
    # Electronics
    "tv", "monitor", "speaker", "subwoofer",
    
    # Equipment
    "exercise equipment", "treadmill", "scooter", "motorcycle",
    "piano", "hot tub", "pool table", "safe",
    
    # Containers (billable by quantity)
    "cardboard box", "plastic storage tote", "plastic bin", "tote",
    "garbage bag", "trash bag", "tire",
}


def classify_lane(proposal: dict) -> str:
    """
    Assign proposal to a lane category.
    
    Lane Categories:
    - PILE_PROMPT_ONLY: Allowlisted pile-type labels (not billable)
    - DROP_NOISE: Tiny detections that are just noise
    - DISCRETE_ITEM: All other items (default for pricing)
    
    Uses ALLOWLIST approach: only known pile labels go to pile lane.
    """
    area_ratio = proposal.get("mask_area_ratio") or 0
    label = proposal.get("raw_label", "").lower()
    score = proposal.get("score", 0)
    pile_overlap = proposal.get("pile_overlap", 0)
    
    # Rule 1: Tiny mask = noise, drop
    if area_ratio < NOISE_AREA_THRESHOLD:
        return "DROP_NOISE"
    
    # Rule 2: Force discrete items to DISCRETE lane (NEVER pile)
    if any(d in label for d in DISCRETE_FORCE_LIST) or label in DISCRETE_FORCE_LIST:
        return "DISCRETE_ITEM"
    
    # Rule 3: Only allowlisted labels can be pile regions
    if label in PILE_REGION_ALLOWLIST:
        return "PILE_PROMPT_ONLY"
    
    # Rule 4: Very large area (>45%) AND high pile overlap → likely pile constituent
    if area_ratio > PILE_AREA_THRESHOLD and pile_overlap > PILE_OVERLAP_HIGH:
        return "PILE_PROMPT_ONLY"
    
    # Default: DISCRETE (all unknown items are billable)
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
        proposal["lane_reason"] = "default_discrete"  # For debugging
        
        if lane == "DISCRETE_ITEM":
            discrete_items.append(proposal)
            label = proposal.get("raw_label", "").lower()
            if any(d in label for d in DISCRETE_FORCE_LIST):
                proposal["lane_reason"] = "forced_discrete"
            else:
                proposal["lane_reason"] = "default_discrete"
                
        elif lane == "PILE_PROMPT_ONLY":
            pile_regions.append(proposal)
            proposal["lane_reason"] = "pile_allowlist" if proposal.get("raw_label", "").lower() in PILE_REGION_ALLOWLIST else "large_area_overlap"
            
        elif lane == "DROP_NOISE":
            dropped_noise.append(proposal)
            proposal["lane_reason"] = "noise_too_small"
    
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
