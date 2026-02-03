"""
Qwen Arbitration Module (v9.0)
Centralized VLM arbitration for frame ranking and box selection.

This module provides two critical decision functions:
1. rank_frames(): Select the best frame from input images
2. select_pile_box(): Choose the single best pile box from DINO candidates
"""

import json
import re
import base64
import os
from dataclasses import dataclass
from typing import Optional
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

# =============================================================================
# CONFIGURATION
# =============================================================================

ARBITRATION_TIMEOUT_S = 25
ARBITRATION_IMAGE_RESIZE_PX = 768
ARBITRATION_MAX_TOKENS = 512
ARBITRATION_ENABLED = True  # Master switch for fallback

# HuggingFace Router API config
HF_ROUTER_URL = "https://router.huggingface.co/v1/chat/completions"
HF_MODEL_ID = "Qwen/Qwen2.5-VL-7B-Instruct:hyperbolic"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class FrameRankingResult:
    """Result from frame ranking."""
    best_frame_id: str
    best_frame_index: int
    rankings: list[dict]  # [{frame_id, index, rank, reason}]
    confidence: float


@dataclass
class BoxSelectionResult:
    """Result from box selection."""
    selected_box_index: int
    selected_box: list[float]  # [x1, y1, x2, y2]
    selected_label: str
    confidence: float
    reason: str


@dataclass
class MultiBoxSelectionResult:
    """Result from multi-box selection (v9.1)."""
    selected_boxes: list[dict]  # [{index, box, label, confidence}]
    multi_pile: bool
    reason: str


# =============================================================================
# JSON PARSE RESILIENCE (reused from vlm_triage)
# =============================================================================

def _repair_json(raw: str) -> str:
    """Attempt to repair common JSON issues from VLM output."""
    # Find first { and last }
    start = raw.find('{')
    end = raw.rfind('}')
    if start != -1 and end != -1 and end > start:
        raw = raw[start:end+1]
    
    # Fix trailing commas
    raw = re.sub(r',\s*}', '}', raw)
    raw = re.sub(r',\s*]', ']', raw)
    
    # Fix single quotes
    raw = raw.replace("'", '"')
    
    return raw


def _extract_json_block(raw: str) -> Optional[str]:
    """Extract the largest {...} block from text."""
    depth = 0
    start_idx = None
    best_block = None
    best_len = 0
    
    for i, char in enumerate(raw):
        if char == '{':
            if depth == 0:
                start_idx = i
            depth += 1
        elif char == '}':
            depth -= 1
            if depth == 0 and start_idx is not None:
                block = raw[start_idx:i+1]
                if len(block) > best_len:
                    best_block = block
                    best_len = len(block)
                start_idx = None
    
    return best_block


def _parse_json_resilient(raw_output: str) -> Optional[dict]:
    """3-step JSON parse with resilience."""
    if not raw_output or not raw_output.strip():
        return None
    
    # Step 1: Direct parse
    try:
        return json.loads(raw_output)
    except json.JSONDecodeError:
        pass
    
    # Step 2: Repair and parse
    repaired = _repair_json(raw_output)
    try:
        return json.loads(repaired)
    except json.JSONDecodeError:
        pass
    
    # Step 3: Extract largest JSON block
    extracted = _extract_json_block(raw_output)
    if extracted:
        try:
            return json.loads(extracted)
        except json.JSONDecodeError:
            pass
    
    return None


# =============================================================================
# IMAGE UTILITIES
# =============================================================================

def _resize_for_vlm(img: Image.Image, max_size: int = ARBITRATION_IMAGE_RESIZE_PX) -> Image.Image:
    """Resize image for VLM input to control latency."""
    w, h = img.size
    if max(w, h) <= max_size:
        return img
    
    if w > h:
        new_w = max_size
        new_h = int(h * max_size / w)
    else:
        new_h = max_size
        new_w = int(w * max_size / h)
    
    return img.resize((new_w, new_h), Image.Resampling.LANCZOS)


def _pil_to_base64(img: Image.Image) -> str:
    """Convert PIL Image to base64 data URI."""
    buffer = BytesIO()
    img.save(buffer, format="JPEG", quality=85)
    b64 = base64.b64encode(buffer.getvalue()).decode()
    return f"data:image/jpeg;base64,{b64}"


