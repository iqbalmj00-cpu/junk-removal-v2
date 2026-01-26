"""
v4.0 Cross-Image Fusion (Step 8)

Deduplicates items appearing in multiple images.
Uses "KEEP IF SEEN" policy with deterministic duplicate resolution.

Key principles:
1. Any item with conf >= KEEP_THRESHOLD survives to dedup phase
2. Only drop if PROVEN duplicate of another survivor
3. Deterministic tie-break for consistent results
"""

from typing import List
from .utils import normalize_bbox_center, vlog


# Minimum confidence to keep an item (lower = more permissive)
KEEP_THRESHOLD = 0.30

# Position bucket grid size (5x5 = 25 buckets)
POSITION_GRID = 5


def get_fusion_sort_key(item: dict) -> tuple:
    """
    Deterministic sort key for fusion tie-breaking.
    
    Order of priority:
    1. Has mask (True > False)
    2. Classifier confidence (higher > lower)
    3. YOLO score (higher > lower)
    4. Mask area (larger > smaller)
    5. Image index (earlier > later)
    6. Proposal ID (alphabetical)
    """
    return (
        -int(item.get("has_mask", False)),      # Has mask first (negative = descending)
        -item.get("classifier_confidence", 0),   # Higher confidence first
        -item.get("score", 0),                   # Higher YOLO score first
        -item.get("mask_area_ratio", 0),         # Larger area first
        item.get("image_id", ""),                # Earlier image first (alphabetical)
        item.get("proposal_id", "")              # Final tie-break
    )


def fuse_across_images(classified_items: List[dict], images: List[dict]) -> List[dict]:
    """
    Deduplicate items with KEEP-IF-SEEN policy.
    
    Phase 1: Retain all items with conf >= KEEP_THRESHOLD
    Phase 2: Only drop proven duplicates with deterministic tie-break
    
    Args:
        classified_items: List of classified proposal dicts
        images: List of image dicts for dimension lookup
        
    Returns:
        Deduplicated list of fused items
    """
    if not classified_items:
        return []
    
    vlog(f"🔗 Fusing {len(classified_items)} items across {len(images)} images...")
    
    # Build image dimension lookup
    image_dims = {img["image_id"]: (img["width"], img["height"]) for img in images}
    
    # ===========================================================================
    # PHASE 1: RETENTION - Keep all items meeting threshold
    # ===========================================================================
    
    retained = []
    dropped_low_conf = []
    
    for item in classified_items:
        conf = item.get("classifier_confidence", item.get("score", 0))
        
        if conf >= KEEP_THRESHOLD:
            retained.append(item)
        else:
            dropped_low_conf.append(item)
            item["drop_reason"] = "low_confidence"
    
    if dropped_low_conf:
        vlog(f"   🔻 Dropped {len(dropped_low_conf)} items below conf threshold ({KEEP_THRESHOLD})")
    
    # ===========================================================================
    # PHASE 2: DEDUPLICATION - Only drop proven duplicates
    # ===========================================================================
    
    # Sort retained items by fusion priority for deterministic selection
    retained_sorted = sorted(retained, key=get_fusion_sort_key)
    
    # Fusion map: track_key -> best item (first seen after sort = best)
    fused = {}
    duplicates = []
    
    for item in retained_sorted:
        # Get image dimensions
        dims = image_dims.get(item["image_id"], (1, 1))
        img_w, img_h = dims
        
        # Normalize bbox center to 0-1 range
        norm_x, norm_y = normalize_bbox_center(item["bbox"], img_w, img_h)
        
        # Create track key: label + position bucket
        pos_bucket_x = int(norm_x * POSITION_GRID)
        pos_bucket_y = int(norm_y * POSITION_GRID)
        track_key = f"{item['canonical_label']}_{pos_bucket_x}_{pos_bucket_y}"
        
        if track_key not in fused:
            # First occurrence - keep it
            fused[track_key] = item
            item["duplicate_of"] = None
        else:
            # Duplicate detected - mark and track
            existing = fused[track_key]
            item["duplicate_of"] = existing.get("proposal_id", "unknown")
            item["drop_reason"] = "duplicate"
            duplicates.append(item)
    
    fused_items = list(fused.values())
    
    # ===========================================================================
    # LOGGING
    # ===========================================================================
    
    reduction = len(classified_items) - len(fused_items)
    if reduction > 0:
        vlog(f"   ✅ Fused: {len(classified_items)} → {len(fused_items)} ({reduction} duplicates removed)")
    else:
        vlog(f"   ✅ No duplicates found, {len(fused_items)} unique items")
    
    # Log fused items
    for item in fused_items:
        vlog(f"      • {item['canonical_label']} ({item['image_id'][:8]}...) conf={item.get('classifier_confidence', 0):.2f}")
    
    # Log duplicates for debugging
    if duplicates:
        vlog(f"   🔄 Duplicates removed:")
        for dup in duplicates[:3]:  # Limit log spam
            vlog(f"      - {dup['canonical_label']} (dup of {dup.get('duplicate_of', '?')[:8]})")
    
    return fused_items
