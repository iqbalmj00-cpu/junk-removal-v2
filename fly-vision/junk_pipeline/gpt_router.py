"""
GPT-4o Pipeline Router

Classifies junk piles into 4 modes and selects processing knobs.
Called after Stage 2 when ambiguity signals are detected.
"""

import json
import base64
from dataclasses import dataclass, field
from typing import Optional
import os


@dataclass
class RoutingDecision:
    """Result from GPT-4o routing."""
    mode: str = "A"  # A, B, C, D
    pile_type: str = "household"
    pile_density: str = "loose"  # solid, loose, sparse
    density_confidence: str = "medium"  # high, medium, low
    background_risks: list[str] = field(default_factory=list)
    pile_touches_background: bool = False
    veg_policy: str = "safe_only"  # safe_only, include_vegetation, none
    retake_advice: str = "none"
    triggered_by: str = "default"  # Which signal triggered router
    router_called: bool = False


# ============================================================================
# TRIGGER THRESHOLDS
# ============================================================================

TRIGGER_THRESHOLDS = {
    "mask_coverage_max": 0.55,
    "safe_bg_overlap_max": 0.15,
}


# ============================================================================
# MODE CONFIGURATIONS
# ============================================================================

MODE_CONFIGS = {
    "A": {  # Household / solid-ish junk
        "z_split_strict": False,
        "density_crop": False,
        "height_cap_m": 2.5,
        "uncertainty_boost": 1.0,
        "description": "household/solid-ish junk (furniture, boxes, bags)"
    },
    "B": {  # Yard Waste
        "z_split_strict": False,
        "density_crop": True,  # Bushes/trees common
        "height_cap_m": 2.0,
        "uncertainty_boost": 1.3,
        "description": "yard waste (branches, leaves, brush)"
    },
    "C": {  # Construction Debris
        "z_split_strict": True,  # Background scaffolding/fences common
        "density_crop": False,
        "height_cap_m": 4.0,
        "uncertainty_boost": 1.0,
        "description": "construction debris (drywall, lumber, rubble)"
    },
    "D": {  # Hard Scene
        "z_split_strict": True,
        "density_crop": True,
        "height_cap_m": 2.5,
        "uncertainty_boost": 2.0,
        "description": "hard scene (merged with background, needs retake)"
    },
}


def get_mode_config(mode: str) -> dict:
    """Get configuration for a routing mode. Falls back to A if invalid."""
    return MODE_CONFIGS.get(mode, MODE_CONFIGS["A"])


# ============================================================================
# PROMPTS
# ============================================================================

ROUTER_SYSTEM_PROMPT = """You are a routing controller for a junk-pile volume estimator. You do NOT estimate volume, dimensions, or distance.

You must output JSON only. No markdown, no commentary.

You choose a processing mode and safeguards based on the images. Use only these enum values and keys.

Allowed values:
pile_type: household | yard_waste | construction | mixed
pile_density: solid | loose | sparse
density_confidence: high | medium | low
background_risks: any subset of [tree_or_hedge, fence_or_wall, building, sky, vehicle, person, reflective_surface, indoor_clutter, none]
recommended_mode: A | B | C | D
semantic_subtraction_policy: safe_only | include_vegetation | none
retake_advice: none | ask_for_more_ground | avoid_tree_background | use_1x_step_back | add_side_angle | add_top_down_angle

Pile density definitions:
solid: stacked boxes, bagged material on pallet, furniture - fills ~90% of bounding box
loose: mixed debris bags piled together - fills ~85% of bounding box
sparse: brush pile, scattered items, yard waste - fills ~70% of bounding box

Mode definitions:
A: household/solid-ish junk (furniture, boxes, bags)
B: yard waste (branches, leaves, brush) — never subtract vegetation
C: construction debris (drywall, lumber, rubble)
D: hard scene (pile merged with hedge/fence/wall, heavy occlusion, strong background contamination) — conservative and likely needs retake

Semantic subtraction policies:
safe_only: subtract sky/building/fence/person/vehicle (never ground/terrain)
include_vegetation: also subtract vegetation/tree/plant only when vegetation is clearly background behind a non-yard-waste pile
none: do not subtract semantics (rare)

If uncertain, choose the safer option:
- avoid include_vegetation unless you are confident it is not yard waste
- choose Mode D if pile touches/merges with background

Return exactly this JSON schema with no extra keys:
{
  "pile_type": "...",
  "pile_density": "...",
  "density_confidence": "...",
  "background_risks": ["..."],
  "pile_touches_background": true/false,
  "recommended_mode": "...",
  "semantic_subtraction_policy": "...",
  "retake_advice": "..."
}"""