def _visualize_boxes(
    image: Image.Image, 
    boxes: list[dict],
    line_width: int = 4
) -> Image.Image:
    """
    Draw numbered bounding boxes on image for Qwen to reference.
    
    Args:
        image: Original PIL image
        boxes: List of {box: [x1,y1,x2,y2], label: str, confidence: float}
        line_width: Width of box outline
        
    Returns:
        PIL image with boxes drawn and numbered (1, 2, 3...)
    """
    img_copy = image.copy()
    draw = ImageDraw.Draw(img_copy)
    
    # Colors for different boxes
    colors = ['#FF0000', '#00FF00', '#0000FF', '#FFFF00', '#FF00FF', '#00FFFF']
    
    # Try to get a readable font, fallback to default
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 24)
    except:
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
        except:
            font = ImageFont.load_default()
    
    for i, box_info in enumerate(boxes):
        x1, y1, x2, y2 = box_info['box']
        color = colors[i % len(colors)]
        label = box_info.get('label', 'unknown')
        conf = box_info.get('confidence', 0.0)
        
        # Draw rectangle
        draw.rectangle([x1, y1, x2, y2], outline=color, width=line_width)
        
        # Draw label with number
        label_text = f"{i+1}: {label} ({conf:.2f})"
        
        # Calculate text position (above box if possible)
        text_y = y1 - 30 if y1 > 40 else y2 + 5
        
        # Draw text background
        bbox = draw.textbbox((x1, text_y), label_text, font=font)
        draw.rectangle(bbox, fill=color)
        draw.text((x1, text_y), label_text, fill='white', font=font)
    
    return img_copy


# =============================================================================
# VLM API CALL
# =============================================================================

def _call_vlm(content: list, timeout: int = ARBITRATION_TIMEOUT_S) -> str:
    """
    Call Qwen2.5-VL via HuggingFace Router API.
    
    Args:
        content: List of content items (images + text)
        timeout: Request timeout in seconds
        
    Returns:
        Raw text output from the model
    """
    import requests
    
    hf_token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    if not hf_token:
        raise ValueError("HF_TOKEN or HUGGING_FACE_HUB_TOKEN environment variable not set")
    
    headers = {
        "Authorization": f"Bearer {hf_token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": HF_MODEL_ID,
        "messages": [{"role": "user", "content": content}],
        "max_tokens": ARBITRATION_MAX_TOKENS,
        "temperature": 0.0  # Deterministic output for consistent box selection
    }
    
    response = requests.post(
        HF_ROUTER_URL,
        headers=headers,
        json=payload,
        timeout=timeout
    )
    
    if response.status_code == 429:
        raise Exception("HF Router rate limited")
    
    response.raise_for_status()
    
    result = response.json()
    return result["choices"][0]["message"]["content"]


# =============================================================================
# FRAME RANKING PROMPTS
# =============================================================================

FRAME_RANKING_PROMPT = """You are evaluating {n} photos of a junk pile for a removal service.
Your task is to rank these photos and select the BEST one for volume estimation.

## Criteria for Best Frame:
1. **Complete visibility**: The ENTIRE pile is visible, not cropped at edges
2. **Clear ground contact**: You can see where the pile meets the ground
3. **Good framing**: Pile is centered, good distance, not too close or far
4. **Single surface**: Ground under pile is one material (not grass+concrete)
5. **Minimal occlusion**: STRONGLY PENALIZE frames where trees, poles, fences, or objects are IN FRONT of the pile
6. **Full debris coverage**: ALL debris types (logs, bags, brush, branches, stumps) should be visible

## Important:
- A frame with a tree branch crossing in front of the pile is MUCH WORSE than a clear view
- Prefer frames where ALL debris (cut logs, garbage bags, brush, palm fronds) is visible without obstruction

## Output Format
Return ONLY valid JSON:
{{
  "best_frame_index": <0-based index of best frame>,
  "rankings": [
    {{"index": 0, "rank": 1, "reason": "why this rank"}},
    {{"index": 1, "rank": 2, "reason": "why this rank"}}
  ],
  "confidence": <0.0-1.0>
}}

The images are numbered 0 to {n_minus_1}. Select the best one."""


