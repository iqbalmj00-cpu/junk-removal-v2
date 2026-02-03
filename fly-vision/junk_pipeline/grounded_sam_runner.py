"""
GroundedSAM Runner: Grounding DINO + SAM2 for Open-Vocab Segmentation
Same architecture as Lang-SAM but fully local GPU inference.

v6.6.0: Added mask caching by preproc_sha256 to eliminate non-determinism.
"""

import hashlib
from dataclasses import dataclass
from typing import Optional, List, Dict
import numpy as np
from PIL import Image

# =============================================================================
# v6.6.0: LANE B MASK CACHE
# =============================================================================
# Cache masks by preproc_sha256 to ensure same pixels → same mask.
# This eliminates GroundedSAM non-determinism within a job.
# Cache is per-job (cleared when runner is recreated).

_LANE_B_MASK_CACHE: Dict[str, 'BulkMaskResult'] = {}

def clear_lane_b_cache():
    """Clear the Lane B mask cache. Call at start of new job."""
    global _LANE_B_MASK_CACHE
    _LANE_B_MASK_CACHE = {}
    print("[GroundedSAM] Lane B cache cleared")


@dataclass
class BulkMaskResult:
    """Result from bulk segmentation."""
    mask_np: Optional[np.ndarray]  # (H, W) boolean mask (after ground sub)
    mask_raw_np: Optional[np.ndarray] = None  # v8.2.2: mask BEFORE ground sub
    area_ratio: float = 0.0
    confidence: float = 0.0
    error: Optional[str] = None


# =============================================================================
# v8.2: BOX SCORING + LABEL PRIORS
# =============================================================================

HARD_NEGATIVE_LABELS = {'branches', 'tree', 'sky', 'grass', 'road', 'sidewalk'}
SOFT_NEGATIVE_LABELS = {'fence', 'building', 'car', 'vehicle'}
POSITIVE_LABELS = {'pile', 'debris', 'trash', 'garbage', 'bags', 'cardboard',
                   'boxes', 'wood', 'furniture', 'junk', 'waste', 'clutter'}


@dataclass
class BoxFeatures:
    """Features for scoring a DINO detection box."""
    box_idx: int
    box: list  # [x1, y1, x2, y2]
    label: str
    conf: float
    w_ratio: float
    h_ratio: float
    area_ratio: float
    center_y_norm: float
    ground_overlap: float
    score: float = 0.0


def _label_prior(label: str) -> float:
    """Score adjustment based on label semantics."""
    label_lower = label.lower()
    for neg in HARD_NEGATIVE_LABELS:
        if neg in label_lower:
            return -0.5
    for soft in SOFT_NEGATIVE_LABELS:
        if soft in label_lower:
            return -0.2
    for pos in POSITIVE_LABELS:
        if pos in label_lower:
            return +0.15
    return 0.0


def _compute_box_features(
    box: list,
    conf: float,
    label: str,
    ground_mask: np.ndarray,
    img_h: int,
    img_w: int,
    box_idx: int
) -> BoxFeatures:
    """Compute features for a single DINO box."""
    x1, y1, x2, y2 = box
    box_w = x2 - x1
    box_h = y2 - y1
    
    w_ratio = box_w / img_w
    h_ratio = box_h / img_h
    area_ratio = (box_w * box_h) / (img_w * img_h)
    center_y_norm = ((y1 + y2) / 2) / img_h
    
    # Ground overlap: fraction of box that overlaps ground mask
    ground_overlap = 0.0
    if ground_mask is not None:
        x1i, y1i, x2i, y2i = int(x1), int(y1), int(x2), int(y2)
        x1i, y1i = max(0, x1i), max(0, y1i)
        x2i, y2i = min(img_w, x2i), min(img_h, y2i)
        box_region = ground_mask[y1i:y2i, x1i:x2i]
        if box_region.size > 0:
            ground_overlap = box_region.sum() / box_region.size
    
    return BoxFeatures(
        box_idx=box_idx,
        box=box,
        label=label,
        conf=conf,
        w_ratio=w_ratio,
        h_ratio=h_ratio,
        area_ratio=area_ratio,
        center_y_norm=center_y_norm,
        ground_overlap=ground_overlap
    )


