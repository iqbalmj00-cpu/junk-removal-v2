"""
Stage 6.5: Foreman Audit (Sanity Check)
Goal: Use GPT vision to validate the physics-based volume estimate.
Runs AFTER fusion, BEFORE output.
"""

import os
import json
import base64
from dataclasses import dataclass, field
from typing import Optional
import requests


@dataclass
class AuditResult:
    """Result of the Foreman Audit stage."""
    status: str  # "PASS" or "FAIL"
    visual_volume_estimate: str  # e.g., "3-5 cubic yards"
    confidence_score: float  # 0.0 to 1.0
    flag_for_human_review: bool
    missing_items: list[str] = field(default_factory=list)
    audit_reason: str = ""
    raw_response: Optional[dict] = None
    error: Optional[str] = None


# Model configuration
AUDIT_MODEL = "gpt-4.1-2025-04-14"  # Using latest available vision model

SYSTEM_PROMPT = """You are the Senior Audit Foreman for a junk removal company. You are reviewing an automated volume estimate.

Reference:
- 1 pickup truck load ≈ 2.5–3.0 cubic yards
- 1 typical dump truck load ≈ 12–14 cubic yards
- A standard washing machine ≈ 0.15 cubic yards
- A couch ≈ 0.5–0.8 cubic yards
- A mattress (queen) ≈ 0.35 cubic yards

Task:
1) Decide if the provided volume is physically plausible for the image.
2) Identify obvious major items in the image that appear missing from the detected list.
3) If the estimate seems wrong, do NOT invent a new exact number; provide a plausible visual range.

Rules:
- Return ONLY valid JSON (no markdown, no code fences).
- Use status: "PASS" or "FAIL".
- If uncertain, set flag_for_human_review=true and status="PASS".
- audit_reason must be <= 220 characters.
- confidence_score: 0.0 = very uncertain, 1.0 = highly confident in your assessment."""


def _encode_image_to_base64(image_path: str) -> str:
    """Encode an image file to base64."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def _get_image_media_type(image_path: str) -> str:
    """Get the media type from file extension."""
    ext = image_path.lower().split(".")[-1]
    if ext in ("jpg", "jpeg"):
        return "image/jpeg"
    elif ext == "png":
        return "image/png"
    elif ext == "webp":
        return "image/webp"
    elif ext == "gif":
        return "image/gif"
    return "image/jpeg"  # Default


def run_foreman_audit(
    best_image_path: str,
    final_volume_cy: float,
    uncertainty_min: float,
    uncertainty_max: float,
    frame_volumes: list[float],
    detected_items: list[str],
    flags: list[str] = None
) -> AuditResult:
    """
    Stage 6.5: Run Foreman Audit to validate the physics estimate.
    
    Args:
        best_image_path: Path to the highest quality frame image
        final_volume_cy: Final fused volume in cubic yards
        uncertainty_min: Lower bound of uncertainty range
        uncertainty_max: Upper bound of uncertainty range
        frame_volumes: List of per-frame volumes for context
        detected_items: List of detected items from Lane A
        flags: Optional list of warning flags (uncalibrated, low_diversity, etc.)
    
    Returns:
        AuditResult with PASS/FAIL status and details
    """
    print(f"[Audit] Running Foreman Audit on best-view image...")
    
    # Check for OpenAI API key
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("[Audit] Warning: No OPENAI_API_KEY found, skipping audit")
        return AuditResult(
            status="PASS",
            visual_volume_estimate="N/A",
            confidence_score=0.0,
            flag_for_human_review=True,
            audit_reason="Audit skipped - no API key",
            error="No OPENAI_API_KEY environment variable"
        )
    
    # Build user prompt
    items_str = ", ".join(detected_items) if detected_items else "None detected"
    volumes_str = ", ".join([f"{v:.1f}" for v in frame_volumes])
    flags_str = ", ".join(flags) if flags else "None"
    
    user_prompt = f"""[Calculated Data]