# =============================================================================
# BOX SELECTION PROMPTS
# =============================================================================

BOX_SELECTION_PROMPT = """This image shows numbered bounding boxes detected as potential junk piles.

## Boxes Detected:
{boxes_json}

## Your Task:
Select ALL boxes that contain junk/debris material. You may select MULTIPLE boxes if there are multiple piles.

## Material Types That Count as Junk:
- Garbage bags, trash, debris piles, household waste
- CUT logs, stumps, wood rounds, lumber (ON THE GROUND, disconnected from any tree)
- CUT branches, palm fronds, leaves, yard waste, vegetation piles (ON THE GROUND)
- Furniture, appliances, construction waste, pallets

## CRITICAL - What is NOT Junk (NEVER select these):
- LIVING TREES: standing trees with branches extending into the sky
- TREE CANOPY: boxes labeled "branches" that show leaves/branches CONNECTED to a tree trunk
- Any box where the TOP edge starts near y=0 (top of image) - this is almost always a tree canopy, NOT junk
- Background objects: vehicles, fences, buildings, people

## Key Distinction - "branches" label:
- LIVING tree branches: connected to trunk, in upper portion of image, extending into sky → NOT JUNK
- CUT branches: disconnected, lying on ground with other debris → IS JUNK

## Criteria for Selection:
1. Box contains actual junk/debris material ON THE GROUND
2. Minimizes empty ground or background area  
3. Covers the pile, not just a portion
4. REJECT any box where the TOP edge is in the upper 40% of the image AND it's labeled "branches" - that's a tree, not junk

## Example:
Input:
- Box 1: branches (0.45) @ [0, 0, 900, 350]  <- TOP of image, standing tree
- Box 2: trash (0.40) @ [50, 400, 300, 600]  <- garbage bags on ground
- Box 3: debris pile (0.50) @ [400, 350, 900, 700] <- yard waste/junk pile
- Box 4: furniture (0.35) @ [600, 420, 800, 650] <- old couch

Correct output:
{{"selected_box_numbers": [2, 3, 4], "multi_pile": true, "reason": "Trash bags, debris pile, and furniture are junk on ground. Box 1 rejected - tree branches in upper image."}}

## Output Format
Return ONLY a valid JSON object. No markdown, no explanation before or after.
{{
  "selected_box_numbers": [<1-based box numbers>],
  "multi_pile": <true/false>,
  "reason": "<brief explanation>"
}}"""


REFERENCE_GUIDED_BOX_PROMPT = """You are selecting junk boxes in a SECONDARY frame based on a REFERENCE frame.

## IMPORTANT: Different Perspectives
The reference and target images are taken from DIFFERENT ANGLES of the same scene.
Materials like logs, stumps, or debris may look VERY DIFFERENT from another viewpoint.
Focus on WHAT the material IS, not exactly how it looks visually.

## Reference Frame (Image 1):
The first image shows what we already identified as junk, highlighted in GREEN.
This includes ALL junk piles in the scene - there may be MULTIPLE separate piles.

## Target Frame (Image 2):
The second image shows YOUR target frame with numbered bounding boxes.
You need to find ALL the same junk pile(s) from this different angle.

## Boxes Detected:
{boxes_json}

## Your Task:
Select ALL boxes that contain junk materials shown in green in the reference.
Do NOT skip any pile - the junk may be in MULTIPLE separate locations.

## Material Matching Tips:
- Cut logs (cylindrical shapes) = junk, even if they look different from another angle
- Palm fronds / brush / debris = junk
- If the reference shows 2 piles, select boxes for BOTH piles

## Critical Rules:
- NEVER select boxes labeled "branches" where TOP edge is near y=0 (top of image) - this is a LIVING TREE, not junk
- Living tree branches: connected to trunk, extending into sky → REJECT
- Cut branches on ground with debris → OK to select
- Do NOT select boxes that cover mostly empty ground or sky
- Select ALL boxes that match ANY part of the green reference, not just the "most similar"

## Example:
Reference shows: debris pile (left) + scattered items (right) in GREEN
Target boxes:
- Box 1: pile @ [50, 350, 300, 550] <- matches debris on left
- Box 2: branches @ [0, 0, 900, 350] <- tree in sky, REJECT
- Box 3: junk @ [400, 300, 900, 650] <- matches scattered items
- Box 4: waste @ [200, 400, 400, 600] <- overlaps with debris

Correct output:
{{"selected_box_numbers": [1, 3, 4], "multi_pile": true, "reason": "Boxes 1, 3, 4 contain junk matching reference. Box 2 rejected - tree branches."}}

## Output Format
Return ONLY a valid JSON object. No markdown, no explanation before or after.
{{
  "selected_box_numbers": [<1-based box numbers - include ALL matching>],
  "multi_pile": <true/false>,
  "reason": "<brief explanation>"
}}"""