def _score_box(feat: BoxFeatures, scene_ground_pct: float = 0.0, fallback_mode: bool = False) -> float:
    """
    Compute selection score for a box.
    
    v8.2.1: Uses excess-based ground overlap penalty to avoid score collapse
    when ground mask covers most of the image.
    """
    score = feat.conf + _label_prior(feat.label)
    
    # Penalty: Panorama boxes (almost never allow)
    if feat.w_ratio > 0.90:
        score -= 1.2
    elif feat.w_ratio > 0.75:
        score -= 0.8
    
    # Penalty: Huge area
    if feat.area_ratio > 0.50:
        score -= 0.5
    
    # Penalty: Ground overlap (v8.2.1: excess-based, conditional)
    # In fallback mode, skip this penalty entirely
    if not fallback_mode:
        # Penalize only if box overlaps ground MORE than scene average
        excess = feat.ground_overlap - scene_ground_pct
        if excess > 0.10:
            # Scale penalty: 0.10 excess → 0.2 penalty, 0.40 excess → 0.6 penalty (capped)
            penalty = 0.6 * min(1.0, excess / 0.30)
            score -= penalty
    
    # Penalty: Upper region (sky/tree zone)
    if feat.center_y_norm < 0.30:
        score -= 0.4
    
    return max(0.0, score)


def _select_boxes(
    features: List[BoxFeatures], 
    top_k: int = 3, 
    min_score: float = 0.25,
    scene_ground_pct: float = 0.0
) -> List[BoxFeatures]:
    """
    Select top-K boxes by score with NMS-like deduplication.
    
    v8.2.1: Detects score collapse and re-scores in fallback mode.
    """
    # Score all boxes with regular mode
    for feat in features:
        feat.score = _score_box(feat, scene_ground_pct, fallback_mode=False)
    
    # SCORE COLLAPSE DETECTION: if max score < min_score, something is wrong
    max_score = max((f.score for f in features), default=0.0)
    
    if max_score < min_score and features:
        # Log detailed breakdown for debugging
        print(f"[BOX_SCORE] ⚠️ SCORE COLLAPSE DETECTED: max_score={max_score:.2f} < min_score={min_score:.2f}")
        print(f"[BOX_SCORE] Scene ground coverage: {scene_ground_pct:.1%}")
        print(f"[BOX_SCORE] Switching to FALLBACK MODE (ignoring ground penalty)")
        
        for feat in features:
            print(f"  Box {feat.box_idx}: \"{feat.label}\" conf={feat.conf:.2f}, "
                  f"w={feat.w_ratio:.2f}, area={feat.area_ratio:.2f}, "
                  f"ground={feat.ground_overlap:.2f}, center_y={feat.center_y_norm:.2f}, "
                  f"prior={_label_prior(feat.label):+.2f}")
        
        # Re-score in fallback mode (no ground penalty)
        for feat in features:
            feat.score = _score_box(feat, scene_ground_pct, fallback_mode=True)
        
        print(f"[BOX_SCORE] Fallback scores: {[(f.box_idx, f.label, f.score) for f in sorted(features, key=lambda x: x.score, reverse=True)[:3]]}")
    
    # Sort by score descending
    ranked = sorted(features, key=lambda f: f.score, reverse=True)
    
    selected = []
    for feat in ranked:
        if feat.score < min_score:
            break
        
        # NMS: skip if 70% overlap with already-selected box
        skip = False
        for sel in selected:
            iou = _box_iou(feat.box, sel.box)
            if iou > 0.70:
                skip = True
                break
        
        if not skip:
            selected.append(feat)
            print(f"[BOX_SCORE] {feat.box_idx}: \"{feat.label}\" conf={feat.conf:.2f}, "
                  f"w={feat.w_ratio:.2f}, ground={feat.ground_overlap:.2f} → score={feat.score:.2f} ✓")
        
        if len(selected) >= top_k:
            break
    
    # Log rejected boxes
    for feat in ranked:
        if feat not in selected:
            print(f"[BOX_SCORE] {feat.box_idx}: \"{feat.label}\" conf={feat.conf:.2f} → score={feat.score:.2f} ✗")
    
    # Fallback: if STILL none selected after fallback mode, take highest scoring box
    if not selected and ranked:
        selected = [ranked[0]]
        print(f"[BOX_SCORE] EMERGENCY FALLBACK: using {ranked[0].label} (score={ranked[0].score:.2f})")
    
    return selected