USER_PROMPT_TEMPLATE = """Analyze these photos of the same junk pile. Each image has a frame_id.

Goal: choose routing settings only (not volume). Output JSON only.

Frame IDs in order:
{FRAME_LIST}

Context:
- scene_guess: {SCENE_GUESS}
- note: {NOTE}

Return the JSON now."""


# ============================================================================
# TRIGGER COMPUTATION
# ============================================================================

def compute_stage2_triggers(perception_results: list) -> dict:
    """
    Compute trigger signals from Stage 2 perception results.
    
    Args:
        perception_results: List of PerceptionResult from Stage 2
        
    Returns:
        Dictionary of trigger signals
    """
    import numpy as np
    
    mask_coverages = []
    safe_overlaps = []
    veg_overlaps = []
    
    for p in perception_results:
        # Mask coverage from Lane B
        mask_coverages.append(p.lane_b.bulk_area_ratio)
        
        # Background overlaps from Lane D
        if p.lane_d and p.lane_b.bulk_mask_np is not None:
            bulk_mask = p.lane_b.bulk_mask_np
            bulk_sum = bulk_mask.sum()
            
            if p.lane_d.safe_bg_mask_np is not None and bulk_sum > 0:
                safe_overlap = (bulk_mask & p.lane_d.safe_bg_mask_np).sum()
                safe_overlaps.append(safe_overlap / bulk_sum)
            
            if p.lane_d.risky_bg_mask_np is not None and bulk_sum > 0:
                veg_overlap = (bulk_mask & p.lane_d.risky_bg_mask_np).sum()
                veg_overlaps.append(veg_overlap / bulk_sum)
    
    return {
        "mask_coverage_max": max(mask_coverages) if mask_coverages else 0,
        "safe_bg_overlap_max": max(safe_overlaps) if safe_overlaps else 0,
        "veg_overlap_max": max(veg_overlaps) if veg_overlaps else 0,
    }


def should_trigger_router(signals: dict) -> tuple[bool, str]:
    """
    Determine if router should be triggered based on signals.
    
    Returns:
        (should_trigger, reason)
    """
    if signals["mask_coverage_max"] > TRIGGER_THRESHOLDS["mask_coverage_max"]:
        return True, f"mask_coverage={signals['mask_coverage_max']:.0%}"
    
    if signals["safe_bg_overlap_max"] > TRIGGER_THRESHOLDS["safe_bg_overlap_max"]:
        return True, f"safe_bg_overlap={signals['safe_bg_overlap_max']:.0%}"
    
    return False, "clean_signals"


# ============================================================================
# FRAME SELECTION
# ============================================================================

def select_routing_frames(frames: list, perception_results: list) -> list:
    """
    Select 2 frames for routing: max mask + max context.
    
    Args:
        frames: List of Frame objects
        perception_results: List of PerceptionResult
        
    Returns:
        List of 1-2 Frame objects
    """
    if not frames or not perception_results:
        return []
    
    n = len(perception_results)
    
    # Frame with max SAM mask area
    max_mask_idx = max(range(n),
        key=lambda i: perception_results[i].lane_b.bulk_area_ratio)
    
    # Frame with max ground/context (highest floor area)
    max_context_idx = 0
    max_floor = 0
    for i, p in enumerate(perception_results):
        if p.lane_d and p.lane_d.ground_area_ratio > max_floor:
            max_floor = p.lane_d.ground_area_ratio
            max_context_idx = i
    
    selected_indices = [max_mask_idx]
    if max_context_idx != max_mask_idx:
        selected_indices.append(max_context_idx)
    
    return [frames[i] for i in selected_indices]