# =============================================================================
# MAIN FUNCTIONS
# =============================================================================

def rank_frames(frames: list) -> FrameRankingResult:
    """
    Stage 2: Qwen evaluates all frames and selects the best one.
    
    Args:
        frames: List of IngestedFrame objects
        
    Returns:
        FrameRankingResult with best_frame_id and rankings
    """
    if not ARBITRATION_ENABLED:
        print("[QWEN_ARB] Disabled → using first frame")
        return _default_frame_ranking(frames)
    
    if not frames:
        raise ValueError("No frames provided for ranking")
    
    if len(frames) == 1:
        # Only one frame - no need to call VLM
        return FrameRankingResult(
            best_frame_id=frames[0].metadata.image_id,
            best_frame_index=0,
            rankings=[{"frame_id": frames[0].metadata.image_id, "index": 0, "rank": 1, "reason": "only frame"}],
            confidence=1.0
        )
    
    frame_ids = [f.metadata.image_id for f in frames]
    
    try:
        print(f"[QWEN_ARB] Ranking {len(frames)} frames...")
        
        # Build content with all images
        content = []
        for frame in frames:
            pil_img = frame.get_pil()
            resized = _resize_for_vlm(pil_img)
            b64_uri = _pil_to_base64(resized)
            content.append({
                "type": "image_url",
                "image_url": {"url": b64_uri}
            })
        
        # Add prompt
        prompt = FRAME_RANKING_PROMPT.format(
            n=len(frames),
            n_minus_1=len(frames) - 1
        )
        content.append({"type": "text", "text": prompt})
        
        # Call VLM
        raw_output = _call_vlm(content)
        print(f"[QWEN_ARB] Frame ranking response: {len(raw_output)} chars")
        
        # Parse response
        parsed = _parse_json_resilient(raw_output)
        if parsed is None:
            print("[QWEN_ARB] JSON parse failed → using first frame")
            return _default_frame_ranking(frames)
        
        # Extract result
        best_idx = int(parsed.get("best_frame_index", 0))
        best_idx = max(0, min(best_idx, len(frames) - 1))  # Clamp to valid range
        
        rankings = []
        for r in parsed.get("rankings", []):
            idx = r.get("index", 0)
            if 0 <= idx < len(frames):
                rankings.append({
                    "frame_id": frame_ids[idx],
                    "index": idx,
                    "rank": r.get("rank", idx + 1),
                    "reason": r.get("reason", "")
                })
        
        result = FrameRankingResult(
            best_frame_id=frame_ids[best_idx],
            best_frame_index=best_idx,
            rankings=rankings or [{"frame_id": frame_ids[best_idx], "index": best_idx, "rank": 1, "reason": "selected"}],
            confidence=float(parsed.get("confidence", 0.7))
        )
        
        print(f"[QWEN_ARB] Best frame: {result.best_frame_id[:8]} (index={best_idx}, conf={result.confidence:.2f})")
        
        return result
        
    except Exception as e:
        print(f"[QWEN_ARB] Error in frame ranking: {e} → using first frame")
        return _default_frame_ranking(frames)


