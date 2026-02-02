"""
VLM Triage Module (Stage 0.5)
Uses Qwen2.5-VL 7B Instruct for pre-compute frame quality assessment.

Advisory only - geometry remains authoritative.
"""

import json
import re
import base64
from dataclasses import dataclass, field
from typing import Optional
from io import BytesIO
from PIL import Image

# =============================================================================
# CONFIGURATION
# =============================================================================

TRIAGE_TIMEOUT_S = 20              # Fail-open if exceeded (allow HF cold start)
TRIAGE_IMAGE_RESIZE_PX = 768       # Long-side resize for latency
TRIAGE_MAX_TOKENS = 1024           # JSON output only
TRIAGE_PROMPT_VERSION = "1.0"
TRIAGE_SCHEMA_VERSION = "1.0"
TRIAGE_ENABLED = True              # Master switch for rollback

# Thresholds for vref_ok computation
VREF_CONFIDENCE_MIN = 0.6
VREF_CROP_RISK_MAX = 0.4
VREF_MULTI_SURFACE_RISK_MAX = 0.5

# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class FrameSignals:
    """Continuous risk scores from VLM (0-1)."""
    crop_risk: float = 0.0
    occlusion_risk: float = 0.0
    multi_surface_risk: float = 0.0
    plane_fit_risk: float = 0.0      # v2: probability geometry will fail
    ground_visibility: float = 1.0
    confidence: float = 0.5


@dataclass
class FrameRoles:
    """Role suitability flags per frame."""
    footprint_ok: bool = True
    height_ok: bool = True
    union_ok: bool = True
    vref_ok: bool = False           # height_ok AND low-risk (preferred anchor)
    vref_candidate_ok: bool = False  # footprint_ok AND low-risk (fallback anchor)
    reason_codes: list[str] = field(default_factory=list)


@dataclass
class BBox:
    """Bounding box for pile and occluders."""
    pile: list[float] = field(default_factory=list)       # [x1, y1, x2, y2] normalized
    occluders: list[list[float]] = field(default_factory=list)


@dataclass
class TriageResult:
    """Complete triage output for a job."""
    schema_version: str = TRIAGE_SCHEMA_VERSION
    coverage_assessment: str = "complete"      # "complete" | "partial" | "poor"
    coverage_confidence: float = 0.5           # 0-1
    coverage_reason_codes: list[str] = field(default_factory=list)
    ranked_frames: list[str] = field(default_factory=list)
    frame_roles: dict[str, FrameRoles] = field(default_factory=dict)
    frame_signals: dict[str, FrameSignals] = field(default_factory=dict)
    bboxes: dict[str, BBox] = field(default_factory=dict)
    job_risks: list[str] = field(default_factory=list)
    retake: dict = field(default_factory=lambda: {"needed": False, "reason": None})
    triage_available: bool = False             # False if VLM failed
    # v1.1: Consistency tracking
    job_risk_sources: dict[str, str] = field(default_factory=dict)  # "multi_surface": "job_only"|"frame_derived"
    triage_trust: float = 1.0                  # 0..1 trust-calibration score
    vref_mode: str = "normal"                  # "normal"|"fallback"|"none"


# =============================================================================
# JSON PARSE RESILIENCE (3-step strategy)
# =============================================================================

def _repair_json(raw: str) -> str:
    """Attempt to repair common JSON issues from VLM output."""
    # Strip any non-JSON prefix/suffix (prose before/after JSON)
    # Find first { and last }
    start = raw.find('{')
    end = raw.rfind('}')
    if start != -1 and end != -1 and end > start:
        raw = raw[start:end+1]
    
    # Fix trailing commas before } or ]
    raw = re.sub(r',\s*}', '}', raw)
    raw = re.sub(r',\s*]', ']', raw)
    
    # Fix unquoted keys (simple cases)
    raw = re.sub(r'(\s*)(\w+)(\s*):', r'\1"\2"\3:', raw)
    
    # Fix single quotes to double quotes
    raw = raw.replace("'", '"')
    
    return raw


def _extract_json_block(raw: str) -> Optional[str]:
    """Extract the largest {...} block from text."""
    # Find all potential JSON objects
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