# ============================================================================
# GPT-4o CALL
# ============================================================================

def call_gpt_router(frames: list, context: dict) -> dict:
    """
    Call GPT-4o to classify pile and get routing decision.
    
    Args:
        frames: List of Frame objects (1-2 frames)
        context: Dictionary with scene_guess, note
        
    Returns:
        Parsed JSON response from GPT-4o
    """
    try:
        import openai
    except ImportError:
        print("[ROUTER] OpenAI not available, using default")
        return {}
    
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("[ROUTER] OPENAI_API_KEY not set, using default")
        return {}
    
    client = openai.OpenAI(api_key=api_key)
    
    # Build image content
    images = []
    frame_list = []
    for i, frame in enumerate(frames):
        # Get base64 from frame - IngestedFrame uses data_uri
        if hasattr(frame, 'data_uri') and frame.data_uri:
            # data_uri format: "data:image/jpeg;base64,{base64_string}"
            images.append({
                "type": "image_url",
                "image_url": {"url": frame.data_uri}
            })
        elif hasattr(frame, 'working_b64') and frame.working_b64:
            images.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{frame.working_b64}"}
            })
        else:
            continue
        
        frame_list.append(f"{i+1}) {frame.metadata.image_id[:8]}")
    
    if not images:
        print("[ROUTER] No valid images, using default")
        return {}
    
    # Build user prompt
    user_text = USER_PROMPT_TEMPLATE.format(
        FRAME_LIST="\n".join(frame_list),
        SCENE_GUESS=context.get("scene_guess", "unknown"),
        NOTE=context.get("note", "")
    )
    
    user_content = images + [{"type": "text", "text": user_text}]
    
    try:
        response = client.chat.completions.create(
            model="chatgpt-4o-latest",
            messages=[
                {"role": "system", "content": ROUTER_SYSTEM_PROMPT},
                {"role": "user", "content": user_content}
            ],
            response_format={"type": "json_object"},
            max_tokens=200,
            timeout=8.0
        )
        
        content = response.choices[0].message.content
        return json.loads(content)
        
    except Exception as e:
        print(f"[ROUTER] GPT-4o error: {e}")
        return {}


# ============================================================================
# GUARDRAILS
# ============================================================================

