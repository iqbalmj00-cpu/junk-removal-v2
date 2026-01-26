"""
v4.0 GPT Classifier (Step 7)

Batch classification of discrete items using GPT-4o-mini.
Uses proposal_id as PRIMARY KEY - never index-based mapping.
Returns consistent JSON contract: {"items": [...]}
"""

import json
import os
from typing import List
from .constants import CANONICAL_LABELS
from .utils import vlog


def run_gpt_classifier(discrete_items: List[dict]) -> List[dict]:
    """
    Batch classify discrete items with GPT-4o-mini.
    
    CRITICAL IMPLEMENTATION RULES:
    1. proposal_id is passed through and returned (PRIMARY KEY)
    2. JSON contract is {"items": [...]} (consistent)
    3. Results are merged back by proposal_id (never by index)
    
    Args:
        discrete_items: List of proposal dicts with proposal_id, raw_label, etc.
        
    Returns:
        Updated proposals with classification attached
    """
    import openai  # Lazy import
    openai.api_key = os.environ.get("OPENAI_API_KEY")
    
    if not discrete_items:
        vlog("📋 No items to classify")
        return []
    
    vlog(f"📋 Classifying {len(discrete_items)} items with GPT-4o-mini...")
    
    # Build classifier input with proposal_id as PRIMARY KEY
    items_for_classifier = []
    for item in discrete_items:
        items_for_classifier.append({
            "proposal_id": item["proposal_id"],  # MUST BE PRESERVED
            "raw_label": item["raw_label"],
            "score": round(item["score"], 3),
            "has_mask": item.get("has_mask", False),
            "mask_area_ratio": round(item.get("mask_area_ratio") or 0, 4),
        })
    
    prompt = f"""You are a junk removal pricing classifier.

Classify these items detected in customer photos for junk removal pricing.

For EACH item, return:
- proposal_id: (MUST match input EXACTLY - this is the join key)
- verdict: CONFIRMED | UNCERTAIN | DENIED
  - CONFIRMED: Clearly a junk item to remove
  - UNCERTAIN: Might be junk, could be billable - use when unsure
  - DENIED: ONLY use for obvious non-junk (walls, floors, people, sky, cars)
- canonical_label: Standardized catalog label (e.g., "bags", "couch", "boxes", "mattress")
- category: furniture | appliance | debris | electronics | yard | hazmat | packaging
- size_bucket: small | medium | large | xlarge
- add_on_flags: Array of applicable flags ["ewaste", "heavy", "two_person_lift", "hazmat"]
- confidence: 0.0-1.0 (your confidence in this classification)

IMPORTANT RULES:
- Trash bags and garbage bags are ALMOST ALWAYS billable junk. Use CONFIRMED or UNCERTAIN.
- When in doubt between DENIED and UNCERTAIN, choose UNCERTAIN.
- Only use DENIED for things that are clearly NOT junk (people, vehicles, walls, floors).

Items to classify:
{json.dumps(items_for_classifier, indent=2)}

Return a JSON object with this EXACT structure:
{{"items": [{{...}}, {{...}}]}}

Each item in the array must include the proposal_id from the input."""

    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",  # Correct model name
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.3,
        )
        
        result = json.loads(response.choices[0].message.content)
        classified_items = result.get("items", [])  # Consistent contract
        
        vlog(f"   ✅ Classifier returned {len(classified_items)} results")
        
        # Merge results back by proposal_id (NEVER by index)
        proposal_map = {p["proposal_id"]: p for p in discrete_items}
        
        for cls_result in classified_items:
            pid = cls_result.get("proposal_id")
            
            if pid and pid in proposal_map:
                proposal = proposal_map[pid]
                
                # Attach classification results
                proposal["verdict"] = cls_result.get("verdict", "UNCERTAIN")
                proposal["canonical_label"] = cls_result.get("canonical_label", proposal["raw_label"])
                proposal["category"] = cls_result.get("category", "furniture")
                proposal["size_bucket"] = cls_result.get("size_bucket", "medium")
                proposal["add_on_flags"] = cls_result.get("add_on_flags", [])
                proposal["classifier_confidence"] = float(cls_result.get("confidence", 0.5))
                
                vlog(f"      {proposal['raw_label']} → {proposal['verdict']} ({proposal['canonical_label']})")
            else:
                vlog(f"   ⚠️ Classifier returned unknown proposal_id: {pid}")
        
        # Apply canonical label mapping for any labels that weren't mapped
        for proposal in discrete_items:
            if not proposal.get("canonical_label"):
                raw = proposal["raw_label"].lower()
                proposal["canonical_label"] = CANONICAL_LABELS.get(raw, raw)
        
        return discrete_items
        
    except Exception as e:
        vlog(f"   ❌ Classifier failed: {e}")
        import traceback
        traceback.print_exc()
        
        # Fallback: set defaults
        for proposal in discrete_items:
            proposal["verdict"] = "UNCERTAIN"
            raw = proposal["raw_label"].lower()
            proposal["canonical_label"] = CANONICAL_LABELS.get(raw, raw)
            proposal["category"] = "furniture"
            proposal["size_bucket"] = "medium"
            proposal["add_on_flags"] = []
            proposal["classifier_confidence"] = 0.3
        
        return discrete_items


def filter_by_verdict(classified_items: List[dict]) -> List[dict]:
    """
    Filter classified items by verdict.
    Keep CONFIRMED and UNCERTAIN, drop DENIED.
    
    Args:
        classified_items: List of classified proposal dicts
        
    Returns:
        Filtered list
    """
    kept = []
    denied_count = 0
    
    for item in classified_items:
        verdict = item.get("verdict", "UNCERTAIN")
        
        if verdict in ("CONFIRMED", "UNCERTAIN"):
            kept.append(item)
        elif verdict == "DENIED":
            denied_count += 1
            vlog(f"   🚫 DENIED: {item['raw_label']} (conf={item.get('classifier_confidence', 0):.2f})")
    
    if denied_count:
        vlog(f"📋 Post-classifier: {len(kept)} kept, {denied_count} denied")
    
    return kept