def _parse_triage_json(raw_output: str) -> Optional[dict]:
    """
    3-step JSON parse with resilience.
    Returns None if all steps fail (triggers fail-open).
    """
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
    
    # All attempts failed
    print(f"[VLM_TRIAGE] ⚠️ JSON parse failed after 3 attempts")
    return None


# =============================================================================
# VREF_OK COMPUTATION (Role-aware)
# =============================================================================

def _compute_vref_ok(roles: FrameRoles, signals: FrameSignals, job_only_multi: bool = False) -> bool:
    """
    Compute vref_ok (preferred V_ref anchor).
    Requires: height_ok AND low-risk AND confidence_ok
    
    If multi_surface is job_only (no per-frame attribution), 
    we allow multi_surface_risk check to pass.
    """
    low_risk = (
        signals.crop_risk < 0.3 and
        signals.occlusion_risk < 0.3 and
        (signals.multi_surface_risk < 0.3 or job_only_multi)
    )
    confidence_ok = signals.confidence > 0.5
    return roles.height_ok and low_risk and confidence_ok


def _compute_vref_candidate_ok(roles: FrameRoles, signals: FrameSignals) -> bool:
    """
    Compute vref_candidate_ok (fallback V_ref anchor).
    Used when no vref_ok exists.
    Requires: footprint_ok AND low crop/occlusion risk
    """
    return (
        roles.footprint_ok and
        signals.crop_risk < 0.3 and
        signals.occlusion_risk < 0.3
    )


# =============================================================================
# TRIAGE WEIGHT COMPUTATION
# =============================================================================

def compute_triage_weight(frame_id: str, triage: Optional[TriageResult]) -> float:
    """
    Compute soft weight multiplier from triage signals.
    Returns 1.0 if triage unavailable (fail-open).
    
    Trust-calibrated: when triage_trust is low, effect is reduced.
    """
    if not triage or not triage.triage_available:
        return 1.0
    
    signals = triage.frame_signals.get(frame_id)
    if not signals:
        return 1.0
    
    # Base weight from risk scores
    w_base = 1.0 - (
        0.6 * signals.crop_risk +
        0.5 * signals.multi_surface_risk +
        0.4 * signals.occlusion_risk
    )
    w_base = max(0.1, min(1.0, w_base))
    
    # Apply trust-calibration: lerp toward 1.0 when trust is low
    # w_effective = 1.0 + (w_base - 1.0) * trust
    trust = triage.triage_trust
    w_effective = 1.0 + (w_base - 1.0) * trust
    
    return max(0.1, min(1.0, w_effective))


# =============================================================================
# DEFAULT TRIAGE RESULT (fail-open)
# =============================================================================

def _create_default_triage(frame_ids: list[str]) -> TriageResult:
    """Create default triage result when VLM fails or is disabled."""
    result = TriageResult(
        triage_available=False,
        ranked_frames=frame_ids,  # Keep original order
        coverage_assessment="complete",  # Assume best case
        coverage_confidence=0.0,  # Low confidence in this assessment
    )
    
    # Default roles: all ok (fail-open)
    for fid in frame_ids:
        result.frame_roles[fid] = FrameRoles()
        result.frame_signals[fid] = FrameSignals()
    
    return result


# =============================================================================
# PROMPT TEMPLATE (v2 - geometry-aware discrimination)
# =============================================================================