def select_pile_boxes(
    image_pil: Image.Image,
    candidate_boxes: list[dict],
) -> MultiBoxSelectionResult:
    """
    Stage 4 (v9.1): Qwen selects one or more pile boxes from DINO candidates.
    
    Supports multi-pile detection by allowing selection of multiple boxes.
    
    Args:
        image_pil: Original frame image (PIL)
        candidate_boxes: List of {box: [x1,y1,x2,y2], label: str, confidence: float}
        
    Returns:
        MultiBoxSelectionResult with all selected boxes
    """
    if not ARBITRATION_ENABLED:
        print("[QWEN_ARB] Disabled → using highest confidence box")
        fallback = _default_box_selection(candidate_boxes)
        return MultiBoxSelectionResult(
            selected_boxes=[{
                'index': fallback.selected_box_index,
                'box': fallback.selected_box,
                'label': fallback.selected_label,
                'confidence': fallback.confidence
            }],
            multi_pile=False,
            reason=fallback.reason
        )
    
    if not candidate_boxes:
        raise ValueError("No candidate boxes provided")
    
    if len(candidate_boxes) == 1:
        # Only one box - no need to call VLM
        box = candidate_boxes[0]
        return MultiBoxSelectionResult(
            selected_boxes=[{
                'index': 0,
                'box': box['box'],
                'label': box.get('label', 'pile'),
                'confidence': box.get('confidence', 1.0)
            }],
            multi_pile=False,
            reason="only candidate"
        )
    
    try:
        print(f"[QWEN_ARB] Selecting from {len(candidate_boxes)} boxes...")
        
        # Draw boxes on image
        annotated_img = _visualize_boxes(image_pil, candidate_boxes)
        resized = _resize_for_vlm(annotated_img)
        b64_uri = _pil_to_base64(resized)
        
        # Format boxes for prompt
        boxes_text = []
        for i, box in enumerate(candidate_boxes):
            x1, y1, x2, y2 = box['box']
            label = box.get('label', 'unknown')
            conf = box.get('confidence', 0.0)
            boxes_text.append(f"Box {i+1}: {label} (confidence: {conf:.2f}) at [{x1:.0f}, {y1:.0f}, {x2:.0f}, {y2:.0f}]")
        
        # Build content
        content = [
            {"type": "image_url", "image_url": {"url": b64_uri}},
            {"type": "text", "text": BOX_SELECTION_PROMPT.format(
                boxes_json="\n".join(boxes_text),
                n=len(candidate_boxes)
            )}
        ]
        
        # Call VLM
        raw_output = _call_vlm(content)
        print(f"[QWEN_ARB] Box selection response: {len(raw_output)} chars")
        
        # Parse response
        parsed = _parse_json_resilient(raw_output)
        if parsed is None:
            print("[QWEN_ARB] JSON parse failed → using highest confidence box")
            fallback = _default_box_selection(candidate_boxes)
            return MultiBoxSelectionResult(
                selected_boxes=[{
                    'index': fallback.selected_box_index,
                    'box': fallback.selected_box,
                    'label': fallback.selected_label,
                    'confidence': fallback.confidence
                }],
                multi_pile=False,
                reason=fallback.reason
            )
        
        # v9.1: Extract multiple box numbers
        selected_nums = parsed.get("selected_box_numbers", [])
        
        # Backward compatibility: handle old single-box format
        if not selected_nums and "selected_box_number" in parsed:
            selected_nums = [parsed["selected_box_number"]]
        
        # Ensure it's a list
        if isinstance(selected_nums, int):
            selected_nums = [selected_nums]
        
        # Convert 1-based to 0-based and validate
        selected_boxes = []
        for num in selected_nums:
            idx = int(num) - 1
            if 0 <= idx < len(candidate_boxes):
                box = candidate_boxes[idx]
                selected_boxes.append({
                    'index': idx,
                    'box': box['box'],
                    'label': box.get('label', 'pile'),
                    'confidence': box.get('confidence', 0.7)
                })
        
        # Fallback if no valid boxes selected
        if not selected_boxes:
            print("[QWEN_ARB] No valid boxes selected → using highest confidence")
            fallback = _default_box_selection(candidate_boxes)
            return MultiBoxSelectionResult(
                selected_boxes=[{
                    'index': fallback.selected_box_index,
                    'box': fallback.selected_box,
                    'label': fallback.selected_label,
                    'confidence': fallback.confidence
                }],
                multi_pile=False,
                reason=fallback.reason
            )
        
        multi_pile = parsed.get("multi_pile", len(selected_boxes) > 1)
        reason = parsed.get("reason", "selected by VLM")
        
        result = MultiBoxSelectionResult(
            selected_boxes=selected_boxes,
            multi_pile=multi_pile,
            reason=reason
        )
        
        box_indices = [b['index'] + 1 for b in selected_boxes]
        print(f"[QWEN_ARB] Selected boxes {box_indices}: multi_pile={multi_pile} - {reason[:50]}")
        
        return result
        
    except Exception as e:
        print(f"[QWEN_ARB] Error in box selection: {e} → using highest confidence box")
        fallback = _default_box_selection(candidate_boxes)
        return MultiBoxSelectionResult(
            selected_boxes=[{
                'index': fallback.selected_box_index,
                'box': fallback.selected_box,
                'label': fallback.selected_label,
                'confidence': fallback.confidence
            }],
            multi_pile=False,
            reason=fallback.reason
        )


