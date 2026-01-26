"""
v4.0 GPT Audit (Step 11)

Final validation and add-on detection using GPT-5-Pro via Replicate.
Flags missing items only when there's evidence.
"""

import json
import os
from typing import List
from .utils import vlog


# Replicate model version for GPT-5-Pro
GPT5_PRO_VERSION = "openai/gpt-5-pro"


def run_gpt_audit(
    fused_items: List[dict],
    volumes: dict,
    trust_metrics: dict
) -> dict:
    """
    Final audit and validation with GPT-5-Pro via Replicate.
    
    Responsibilities:
    - Validate item list is reasonable
    - Flag missing items (ONLY if evidence exists)
    - Detect add-on requirements (e-waste, heavy, etc.)
    - Rate overall confidence
    
    Args:
        fused_items: List of fused, classified items
        volumes: Volume computation results
        trust_metrics: Coverage and mask statistics
        
    Returns:
        Audit result dict
    """
    import replicate  # Lazy import
    
    vlog(f"🔍 Running GPT-5-Pro audit on {len(fused_items)} items...")
    
    # Build audit input
    items_summary = []
    for item in fused_items:
        items_summary.append({
            "label": item.get("canonical_label", item.get("raw_label", "unknown")),
            "category": item.get("category", "unknown"),
            "size": item.get("size_bucket", "medium"),
            "has_mask": item.get("has_mask", False),
            "confidence": round(item.get("classifier_confidence", 0.5), 2)
        })
    
    prompt = f"""You are auditing a junk removal quote for accuracy and completeness.

DETECTED ITEMS ({len(fused_items)} total):
{json.dumps(items_summary, indent=2)}

VOLUME CALCULATION:
- Final volume: {volumes.get('final_volume', 0)} yd³
- Lane A (Occupancy): {volumes.get('lane_a_occupancy', 0)} yd³
- Lane B (Catalog): {volumes.get('lane_b_catalog', 0)} yd³
- Dominant method: {volumes.get('dominant', 'unknown')}

TRUST METRICS:
- Coverage: {trust_metrics.get('mask_coverage_pct', 0)}%
- Items with masks: {trust_metrics.get('items_with_masks', 0)}/{len(fused_items)}
- Remainder ratio: {trust_metrics.get('remainder_ratio', 0)*100:.1f}%

AUDIT TASKS:
1. Are the detected items reasonable for a junk removal job?
2. Flag any items that should have add-ons:
   - "ewaste": TVs, monitors, computers, electronics
   - "heavy": Refrigerators, pianos, safes, concrete
   - "two_person_lift": Large furniture, appliances
   - "hazmat": Tires, paint, chemicals
3. Are there likely missing items? (Only flag if there's evidence from patterns)
4. Rate your confidence in this quote (0.0-1.0)

DO NOT GUESS. Only flag issues you have evidence for.

Return ONLY valid JSON with this exact structure:
{{
  "validation": "PASS" or "REVIEW" or "FAIL",
  "missing_items": [],
  "add_on_flags": [],
  "confidence": 0.0,
  "notes": "Brief explanation"
}}"""

    try:
        # Run GPT-5-Pro via Replicate
        output = replicate.run(
            GPT5_PRO_VERSION,
            input={
                "prompt": prompt,
                "max_tokens": 500,
            }
        )
        
        # Parse output - Replicate returns string or iterator
        response_text = ""
        if isinstance(output, str):
            response_text = output
        elif hasattr(output, "__iter__"):
            response_text = "".join(list(output))
        
        # Clean up response (remove markdown code blocks if present)
        response_text = response_text.strip()
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            response_text = "\n".join(lines[1:-1])
        
        result = json.loads(response_text)
        
        vlog(f"   ✅ Audit: {result.get('validation', 'unknown')} (conf={result.get('confidence', 0):.2f})")
        
        # Safely log add-on flags (handle both strings and dicts)
        if result.get("add_on_flags"):
            flags = result["add_on_flags"]
            flag_strs = [f.get("name", str(f)) if isinstance(f, dict) else str(f) for f in flags]
            vlog(f"   ➕ Add-ons: {', '.join(flag_strs)}")
        
        # Safely log missing items (handle both strings and dicts)
        if result.get("missing_items"):
            items = result["missing_items"]
            item_strs = [i.get("label", str(i)) if isinstance(i, dict) else str(i) for i in items]
            vlog(f"   ⚠️ Missing: {', '.join(item_strs)}")
        
        return result
        
    except Exception as e:
        vlog(f"   ❌ Audit failed: {e}")
        return {
            "validation": "REVIEW",
            "missing_items": [],
            "add_on_flags": [],
            "confidence": 0.5,
            "notes": f"Audit failed: {str(e)}",
            "error": str(e)
        }