TRIAGE_PROMPT = """You are analyzing {n_frames} images of a junk pile for GEOMETRIC volume estimation.
Your job is to predict which frames will work for plane-fitting, not just "look good."

## CRITICAL: Geometry Failure Causes
The volume system FAILS when:
- Ground plane has multiple surfaces (grass + concrete, slope, curb)
- Ground contact is hidden or unclear across the pile width  
- Pile occupies so much of the bottom that floor evidence is thin
- Reflections, puddles, or shadows obscure ground contact

## Per-Frame Signals (0.0-1.0)

1. crop_risk: Pile edges cut off at image boundary
2. occlusion_risk: Objects hiding parts of the pile
3. multi_surface_risk: CRITICAL - must be HIGH (≥0.6) if:
   - Visible curb/edge between surfaces under pile
   - Grass AND concrete both under pile footprint
   - Slope or driveway grade change visible
   - Pile spans two planes (one part higher/lower)
   - Shadows hide where pile meets ground
4. plane_fit_risk: Probability geometry will FAIL (0.0-1.0)
   - High if: multi-material ground, curb/slope, unclear ground contact,
     bottom band dominated by pile, reflections, heavy shadows at contact
5. ground_visibility: How clearly the pile-to-ground line is visible
6. confidence: Your confidence in these assessments

## Role Suitability

- footprint_ok: Good footprint if NOT cropped AND clear pile edges AND single surface
- height_ok: Good height if clear ground contact across width AND single surface AND plane_fit_risk < 0.4
- union_ok: Adds complementary view (different angle, not redundant)

## V_ref Selection (STRICT - typically 0-1 frames qualify)
vref_ok = "BEST single frame to anchor the whole job"
Requirements for vref_ok=true:
- Edges mostly visible (not cropped)
- Ground contact visible across a WIDE span
- Single-surface under pile (no curb/grass boundary)
- Not extreme close-range distortion
- plane_fit_risk < 0.3

**Only 0-1 frames should typically have vref_ok=true.** If unsure, set vref_ok=false.

## Anti-All-Zeros Rule
At least ONE frame must have a non-zero risk (>0.2) for crop_risk, occlusion_risk, 
multi_surface_risk, OR plane_fit_risk — unless you are EXTREMELY confident all frames 
are geometrically perfect. If you output all risks <0.2, set coverage_confidence <0.6.

## Reason Code Requirements
- If multi_surface_risk ≥ 0.3, reason_codes MUST include "multi_surface"
- If plane_fit_risk ≥ 0.4, reason_codes MUST include "floor_risk"  
- If vref_ok=true, reason_codes MUST include "clear_ground_contact" AND "single_surface"
- If height_ok=false, reason_codes MUST explain why (e.g. "ground_hidden", "multi_surface")

## Job-Level Assessment
- coverage_assessment: "complete" | "partial" | "poor"
- coverage_confidence: 0.0-1.0
- job_risks: multi_surface, curb_edge, slope, touching_wall, close_range, glare, shadow, low_light

Respond with ONLY valid JSON:
{{
  "coverage_assessment": "complete|partial|poor",
  "coverage_confidence": 0.0-1.0,
  "coverage_reason_codes": ["string"],
  "ranked_frames": ["frame_id_best", ...],
  "frame_roles": {{
    "frame_id": {{"footprint_ok": bool, "height_ok": bool, "union_ok": bool, "vref_ok": bool, "reason_codes": ["string"]}}
  }},
  "frame_signals": {{
    "frame_id": {{"crop_risk": 0.0-1.0, "occlusion_risk": 0.0-1.0, "multi_surface_risk": 0.0-1.0, "plane_fit_risk": 0.0-1.0, "ground_visibility": 0.0-1.0, "confidence": 0.0-1.0}}
  }},
  "job_risks": ["string"],
  "retake": {{"needed": bool, "reason": "string or null"}}
}}

Frame IDs: {frame_ids}
"""


# =============================================================================
# IMAGE PREPROCESSING
# =============================================================================

def _prepare_image_for_vlm(img: Image.Image, max_size: int = TRIAGE_IMAGE_RESIZE_PX) -> Image.Image:
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


# =============================================================================
# MAIN TRIAGE FUNCTION
# =============================================================================

# Global model cache (loaded once per container)
_vlm_model = None
_vlm_processor = None


# HuggingFace Router API config
HF_ROUTER_URL = "https://router.huggingface.co/v1/chat/completions"
HF_MODEL_ID = "Qwen/Qwen2.5-VL-7B-Instruct:hyperbolic"