def _box_iou(box1: list, box2: list) -> float:
    """Compute IoU between two boxes."""
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])
    
    inter_area = max(0, x2 - x1) * max(0, y2 - y1)
    box1_area = (box1[2] - box1[0]) * (box1[3] - box1[1])
    box2_area = (box2[2] - box2[0]) * (box2[3] - box2[1])
    union_area = box1_area + box2_area - inter_area
    
    return inter_area / union_area if union_area > 0 else 0.0


# =============================================================================
# v8.2: MASK CLEANUP PIPELINE
# =============================================================================

def _is_grounded_component(
    comp_mask: np.ndarray,
    dist_to_ground: np.ndarray,
    img_h: int,
    max_ground_dist_px: int = 20
) -> bool:
    """
    Check if component is grounded (not floating).
    
    Rules:
    1. Within N pixels of ground boundary, OR
    2. Touches bottom 40% of image, OR  
    3. Kill if entirely in top 45%
    """
    # Rule 1: Distance to ground
    d = dist_to_ground[comp_mask]
    if d.size > 0 and d.min() <= max_ground_dist_px:
        return True
    
    # Rule 2: Touches bottom 40%
    rows = np.where(comp_mask.any(axis=1))[0]
    if rows.size > 0 and rows.max() >= 0.60 * img_h:
        return True
    
    # Rule 3: Kill if entirely above 45% line
    if rows.size > 0 and rows.max() < 0.45 * img_h:
        return False
    
    return False


def _float_filter(
    bulk_raw: np.ndarray,
    ground_mask: np.ndarray,
    img_h: int,
    max_ground_dist_px: int = 20
) -> np.ndarray:
    """
    Remove floating blobs not connected to ground.
    
    Must run BEFORE ground subtraction so ground overlap check works.
    """
    from scipy.ndimage import distance_transform_edt, label as scipy_label
    
    if ground_mask is None:
        return bulk_raw
    
    # Force boolean and compute EDT once
    ground_mask_bool = (ground_mask > 0)
    dist_to_ground = distance_transform_edt(~ground_mask_bool)
    
    # Find connected components
    labeled, num_features = scipy_label(bulk_raw)
    bulk_grounded = np.zeros_like(bulk_raw)
    
    removed_count = 0
    for comp_id in range(1, num_features + 1):
        comp_mask = (labeled == comp_id)
        if _is_grounded_component(comp_mask, dist_to_ground, img_h, max_ground_dist_px):
            bulk_grounded |= comp_mask
        else:
            removed_count += 1
    
    if removed_count > 0:
        print(f"[FLOAT_FILTER] Removed {removed_count} floating components")
    
    return bulk_grounded


def _clean_bulk_with_ground(
    bulk_grounded: np.ndarray,
    ground_mask: np.ndarray
) -> np.ndarray:
    """
    Adaptive ground subtraction with dilation based on overlap.
    
    High overlap → aggressive subtraction (12px dilation)
    Low overlap → gentle subtraction (4px dilation)  
    """
    import cv2
    
    if ground_mask is None or bulk_grounded.sum() == 0:
        return bulk_grounded
    
    # Force boolean
    ground_mask_bool = (ground_mask > 0)
    
    # Compute overlap
    overlap_pct = (bulk_grounded & ground_mask_bool).sum() / bulk_grounded.sum()
    
    # Adaptive radius
    if overlap_pct > 0.25:
        radius = 12
    elif overlap_pct > 0.15:
        radius = 10
    elif overlap_pct > 0.08:
        radius = 6
    else:
        radius = 4
    
    print(f"[GROUND_SUB] overlap={overlap_pct:.1%}, dilation_radius={radius}px")
    
    # Dilate ground
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (radius*2+1, radius*2+1))
    g = ground_mask_bool.astype(np.uint8)
    ground_expanded = cv2.dilate(g, kernel).astype(bool)
    
    # Subtract
    bulk_clean = bulk_grounded & ~ground_expanded
    
    # Close small holes (tarp folds, shadows)
    close_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    bulk_clean = cv2.morphologyEx(bulk_clean.astype(np.uint8), cv2.MORPH_CLOSE, close_kernel).astype(bool)
    
    return bulk_clean