- Total Volume: {final_volume_cy:.1f} cubic yards
- Uncertainty Range: {uncertainty_min:.1f} to {uncertainty_max:.1f} cubic yards
- Frame Volumes: [{volumes_str}]
- Detected Items: {items_str}
- Flags: {flags_str}

[Image Attached]
Evaluate this quote:
1) Does the visual pile roughly match {final_volume_cy:.1f} yards?
2) Are obvious major items missing from Detected Items?

Return JSON:
{{
  "status": "PASS",
  "visual_volume_estimate": "string",
  "confidence_score": 0.0,
  "flag_for_human_review": false,
  "missing_items": ["string"],
  "audit_reason": "string"
}}"""

    try:
        # Encode image
        image_b64 = _encode_image_to_base64(best_image_path)
        media_type = _get_image_media_type(best_image_path)
        
        # Build API request
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": AUDIT_MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{media_type};base64,{image_b64}",
                                "detail": "low"  # Use low detail to reduce cost
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 300,
            "temperature": 0.1  # Low temp for consistent output
        }
        
        # Call OpenAI API
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        
        result_data = response.json()
        content = result_data["choices"][0]["message"]["content"]
        
        # Parse JSON response
        # Clean up any markdown fences if present
        content = content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        content = content.strip()
        
        audit_json = json.loads(content)
        
        # Build result
        result = AuditResult(
            status=audit_json.get("status", "PASS"),
            visual_volume_estimate=audit_json.get("visual_volume_estimate", "unknown"),
            confidence_score=float(audit_json.get("confidence_score", 0.5)),
            flag_for_human_review=audit_json.get("flag_for_human_review", False),
            missing_items=audit_json.get("missing_items", []),
            audit_reason=audit_json.get("audit_reason", ""),
            raw_response=audit_json
        )
        
        # Log result
        print(f"[Audit] Status: {result.status}")
        print(f"[Audit] Visual estimate: {result.visual_volume_estimate}")
        print(f"[Audit] Confidence: {result.confidence_score:.2f}")
        if result.flag_for_human_review:
            print(f"[Audit] ⚠️ FLAGGED FOR HUMAN REVIEW")
        if result.missing_items:
            print(f"[Audit] Missing items: {result.missing_items}")
        print(f"[Audit] Reason: {result.audit_reason}")
        
        return result
        
    except json.JSONDecodeError as e:
        print(f"[Audit] Error parsing JSON response: {e}")
        return AuditResult(
            status="PASS",
            visual_volume_estimate="unknown",
            confidence_score=0.0,
            flag_for_human_review=True,
            audit_reason="Failed to parse audit response",
            error=str(e)
        )
    except requests.RequestException as e:
        print(f"[Audit] API request failed: {e}")
        return AuditResult(
            status="PASS",
            visual_volume_estimate="unknown",
            confidence_score=0.0,
            flag_for_human_review=True,
            audit_reason="Audit API request failed",
            error=str(e)
        )
    except Exception as e:
        print(f"[Audit] Unexpected error: {e}")
        return AuditResult(
            status="PASS",
            visual_volume_estimate="unknown",
            confidence_score=0.0,
            flag_for_human_review=True,
            audit_reason="Audit failed unexpectedly",
            error=str(e)
        )


def select_best_view_image(
    frames: list,
    floor_qualities: dict[str, str],
    depth_confidences: dict[str, float]
) -> Optional[str]:
    """
    Select the best-view image based on quality metrics.
    
    Returns the path to the best image, or None if no suitable image found.
    """
    best_score = -1
    best_path = None
    
    for frame in frames:
        frame_id = frame.metadata.image_id
        
        # Score components
        floor_q = floor_qualities.get(frame_id, "unknown")
        floor_score = 1.0 if floor_q == "good" else 0.6 if floor_q == "noisy" else 0.2
        
        depth_score = depth_confidences.get(frame_id, 0.5)
        
        # Combined score
        score = floor_score * 0.5 + depth_score * 0.5
        
        if score > best_score:
            best_score = score
            best_path = frame.metadata.original_path
    
    return best_path