def apply_guardrails(gpt_output: dict, lane_a_labels: list = None) -> RoutingDecision:
    """
    Apply hard guardrails to GPT output.
    
    Args:
        gpt_output: Raw JSON from GPT-4o
        lane_a_labels: List of labels from Lane A (YOLO detections)
        
    Returns:
        RoutingDecision with guardrails applied
    """
    if lane_a_labels is None:
        lane_a_labels = []
    
    # Validate mode
    mode = gpt_output.get("recommended_mode", "A")
    if mode not in ["A", "B", "C", "D"]:
        mode = "A"
    
    pile_type = gpt_output.get("pile_type", "household")
    if pile_type not in ["household", "yard_waste", "construction", "mixed"]:
        pile_type = "household"
    
    veg_policy = gpt_output.get("semantic_subtraction_policy", "safe_only")
    if veg_policy not in ["safe_only", "include_vegetation", "none"]:
        veg_policy = "safe_only"
    
    background_risks = gpt_output.get("background_risks", [])
    pile_touches_background = gpt_output.get("pile_touches_background", False)
    retake_advice = gpt_output.get("retake_advice", "none")
    
    # HARD RULE 1: yard_waste → never subtract vegetation
    if pile_type == "yard_waste":
        veg_policy = "safe_only"
        if mode not in ["B", "D"]:
            mode = "B"
    
    # HARD RULE 2: Lane A detected furniture + yard_waste → override to mixed
    furniture_labels = {"sofa", "couch", "chair", "table", "desk", "mattress", 
                       "refrigerator", "washer", "dryer", "bed"}
    lane_a_lower = [l.lower() for l in lane_a_labels]
    if pile_type == "yard_waste" and any(f in lane_a_lower for f in furniture_labels):
        pile_type = "mixed"
        mode = "A"
        print(f"[ROUTER] Override: yard_waste + furniture → mixed, Mode A")
    
    # HARD RULE 3: include_vegetation only if tree_or_hedge in risks AND not yard_waste
    if veg_policy == "include_vegetation":
        if pile_type == "yard_waste":
            veg_policy = "safe_only"
        elif "tree_or_hedge" not in background_risks:
            veg_policy = "safe_only"
    
    # Parse pile_density
    pile_density = gpt_output.get("pile_density", "loose")
    if pile_density not in ["solid", "loose", "sparse"]:
        pile_density = "loose"
    
    # Parse density_confidence
    density_confidence = gpt_output.get("density_confidence", "medium")
    if density_confidence not in ["high", "medium", "low"]:
        density_confidence = "medium"
    
    return RoutingDecision(
        mode=mode,
        pile_type=pile_type,
        pile_density=pile_density,
        density_confidence=density_confidence,
        background_risks=background_risks,
        pile_touches_background=pile_touches_background,
        veg_policy=veg_policy,
        retake_advice=retake_advice,
        router_called=True
    )


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def route_pipeline(
    frames: list,
    perception_results: list,
    lane_a_labels: list = None
) -> RoutingDecision:
    """
    Main router entry point. Call after Stage 2.
    
    Args:
        frames: List of Frame objects
        perception_results: List of PerceptionResult from Stage 2
        lane_a_labels: Optional list of Lane A detection labels
        
    Returns:
        RoutingDecision with mode and knobs
    """
    # Compute triggers
    signals = compute_stage2_triggers(perception_results)
    should_trigger, trigger_reason = should_trigger_router(signals)
    
    if not should_trigger:
        print(f"[ROUTER] Skipped ({trigger_reason}), defaulting to Mode A")
        return RoutingDecision(
            mode="A",
            veg_policy="safe_only",
            triggered_by=trigger_reason
        )
    
    print(f"[ROUTER] Triggered: {trigger_reason}")
    
    # Select frames
    routing_frames = select_routing_frames(frames, perception_results)
    if not routing_frames:
        print("[ROUTER] No frames for routing, defaulting to Mode A")
        return RoutingDecision(mode="A", veg_policy="safe_only")
    
    # Build context
    scene_guess = "unknown"
    if perception_results and perception_results[0].lane_c:
        scene_guess = perception_results[0].lane_c.scene_type.value
    
    context = {
        "scene_guess": scene_guess,
        "note": f"safe_bg_overlap={signals['safe_bg_overlap_max']:.0%}, veg_overlap={signals['veg_overlap_max']:.0%}"
    }
    
    # Call GPT-4o
    gpt_output = call_gpt_router(routing_frames, context)
    
    if not gpt_output:
        print("[ROUTER] GPT-4o returned empty, defaulting to Mode A")
        return RoutingDecision(mode="A", veg_policy="safe_only", triggered_by=trigger_reason)
    
    # Apply guardrails
    decision = apply_guardrails(gpt_output, lane_a_labels)
    decision.triggered_by = trigger_reason
    
    print(f"[ROUTER] Decision: mode={decision.mode}, pile={decision.pile_type}, veg={decision.veg_policy}")
    if decision.background_risks:
        print(f"[ROUTER] Risks: {decision.background_risks}")
    if decision.retake_advice != "none":
        print(f"[ROUTER] Retake advice: {decision.retake_advice}")
    
    return decision