def _keep_top_components(
    bulk_clean: np.ndarray,
    max_components: int = 4,
    min_area_pct: float = 0.01
) -> np.ndarray:
    """Keep top N components above minimum area threshold."""
    import cv2
    
    if bulk_clean.sum() == 0:
        return bulk_clean
    
    # Find connected components
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(
        bulk_clean.astype(np.uint8), connectivity=8
    )
    
    min_area = min_area_pct * bulk_clean.size
    
    # Sort by area (skip background label 0)
    component_areas = [(i, stats[i, cv2.CC_STAT_AREA]) for i in range(1, num_labels)]
    component_areas.sort(key=lambda x: x[1], reverse=True)
    
    # Keep top N above threshold
    keep_mask = np.zeros_like(bulk_clean)
    kept = 0
    for comp_id, area in component_areas:
        if area >= min_area and kept < max_components:
            keep_mask |= (labels == comp_id)
            kept += 1
    
    if kept < len(component_areas):
        print(f"[COMP_KEEP] Kept {kept}/{len(component_areas)} components")
    
    return keep_mask


def _is_catastrophic_spill(
    bulk_clean: np.ndarray,
    ground_mask: np.ndarray = None
) -> tuple:
    """
    Detect catastrophic mask spill.
    
    Returns (is_spill, reason) tuple.
    """
    if bulk_clean.sum() == 0:
        return False, None
    
    h, w = bulk_clean.shape
    clean_ratio = bulk_clean.sum() / bulk_clean.size
    
    # Check edge touching
    touches_left = bulk_clean[:, 0].any()
    touches_right = bulk_clean[:, -1].any()
    touches_top = bulk_clean[0, :].any()
    touches_bottom = bulk_clean[-1, :].any()
    edge_count = sum([touches_left, touches_right, touches_top, touches_bottom])
    
    # Trigger conditions
    if clean_ratio > 0.45 and edge_count >= 3:
        return True, f"area={clean_ratio:.1%} + {edge_count} edges"
    if clean_ratio > 0.55:
        return True, f"area={clean_ratio:.1%} > 55%"
    if edge_count == 4:
        return True, "touches all 4 edges"
    if touches_left and touches_right and clean_ratio > 0.40:
        return True, f"spans full width + area={clean_ratio:.1%}"
    
    return False, None


