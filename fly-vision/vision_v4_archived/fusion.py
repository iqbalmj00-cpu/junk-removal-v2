"""
v4.0 Cross-Image Fusion (Step 8)

Deduplicates items appearing in multiple images.
Uses "KEEP IF SEEN" policy with deterministic duplicate resolution.

Key principles:
1. INTRA-IMAGE DEDUP: Collapse same-label items in same image (bbox IoU > 0.50)
2. Any item with conf >= KEEP_THRESHOLD survives to dedup phase
3. Only drop if PROVEN duplicate of another survivor
4. Deterministic tie-break for consistent results
"""

from typing import List
from .utils import normalize_bbox_center, vlog


# Minimum confidence to keep an item (lower = more permissive)
KEEP_THRESHOLD = 0.30

# Position bucket grid size (5x5 = 25 buckets)
POSITION_GRID = 5

# Intra-image dedup threshold (bbox IoU > this = same object)
INTRA_IOU_THRESHOLD = 0.50

# Step 4: Separation guard thresholds (Gap 5)
SEPARATION_MIN_GAP = 0.02   # Min gap between edges as fraction of image
SEPARATION_CENTROID_MIN = 0.05  # Min centroid distance as fraction of image


def compute_bbox_iou(bbox1: List[float], bbox2: List[float]) -> float:
    """
    Compute Intersection over Union (IoU) for two bboxes.
    
    Bbox format: [x1, y1, x2, y2]
    """
    x1 = max(bbox1[0], bbox2[0])
    y1 = max(bbox1[1], bbox2[1])
    x2 = min(bbox1[2], bbox2[2])
    y2 = min(bbox1[3], bbox2[3])
    
    # Intersection area
    inter_width = max(0, x2 - x1)
    inter_height = max(0, y2 - y1)
    inter_area = inter_width * inter_height
    
    # Union area
    area1 = (bbox1[2] - bbox1[0]) * (bbox1[3] - bbox1[1])
    area2 = (bbox2[2] - bbox2[0]) * (bbox2[3] - bbox2[1])
    union_area = area1 + area2 - inter_area
    
    if union_area <= 0:
        return 0.0
    
    return inter_area / union_area


def has_separation_evidence(item1: dict, item2: dict) -> bool:
    """
    Step 4 (Gap 5): Detect if two items are proven separate.
    
    Items are proven separate if:
    - Non-overlapping bboxes (IoU = 0 or very low)
    - AND distinct centroids (distance > SEPARATION_CENTROID_MIN)
    
    Returns True if items should NOT be merged.
    """
    bbox1 = item1.get("bbox", [0, 0, 0, 0])
    bbox2 = item2.get("bbox", [0, 0, 0, 0])
    
    # Check if bboxes are non-overlapping
    iou = compute_bbox_iou(bbox1, bbox2)
    
    if iou > 0.1:
        # Overlapping, not proven separate
        return False
    
    # Check centroid distance
    c1_x = (bbox1[0] + bbox1[2]) / 2
    c1_y = (bbox1[1] + bbox1[3]) / 2
    c2_x = (bbox2[0] + bbox2[2]) / 2
    c2_y = (bbox2[1] + bbox2[3]) / 2
    
    # Centroid distance (normalized to 0-1 assuming normalized bboxes)
    dist = ((c2_x - c1_x) ** 2 + (c2_y - c1_y) ** 2) ** 0.5
    
    if dist >= SEPARATION_CENTROID_MIN:
        # Distinct centroids + non-overlapping = proven separate
        return True
    
    return False


def collapse_intra_image_duplicates(items: List[dict]) -> List[dict]:
    """
    Collapse duplicates within the same image.
    
    Rule: If two items have:
    - Same image_id
    - Same canonical_label (or raw_label)
    - bbox IoU > INTRA_IOU_THRESHOLD
    
    Then keep only the higher-confidence one.
    """
    if not items:
        return []
    
    # Group by (image_id, label)
    groups = {}
    for item in items:
        label = item.get("canonical_label", item.get("raw_label", "unknown")).lower()
        image_id = item.get("image_id", "unknown")
        key = (image_id, label)
        
        if key not in groups:
            groups[key] = []
        groups[key].append(item)
    
    # Collapse duplicates within each group
    collapsed = []
    total_dropped = 0
    
    for (image_id, label), group in groups.items():
        if len(group) == 1:
            collapsed.append(group[0])
            continue
        
        # Sort by confidence (highest first)
        group_sorted = sorted(group, key=lambda x: -x.get("classifier_confidence", x.get("score", 0)))
        
        # Keep list of surviving items
        survivors = []
        
        for item in group_sorted:
            is_duplicate = False
            
            for survivor in survivors:
                # Step 4: Check separation evidence FIRST
                if has_separation_evidence(item, survivor):
                    # Proven separate, do NOT merge even if label matches
                    continue
                
                iou = compute_bbox_iou(item.get("bbox", [0,0,0,0]), survivor.get("bbox", [0,0,0,0]))
                
                if iou > INTRA_IOU_THRESHOLD:
                    # This is a duplicate of an existing survivor
                    is_duplicate = True
                    item["intra_dup_of"] = survivor.get("proposal_id", "unknown")
                    item["intra_dup_iou"] = round(iou, 3)
                    total_dropped += 1
                    vlog(f"      🔄 INTRA_DUP: {label} (iou={iou:.2f}) dropped, keeping {survivor.get('proposal_id', '?')[:8]}")
                    break
            
            if not is_duplicate:
                survivors.append(item)
        
        collapsed.extend(survivors)
    
    if total_dropped > 0:
        vlog(f"   🔄 Intra-image dedup: collapsed {total_dropped} duplicate(s)")
    
    return collapsed


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
    
    Phase 0: Intra-image dedup (collapse same-label items with high bbox IoU)
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
    # PHASE 0: INTRA-IMAGE DEDUP (collapse same object detected twice in same image)
    # ===========================================================================
    
    items_after_intra = collapse_intra_image_duplicates(classified_items)
    vlog(f"   📦 After intra-image dedup: {len(classified_items)} → {len(items_after_intra)} items")
    
    # ===========================================================================
    # PHASE 1: RETENTION - Keep all items meeting threshold
    # ===========================================================================
    
    retained = []
    dropped_low_conf = []
    
    for item in items_after_intra:  # Use post-intra-dedup items
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