def select_pile_box(
    image_pil: Image.Image,
    candidate_boxes: list[dict],
) -> BoxSelectionResult:
    """
    Stage 4: Backward-compatible wrapper that returns single best box.
    
    DEPRECATED: Use select_pile_boxes() for multi-pile support.
    
    Args:
        image_pil: Original frame image (PIL)
        candidate_boxes: List of {box: [x1,y1,x2,y2], label: str, confidence: float}
        
    Returns:
        BoxSelectionResult with the first selected box
    """
    multi_result = select_pile_boxes(image_pil, candidate_boxes)
    
    # Return first selected box for backward compatibility
    first_box = multi_result.selected_boxes[0]
    return BoxSelectionResult(
        selected_box_index=first_box['index'],
        selected_box=first_box['box'],
        selected_label=first_box['label'],
        confidence=first_box['confidence'],
        reason=multi_result.reason
    )


def select_pile_boxes_with_reference(
    reference_image: Image.Image,
    target_image: Image.Image,
    target_boxes: list[dict],
) -> MultiBoxSelectionResult:
    """
    v9.2: Select boxes in secondary frame guided by visual reference.
    
    Uses the best frame's mask overlay to show Qwen what junk looks like,
    then asks it to find the same junk in the secondary frame.
    
    Args:
        reference_image: Best frame with green mask overlay (RGB)
        target_image: Secondary frame (original, no overlay)
        target_boxes: DINO boxes detected in secondary frame
        
    Returns:
        MultiBoxSelectionResult with selected boxes
    """
    if not ARBITRATION_ENABLED:
        print("[QWEN_ARB] Disabled → using highest confidence box")
        fallback = _default_box_selection(target_boxes)
        return MultiBoxSelectionResult(
            selected_boxes=[{
                'index': fallback.selected_box_index,
                'box': fallback.selected_box,
                'label': fallback.selected_label,
                'confidence': fallback.confidence
            }],
            multi_pile=False,
            reason=fallback.reason
        )
    
    if not target_boxes:
        raise ValueError("No target boxes provided")
    
    if len(target_boxes) == 1:
        # Only one box - no need for VLM
        box = target_boxes[0]
        return MultiBoxSelectionResult(
            selected_boxes=[{
                'index': 0,
                'box': box['box'],
                'label': box.get('label', 'pile'),
                'confidence': box.get('confidence', 1.0)
            }],
            multi_pile=False,
            reason="only candidate"
        )
    
    try:
        print(f"[QWEN_ARB] Reference-guided selection from {len(target_boxes)} boxes...")
        
        # Draw boxes on target image
        annotated_target = _visualize_boxes(target_image, target_boxes)
        
        # Resize both images for VLM
        ref_resized = _resize_for_vlm(reference_image)
        target_resized = _resize_for_vlm(annotated_target)
        
        ref_b64 = _pil_to_base64(ref_resized)
        target_b64 = _pil_to_base64(target_resized)
        
        # Format boxes for prompt
        boxes_text = []
        for i, box in enumerate(target_boxes):
            x1, y1, x2, y2 = box['box']
            label = box.get('label', 'unknown')
            conf = box.get('confidence', 0.0)
            boxes_text.append(f"Box {i+1}: {label} (confidence: {conf:.2f}) at [{x1:.0f}, {y1:.0f}, {x2:.0f}, {y2:.0f}]")
        
        # Build content with TWO images
        content = [
            {"type": "image_url", "image_url": {"url": ref_b64}},      # Reference (Image 1)
            {"type": "image_url", "image_url": {"url": target_b64}},  # Target (Image 2)
            {"type": "text", "text": REFERENCE_GUIDED_BOX_PROMPT.format(
                boxes_json="\n".join(boxes_text)
            )}
        ]
        
        # Call VLM
        raw_output = _call_vlm(content)
        print(f"[QWEN_ARB] Reference-guided response: {len(raw_output)} chars")
        
        # Parse response (same logic as select_pile_boxes)
        parsed = _parse_json_resilient(raw_output)
        if parsed is None:
            print("[QWEN_ARB] JSON parse failed → using highest confidence box")
            fallback = _default_box_selection(target_boxes)
            return MultiBoxSelectionResult(
                selected_boxes=[{
                    'index': fallback.selected_box_index,
                    'box': fallback.selected_box,
                    'label': fallback.selected_label,
                    'confidence': fallback.confidence
                }],
                multi_pile=False,
                reason=fallback.reason
            )
        
        # Extract selected box numbers
        selected_nums = parsed.get("selected_box_numbers", [])
        if isinstance(selected_nums, int):
            selected_nums = [selected_nums]
        
        # Convert 1-based to 0-based and validate
        selected_boxes = []
        for num in selected_nums:
            idx = int(num) - 1
            if 0 <= idx < len(target_boxes):
                box = target_boxes[idx]
                selected_boxes.append({
                    'index': idx,
                    'box': box['box'],
                    'label': box.get('label', 'pile'),
                    'confidence': box.get('confidence', 0.7)
                })
        
        # Fallback if no valid boxes
        if not selected_boxes:
            print("[QWEN_ARB] No valid boxes from reference-guided → using highest confidence")
            fallback = _default_box_selection(target_boxes)
            return MultiBoxSelectionResult(
                selected_boxes=[{
                    'index': fallback.selected_box_index,
                    'box': fallback.selected_box,
                    'label': fallback.selected_label,
                    'confidence': fallback.confidence
                }],
                multi_pile=False,
                reason=fallback.reason
            )
        
        multi_pile = parsed.get("multi_pile", len(selected_boxes) > 1)
        reason = parsed.get("reason", "reference-guided selection")
        
        result = MultiBoxSelectionResult(
            selected_boxes=selected_boxes,
            multi_pile=multi_pile,
            reason=reason
        )
        
        box_indices = [b['index'] + 1 for b in selected_boxes]
        print(f"[QWEN_ARB] Reference-guided selected boxes {box_indices}: {reason[:50]}")
        
        return result
        
    except Exception as e:
        print(f"[QWEN_ARB] Error in reference-guided selection: {e}")
        fallback = _default_box_selection(target_boxes)
        return MultiBoxSelectionResult(
            selected_boxes=[{
                'index': fallback.selected_box_index,
                'box': fallback.selected_box,
                'label': fallback.selected_label,
                'confidence': fallback.confidence
            }],
            multi_pile=False,
            reason=fallback.reason
        )


# =============================================================================
# FALLBACK FUNCTIONS
# =============================================================================

def _default_frame_ranking(frames: list) -> FrameRankingResult:
    """Default ranking when VLM fails - use first frame."""
    return FrameRankingResult(
        best_frame_id=frames[0].metadata.image_id,
        best_frame_index=0,
        rankings=[{"frame_id": frames[0].metadata.image_id, "index": 0, "rank": 1, "reason": "default (VLM unavailable)"}],
        confidence=0.5
    )


def _default_box_selection(boxes: list[dict]) -> BoxSelectionResult:
    """Default selection when VLM fails - use highest confidence box."""
    # Sort by confidence, highest first
    sorted_boxes = sorted(
        enumerate(boxes), 
        key=lambda x: x[1].get('confidence', 0), 
        reverse=True
    )
    best_idx, best_box = sorted_boxes[0]
    
    return BoxSelectionResult(
        selected_box_index=best_idx,
        selected_box=best_box['box'],
        selected_label=best_box.get('label', 'pile'),
        confidence=best_box.get('confidence', 0.5),
        reason="default (highest confidence, VLM unavailable)"
    )