class GroundedSAMRunner:
    """
    Grounding DINO + SAM2 for open-vocabulary segmentation.
    Uses HuggingFace Transformers API.
    """
    _instance = None
    _gdino_model = None
    _gdino_processor = None
    _sam_model = None
    _sam_processor = None
    _device = None
    
    # Detection threshold (lowered for better recall)
    BOX_THRESHOLD = 0.10
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._gdino_model is None:
            self._load_models()
    
    def _load_models(self):
        """Load Grounding DINO and SAM2 models."""
        try:
            import torch
            from transformers import (
                AutoProcessor, 
                AutoModelForZeroShotObjectDetection,
                SamModel,
                SamProcessor,
            )
            
            # Determine device
            if torch.cuda.is_available():
                self._device = "cuda"
            elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                self._device = "mps"
            else:
                self._device = "cpu"
            
            # Load Grounding DINO
            print(f"[GroundedSAM] Loading Grounding DINO on {self._device}...")
            gdino_id = "IDEA-Research/grounding-dino-base"
            # v6.6.0: Pin use_fast=False to eliminate processor variance
            self._gdino_processor = AutoProcessor.from_pretrained(gdino_id, use_fast=False)
            self._gdino_model = AutoModelForZeroShotObjectDetection.from_pretrained(gdino_id).to(self._device)
            print(f"[GroundedSAM] Grounding DINO loaded")
            
            # Load SAM2
            print(f"[GroundedSAM] Loading SAM2...")
            sam_id = "facebook/sam-vit-base"
            # v6.6.0: Pin use_fast=False to eliminate processor variance
            self._sam_processor = SamProcessor.from_pretrained(sam_id, use_fast=False)
            self._sam_model = SamModel.from_pretrained(sam_id).to(self._device)
            print(f"[GroundedSAM] SAM2 loaded successfully")
            
        except ImportError as e:
            print(f"[GroundedSAM] Import error: {e}")
            self._gdino_model = None
            
        except Exception as e:
            print(f"[GroundedSAM] Failed to load models: {e}")
            import traceback
            traceback.print_exc()
            self._gdino_model = None
    
    def _run_detection(self, image: Image.Image, prompts: List[str]):
        """Run Grounding DINO detection with given prompts."""
        import torch
        
        # Format prompts: "pile. debris. branches." (lowercase + dot)
        text_prompt = " ".join([f"{p.lower()}." for p in prompts])
        
        gdino_inputs = self._gdino_processor(
            images=image, 
            text=text_prompt, 
            return_tensors="pt"
        ).to(self._device)
        
        with torch.no_grad():
            gdino_outputs = self._gdino_model(**gdino_inputs)
        
        # Post-process detections
        results = self._gdino_processor.post_process_grounded_object_detection(
            gdino_outputs,
            gdino_inputs.input_ids,
            target_sizes=[image.size[::-1]]  # (height, width)
        )[0]
        
        boxes = results["boxes"]
        scores = results["scores"]
        labels = results["labels"]
        
        # Filter by threshold
        mask = scores >= self.BOX_THRESHOLD
        boxes = boxes[mask]
        scores = scores[mask]
        labels = [l for l, m in zip(labels, mask.tolist()) if m]
        
        return boxes, scores, labels
    
    # =========================================================================
    # v9.0: Separated Detection + Segmentation for Qwen Arbitration
    # =========================================================================
    
    def run_detection(
        self,
        image: Image.Image,
        prompts: List[str] = None
    ) -> List[dict]:
        """
        v9.0: Run Grounding DINO detection only (no SAM2).
        
        Used by orchestrator to get candidate boxes before Qwen arbitration.
        
        Args:
            image: PIL Image
            prompts: Detection prompts (default: pile prompts)
            
        Returns:
            List of candidate boxes:
            [{"box": [x1, y1, x2, y2], "label": str, "confidence": float}, ...]
        """
        if self._gdino_model is None:
            print("[GroundedSAM] Models not loaded - returning empty boxes")
            return []
        
        # Ensure RGB
        if image.mode != "RGB":
            image = image.convert("RGB")
        
        # Primary prompts for junk/debris
        primary_prompts = prompts if prompts else [
            "pile of junk",
            "debris pile",
            "garbage bags",
            "branches and wood",
            "yard waste",
            "trash pile",
            "cardboard boxes",
        ]
        
        # Fallback prompts if primary fails
        fallback_prompts = [
            "objects",
            "stuff",
            "items",
            "material",
            "clutter",
        ]
        
        try:
            print(f"[GroundedSAM] run_detection: trying primary prompts...")
            boxes, scores, labels = self._run_detection(image, primary_prompts)
            
            if len(boxes) == 0:
                print(f"[GroundedSAM] Primary failed, trying fallback prompts...")
                boxes, scores, labels = self._run_detection(image, fallback_prompts)
            
            if len(boxes) == 0:
                print(f"[GroundedSAM] run_detection: no boxes found")
                return []
            
            # Convert to list of dicts
            boxes_list = boxes.cpu().tolist()
            scores_list = scores.cpu().tolist()
            
            result = []
            for box, score, label in zip(boxes_list, scores_list, labels):
                result.append({
                    "box": box,
                    "label": label,
                    "confidence": float(score)
                })
            
            print(f"[GroundedSAM] run_detection: found {len(result)} boxes")
            for i, r in enumerate(result[:5]):  # Log first 5
                print(f"  Box {i}: {r['label']} ({r['confidence']:.2f}) @ {[int(x) for x in r['box']]}")
            
            return result
            
        except Exception as e:
            print(f"[GroundedSAM] run_detection error: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def run_segmentation_on_box(
        self,
        image: Image.Image,
        box: List[float],
        mask_hint: Optional[np.ndarray] = None,  # v9.2: reference mask for guidance
    ) -> np.ndarray:
        """
        v9.2: Run SAM2 segmentation on a single box prompt with optional mask hint.
        
        Used after Qwen arbitration selects the best box.
        
        Args:
            image: PIL Image (full resolution)
            box: Bounding box coordinates [x1, y1, x2, y2]
            mask_hint: Optional binary mask from best frame to guide segmentation
            
        Returns:
            Binary mask (H, W) dtype=bool for pile within box
        """
        if self._sam_model is None:
            print("[GroundedSAM] SAM model not loaded")
            h, w = image.height, image.width
            return np.zeros((h, w), dtype=bool)
        
        # Ensure RGB
        if image.mode != "RGB":
            image = image.convert("RGB")
        
        h, w = image.height, image.width
        
        try:
            import torch
            from scipy import ndimage
            
            hint_str = " (with mask hint)" if mask_hint is not None else ""
            print(f"[GroundedSAM] run_segmentation_on_box: box={[int(x) for x in box]}{hint_str}")
            
            # v9.2: Prepare mask hint if provided
            mask_inputs = None
            if mask_hint is not None:
                # Resize hint to match image if needed
                if mask_hint.shape != (h, w):
                    from PIL import Image as PILImage
                    hint_img = PILImage.fromarray((mask_hint * 255).astype(np.uint8))
                    hint_img = hint_img.resize((w, h), PILImage.NEAREST)
                    mask_hint = np.array(hint_img) > 127
                
                # Convert to tensor for SAM2 (1 x 1 x H x W)
                mask_inputs = torch.from_numpy(mask_hint.astype(np.float32)).unsqueeze(0).unsqueeze(0)
            
            # Run SAM2 with box prompt (and optional mask hint)
            sam_inputs = self._sam_processor(
                image,
                input_boxes=[[[box]]],
                return_tensors="pt"
            ).to(self._device)
            
            # v9.2: Add mask_inputs if available
            if mask_inputs is not None:
                sam_inputs["mask_inputs"] = mask_inputs.to(self._device)
            
            with torch.no_grad():
                sam_outputs = self._sam_model(**sam_inputs)
            
            masks = self._sam_processor.image_processor.post_process_masks(
                sam_outputs.pred_masks.cpu(),
                sam_inputs["original_sizes"].cpu(),
                sam_inputs["reshaped_input_sizes"].cpu()
            )[0]
            
            if len(masks) == 0:
                print(f"[GroundedSAM] SAM returned no masks")
                return np.zeros((h, w), dtype=bool)
            
            # Get best mask
            mask = masks[0].squeeze().numpy()
            if mask.ndim == 3:
                mask = mask[0]
            
            binary_mask = mask > 0.5
            
            # Apply slight dilation (4px)
            DILATION_RADIUS = 4
            struct = ndimage.generate_binary_structure(2, 1)
            dilated_mask = ndimage.binary_dilation(
                binary_mask, 
                structure=struct, 
                iterations=DILATION_RADIUS
            )
            
            area_pct = np.mean(dilated_mask) * 100
            print(f"[GroundedSAM] run_segmentation_on_box: mask area={area_pct:.1f}%")
            
            return dilated_mask.astype(bool)
            
        except Exception as e:
            print(f"[GroundedSAM] run_segmentation_on_box error: {e}")
            import traceback
            traceback.print_exc()
            return np.zeros((h, w), dtype=bool)
    
    def segment_cached(
        self,
        image: Image.Image,
        preproc_sha256: str,
        prompts: List[str] = None,
        frame_id: str = None,
        job_id: str = None,
        ground_mask: np.ndarray = None
    ) -> BulkMaskResult:
        """
        v8.2: Cache-first segmentation with ground mask cleanup.
        
        Returns cached mask if preproc_sha256 matches, otherwise computes and caches.
        Note: When cache hits, ground mask cleanup is NOT reapplied.
        """
        global _LANE_B_MASK_CACHE
        
        if preproc_sha256 in _LANE_B_MASK_CACHE:
            cached = _LANE_B_MASK_CACHE[preproc_sha256]
            print(f"[GroundedSAM] CACHE HIT for {preproc_sha256[:12]} (area={cached.area_ratio:.1%})")
            return cached
        
        # Compute fresh with ground mask cleanup
        result = self.segment(image, prompts, frame_id=frame_id, job_id=job_id, ground_mask=ground_mask)
        
        # Cache result
        _LANE_B_MASK_CACHE[preproc_sha256] = result
        print(f"[GroundedSAM] CACHE STORE for {preproc_sha256[:12]}")
        
        return result
    
    def _save_dino_overlay(
        self,
        image: Image.Image,
        boxes: list,
        scores: list,
        labels: list,
        frame_id: str = None,
        job_id: str = None
    ):
        """
        v7.2: Save DINO bounding box overlay for debugging.
        Draws colored boxes with labels and confidence scores.
        """
        import os
        from PIL import ImageDraw, ImageFont
        
        if not frame_id or not job_id:
            return
        
        try:
            # Create overlay directory
            overlay_dir = f"/tmp/gate_overlays/{job_id}"
            os.makedirs(overlay_dir, exist_ok=True)
            
            # Copy image for drawing
            overlay = image.copy()
            draw = ImageDraw.Draw(overlay)
            
            # Color palette for boxes
            colors = [
                (255, 0, 0),    # Red
                (0, 255, 0),    # Green
                (0, 0, 255),    # Blue
                (255, 255, 0),  # Yellow
                (255, 0, 255),  # Magenta
                (0, 255, 255),  # Cyan
                (255, 128, 0),  # Orange
                (128, 0, 255),  # Purple
            ]
            
            for i, (box, score, label) in enumerate(zip(boxes, scores, labels)):
                color = colors[i % len(colors)]
                x1, y1, x2, y2 = box
                
                # Draw box with thick outline
                for offset in range(3):  # 3px thick
                    draw.rectangle(
                        [x1 - offset, y1 - offset, x2 + offset, y2 + offset],
                        outline=color
                    )
                
                # Draw label background
                label_text = f"{label}: {score:.2f}"
                text_bbox = draw.textbbox((x1, y1 - 20), label_text)
                draw.rectangle(text_bbox, fill=color)
                draw.text((x1, y1 - 20), label_text, fill=(255, 255, 255))
                
                # Log box details
                print(f"[DINO_BOX] {i}: \"{label}\" ({score:.2f}) [{int(x1)}, {int(y1)}, {int(x2)}, {int(y2)}]")
            
            # Save overlay
            overlay_path = f"{overlay_dir}/{frame_id[:8]}_dino_boxes.png"
            overlay.save(overlay_path)
            print(f"[OVERLAY] Saved: {overlay_path}")
            
        except Exception as e:
            print(f"[GroundedSAM] Failed to save DINO overlay: {e}")
    
    def segment(
        self, 
        image: Image.Image, 
        prompts: List[str] = None,
        frame_id: str = None,
        job_id: str = None,
        ground_mask: np.ndarray = None
    ) -> BulkMaskResult:
        """
        v8.2: Run Grounding DINO + SAM2 segmentation with box scoring and cleanup.
        
        Pipeline:
        1. DINO detection
        2. Box scoring with label priors
        3. Top-K box selection
        4. SAM2 on selected boxes only
        5. Floating blob filter
        6. Adaptive ground subtraction
        7. Component filtering
        8. Spill detection
        
        Args:
            image: PIL Image to process
            prompts: List of text prompts
            frame_id: Frame ID for overlay naming
            job_id: Job ID for overlay directory
            ground_mask: Optional ground mask from Lane D (for cleanup)
            
        Returns:
            BulkMaskResult with cleaned mask
        """
        if self._gdino_model is None or self._sam_model is None:
            return BulkMaskResult(
                mask_np=None,
                area_ratio=0.0,
                confidence=0.0,
                error="Models not loaded"
            )
        
        # Primary prompts for junk/debris
        primary_prompts = prompts if prompts else [
            "pile of junk",
            "debris pile",
            "garbage bags",
            "branches and wood",
            "yard waste",
            "trash pile",
            "cardboard boxes",
        ]
        
        # Fallback prompts if primary fails
        fallback_prompts = [
            "objects",
            "stuff",
            "items",
            "material",
            "clutter",
        ]
        
        try:
            import torch
            from scipy import ndimage
            
            # Ensure RGB
            if image.mode != "RGB":
                image = image.convert("RGB")
            
            h, w = image.height, image.width
            
            # Force boolean ground mask
            ground_mask_bool = (ground_mask > 0) if ground_mask is not None else None
            
            # =========================================================
            # STEP 1: DINO Detection
            # =========================================================
            print(f"[GroundedSAM] Trying primary prompts (threshold={self.BOX_THRESHOLD})...")
            boxes, scores, labels = self._run_detection(image, primary_prompts)
            
            if len(boxes) == 0:
                print(f"[GroundedSAM] Primary failed, trying fallback prompts...")
                boxes, scores, labels = self._run_detection(image, fallback_prompts)
            
            print(f"[GroundedSAM] DINO detected {len(boxes)} objects: {labels[:5]}...")
            
            if len(boxes) == 0:
                print(f"[GroundedSAM] No detections with any prompts")
                return BulkMaskResult(
                    mask_np=np.zeros((h, w), dtype=bool),
                    area_ratio=0.0,
                    confidence=0.0,
                    error=None
                )
            
            boxes_list = boxes.cpu().tolist()
            scores_list = scores.cpu().tolist()
            
            # Save DINO overlay (all boxes)
            self._save_dino_overlay(image, boxes_list, scores_list, labels, frame_id, job_id)
            
            # =========================================================
            # STEP 2: Box Scoring + Selection (v8.2.1)
            # =========================================================
            # Compute scene-level ground coverage for excess-based penalty
            scene_ground_pct = 0.0
            if ground_mask_bool is not None:
                scene_ground_pct = float(ground_mask_bool.sum()) / ground_mask_bool.size
            
            box_features = [
                _compute_box_features(box, score, label, ground_mask_bool, h, w, idx)
                for idx, (box, score, label) in enumerate(zip(boxes_list, scores_list, labels))
            ]
            
            selected_boxes = _select_boxes(box_features, top_k=3, min_score=0.25, scene_ground_pct=scene_ground_pct)
            
            if not selected_boxes:
                print(f"[GroundedSAM] No boxes passed scoring")
                return BulkMaskResult(
                    mask_np=np.zeros((h, w), dtype=bool),
                    area_ratio=0.0,
                    confidence=0.0,
                    error=None
                )
            
            # =========================================================
            # STEP 3: SAM2 on Selected Boxes Only
            # =========================================================
            combined_mask = np.zeros((h, w), dtype=bool)
            max_score = max(f.conf for f in selected_boxes)
            
            for feat in selected_boxes:
                try:
                    sam_inputs = self._sam_processor(
                        image,
                        input_boxes=[[[feat.box]]],
                        return_tensors="pt"
                    ).to(self._device)
                    
                    with torch.no_grad():
                        sam_outputs = self._sam_model(**sam_inputs)
                    
                    masks = self._sam_processor.image_processor.post_process_masks(
                        sam_outputs.pred_masks.cpu(),
                        sam_inputs["original_sizes"].cpu(),
                        sam_inputs["reshaped_input_sizes"].cpu()
                    )[0]
                    
                    if len(masks) > 0:
                        mask = masks[0].squeeze().numpy()
                        if mask.ndim == 3:
                            mask = mask[0]
                        combined_mask |= (mask > 0.5)
                except Exception as e:
                    print(f"[GroundedSAM] SAM error for box {feat.box_idx}: {e}")
                    continue
            
            # Apply slight dilation (4px - reduced from 8px)
            DILATION_RADIUS = 4
            struct = ndimage.generate_binary_structure(2, 1)
            bulk_raw = ndimage.binary_dilation(
                combined_mask, 
                structure=struct, 
                iterations=DILATION_RADIUS
            )
            
            raw_area = float(np.sum(bulk_raw)) / (h * w)
            print(f"[GroundedSAM] bulk_raw area={raw_area:.1%}, boxes_used={len(selected_boxes)}/{len(boxes_list)}")
            
            # =========================================================
            # STEP 4-7: Cleanup Pipeline (v8.2)
            # =========================================================
            
            # Step 4: Floating blob filter (BEFORE ground subtraction)
            bulk_grounded = _float_filter(bulk_raw, ground_mask, h, max_ground_dist_px=20)
            
            # Step 5: Adaptive ground subtraction
            bulk_clean = _clean_bulk_with_ground(bulk_grounded, ground_mask)
            
            # Step 6: Keep top components
            bulk_clean = _keep_top_components(bulk_clean, max_components=4, min_area_pct=0.01)
            
            # Step 7: Spill check
            is_spill, spill_reason = _is_catastrophic_spill(bulk_clean)
            if is_spill:
                print(f"[SPILL_DETECT] Triggered: {spill_reason}")
            
            # Calculate final area ratio
            area_ratio = float(np.sum(bulk_clean)) / (h * w)
            
            print(f"[GroundedSAM] bulk_clean area={area_ratio:.1%} (was {raw_area:.1%}), spill={is_spill}")
            
            return BulkMaskResult(
                mask_np=bulk_clean,
                mask_raw_np=bulk_grounded.copy(),  # v8.2.2: Store pre-ground-sub mask
                area_ratio=area_ratio,
                confidence=max_score if not is_spill else max_score * 0.5,
                error="spill_detected" if is_spill else None
            )
            
        except Exception as e:
            print(f"[GroundedSAM] Error: {e}")
            import traceback
            traceback.print_exc()
            
            return BulkMaskResult(
                mask_np=None,
                area_ratio=0.0,
                confidence=0.0,
                error=str(e)
            )


# Global instance getter
_runner_instance = None

def get_grounded_sam_runner() -> GroundedSAMRunner:
    """Get or create the GroundedSAM runner instance."""
    global _runner_instance
    if _runner_instance is None:
        _runner_instance = GroundedSAMRunner()
    return _runner_instance