def _call_vlm_api(frames: list, frame_ids: list[str]) -> str:
    """
    Call Qwen2.5-VL via HuggingFace Router API.
    
    Returns raw text output from the model.
    """
    import requests
    import os
    
    hf_token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    if not hf_token:
        raise ValueError("HF_TOKEN or HUGGING_FACE_HUB_TOKEN environment variable not set")
    
    headers = {
        "Authorization": f"Bearer {hf_token}",
        "Content-Type": "application/json"
    }
    
    # Build content with images + prompt
    content = []
    
    # Add all images as base64 data URIs
    for frame in frames:
        pil_img = frame.get_pil()
        resized = _prepare_image_for_vlm(pil_img)
        b64_uri = _pil_to_base64(resized)
        content.append({
            "type": "image_url",
            "image_url": {"url": b64_uri}
        })
    
    # Add text prompt
    prompt = TRIAGE_PROMPT.format(
        n_frames=len(frames),
        frame_ids=json.dumps(frame_ids)
    )
    content.append({"type": "text", "text": prompt})
    
    payload = {
        "model": HF_MODEL_ID,
        "messages": [{"role": "user", "content": content}],
        "max_tokens": TRIAGE_MAX_TOKENS
    }
    
    print(f"[VLM_TRIAGE] Calling HF Router API ({len(frames)} images)...")
    response = requests.post(
        HF_ROUTER_URL,
        headers=headers,
        json=payload,
        timeout=TRIAGE_TIMEOUT_S
    )
    
    # Rate limit handling
    if response.status_code == 429:
        print("[VLM_TRIAGE] ⚠️ Rate limited by HF Router → fail-open")
        raise Exception("HF Router rate limited")
    
    response.raise_for_status()
    
    result = response.json()
    raw_output = result["choices"][0]["message"]["content"]
    print(f"[VLM_TRIAGE] API response: {len(raw_output)} chars")
    
    return raw_output


def _parse_vlm_response(raw_json: dict, frame_ids: list[str]) -> TriageResult:
    """Convert parsed JSON to TriageResult with validation and trust calculation."""
    result = TriageResult(
        schema_version=TRIAGE_SCHEMA_VERSION,
        triage_available=True,
        coverage_assessment=raw_json.get("coverage_assessment", "complete"),
        coverage_confidence=float(raw_json.get("coverage_confidence", 0.5)),
        coverage_reason_codes=raw_json.get("coverage_reason_codes", []),
        ranked_frames=raw_json.get("ranked_frames", frame_ids),
        job_risks=raw_json.get("job_risks", []),
        retake=raw_json.get("retake", {"needed": False, "reason": None}),
    )
    
    # Parse frame roles and signals
    raw_roles = raw_json.get("frame_roles", {})
    raw_signals = raw_json.get("frame_signals", {})
    
    for fid in frame_ids:
        # Parse signals (v2: includes plane_fit_risk)
        sig_data = raw_signals.get(fid, {})
        signals = FrameSignals(
            crop_risk=float(sig_data.get("crop_risk", 0.0)),
            occlusion_risk=float(sig_data.get("occlusion_risk", 0.0)),
            multi_surface_risk=float(sig_data.get("multi_surface_risk", 0.0)),
            plane_fit_risk=float(sig_data.get("plane_fit_risk", 0.0)),  # v2
            ground_visibility=float(sig_data.get("ground_visibility", 1.0)),
            confidence=float(sig_data.get("confidence", 0.5)),
        )
        result.frame_signals[fid] = signals
        
        # Parse roles (v2: model may provide vref_ok directly)
        role_data = raw_roles.get(fid, {})
        model_vref = role_data.get("vref_ok")  # Model's direct output
        roles = FrameRoles(
            footprint_ok=bool(role_data.get("footprint_ok", True)),
            height_ok=bool(role_data.get("height_ok", True)),
            union_ok=bool(role_data.get("union_ok", True)),
            reason_codes=role_data.get("reason_codes", []),
        )
        # Use model's vref_ok if provided, otherwise compute later
        if model_vref is not None:
            roles.vref_ok = bool(model_vref)
        result.frame_roles[fid] = roles
    
    # =========================================================================
    # CONSISTENCY VALIDATION & TRUST CALCULATION
    # =========================================================================
    trust = 0.30  # Base: JSON parsed successfully
    
    # 1) Job risk source attribution
    for risk in result.job_risks:
        if risk == "multi_surface":
            max_multi = max((s.multi_surface_risk for s in result.frame_signals.values()), default=0.0)
            if max_multi >= 0.3:
                result.job_risk_sources[risk] = "frame_derived"
            else:
                result.job_risk_sources[risk] = "job_only"
        else:
            result.job_risk_sources[risk] = "job_only"
    
    # Check if multi_surface is job_only for vref computation
    job_only_multi = result.job_risk_sources.get("multi_surface") == "job_only"
    
    # 2) Compute vref_ok and vref_candidate_ok for each frame
    for fid in frame_ids:
        roles = result.frame_roles[fid]
        signals = result.frame_signals[fid]
        roles.vref_ok = _compute_vref_ok(roles, signals, job_only_multi)
        roles.vref_candidate_ok = _compute_vref_candidate_ok(roles, signals)
    
    # 3) Consistency score (+0.30)
    consistency_ok = True
    # If job_only, reduce trust slightly
    if "job_only" in result.job_risk_sources.values():
        consistency_ok = False
    trust += 0.30 if consistency_ok else 0.15
    
    # 4) Model confidence component (+0.20)
    trust += 0.20 if result.coverage_confidence > 0.6 else 0.10
    
    # 5) Utility: has useful outputs (+0.20)
    has_vref = any(r.vref_ok for r in result.frame_roles.values())
    has_roles = (
        any(r.footprint_ok for r in result.frame_roles.values()) and
        any(r.height_ok for r in result.frame_roles.values())
    )
    trust += 0.20 if (has_vref or has_roles) else 0.05
    
    # 6) Fallback vref selection if none exist
    if not any(r.vref_ok for r in result.frame_roles.values()):
        # Find best vref_candidate
        candidates = [(fid, result.frame_signals[fid]) 
                      for fid, r in result.frame_roles.items() if r.vref_candidate_ok]
        
        if candidates:
            # Pick lowest risk candidate  
            best_fid = min(candidates, key=lambda x: x[1].crop_risk + x[1].occlusion_risk)[0]
            result.frame_roles[best_fid].vref_ok = True
            result.vref_mode = "fallback"
            trust *= 0.8  # Reduce trust for fallback
            print(f"[VLM_TRIAGE] vref fallback: {best_fid[:8]} selected")
        else:
            result.vref_mode = "none"
            trust *= 0.6
            print("[VLM_TRIAGE] ⚠️ vref_mode=none (no candidates)")
    else:
        result.vref_mode = "normal"
    
    result.triage_trust = min(trust, 1.0)
    
    return result



def run_triage(frames: list) -> TriageResult:
    """
    Run VLM triage on all frames.
    
    Args:
        frames: List of IngestedFrame objects
        
    Returns:
        TriageResult (triage_available=False if VLM fails → fail-open)
    """
    if not TRIAGE_ENABLED:
        print("[VLM_TRIAGE] Disabled by TRIAGE_ENABLED=False")
        return _create_default_triage([f.metadata.image_id for f in frames])
    
    if not frames:
        return _create_default_triage([])
    
    frame_ids = [f.metadata.image_id for f in frames]
    
    try:
        # Call HuggingFace Router API
        raw_output = _call_vlm_api(frames, frame_ids)
        print(f"[VLM_TRIAGE] Raw output length: {len(raw_output)} chars")
        
        # Parse JSON (3-step resilience)
        parsed = _parse_triage_json(raw_output)
        if parsed is None:
            print("[VLM_TRIAGE] JSON parse failed → using defaults")
            return _create_default_triage(frame_ids)
        
        # Convert to TriageResult
        result = _parse_vlm_response(parsed, frame_ids)
        
        # Log summary
        print(f"[VLM_TRIAGE] Coverage: {result.coverage_assessment} "
              f"(conf={result.coverage_confidence:.2f})")
        print(f"[VLM_TRIAGE] Trust: {result.triage_trust:.2f}, vref_mode: {result.vref_mode}")
        print(f"[VLM_TRIAGE] Ranked: {[f[:8] for f in result.ranked_frames]}")
        print(f"[VLM_TRIAGE] Risks: {result.job_risks} (sources: {result.job_risk_sources})")
        for fid in frame_ids:
            roles = result.frame_roles.get(fid, FrameRoles())
            signals = result.frame_signals.get(fid, FrameSignals())
            print(f"[VLM_TRIAGE] {fid[:8]}: vref={roles.vref_ok}, vref_cand={roles.vref_candidate_ok}, "
                  f"fp={roles.footprint_ok}, h={roles.height_ok}, "
                  f"crop={signals.crop_risk:.2f}, multi={signals.multi_surface_risk:.2f}, "
                  f"plane_fit={signals.plane_fit_risk:.2f}")
        
        return result
        
    except Exception as e:
        print(f"[VLM_TRIAGE] ⚠️ Error: {e} → using defaults (fail-open)")
        return _create_default_triage(frame_ids)
