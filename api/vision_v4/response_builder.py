"""
v4.0 Response Builder (Step 12)

Builds the final API response with all computed data.
"""

from typing import List
from .volume_engine import compute_pricing
from .utils import vlog


def build_response(
    fused_items: List[dict],
    volumes: dict,
    audit: dict,
    request_id: str,
    images: List[dict]
) -> dict:
    """
    Build final API response.
    
    Args:
        fused_items: List of fused, classified items
        volumes: Volume computation results
        audit: Audit results
        request_id: Unique request identifier
        images: List of image dicts
        
    Returns:
        Complete API response dict
    """
    vlog(f"📦 Building response for {request_id}...")
    
    # Compute pricing from final volume
    pricing = compute_pricing(volumes["final_volume"])
    
    # Build item list for response
    items = []
    for item in fused_items:
        items.append({
            "label": item.get("canonical_label", item.get("raw_label", "unknown")),
            "raw_label": item.get("raw_label", ""),
            "category": item.get("category", "furniture"),
            "size": item.get("size_bucket", "medium"),
            "has_mask": item.get("has_mask", False),
            "confidence": round(item.get("classifier_confidence", 0.5), 2),
            "add_on_flags": item.get("add_on_flags", []),
            "proposal_id": item.get("proposal_id", ""),
            "image_id": item.get("image_id", ""),
            "verdict": item.get("verdict", "UNCERTAIN"),
        })
    
    # Collect all add-on flags
    item_addons = set()
    for item in fused_items:
        item_addons.update(item.get("add_on_flags", []))
    audit_addons = set(audit.get("add_on_flags", []))
    all_addons = list(item_addons | audit_addons)
    
    # Trust metrics
    items_with_masks = sum(1 for i in fused_items if i.get("has_mask", False))
    total_items = len(fused_items)
    mask_coverage_pct = (items_with_masks / total_items * 100) if total_items > 0 else 0
    
    # Build final response
    response = {
        # Request metadata
        "request_id": request_id,
        "pipeline_version": "v4.0",
        "image_count": len(images),
        
        # Items
        "items": items,
        "item_count": len(items),
        
        # Volumes
        "volumes": {
            "final": volumes["final_volume"],
            "lane_a_occupancy": volumes["lane_a_occupancy"],
            "lane_b_catalog": volumes["lane_b_catalog"],
            "dominant": volumes["dominant"],
            "remainder_ratio": volumes.get("remainder_ratio", 0),
        },
        
        # Pricing
        "pricing": {
            "tier": pricing["tier"],
            "base_price": pricing["base_price"],
            "low_price": pricing["low_price"],
            "high_price": pricing["high_price"],
            "currency": "USD",
        },
        
        # Trust & Quality
        "trust": {
            "items_with_masks": items_with_masks,
            "mask_coverage_pct": round(mask_coverage_pct, 1),
            "audit_validation": audit.get("validation", "REVIEW"),
            "audit_confidence": audit.get("confidence", 0.5),
            "fallback_used": volumes["final_volume"] <= 0.5,
        },
        
        # Add-ons & Flags
        "add_on_flags": all_addons,
        
        # Audit notes
        "audit": {
            "notes": audit.get("notes", ""),
            "missing_items": audit.get("missing_items", []),
        },
    }
    
    vlog(f"   ✅ Response built: {len(items)} items, {volumes['final_volume']} yd³, ${pricing['base_price']}")
    
    return response


def build_error_response(request_id: str, error: str, images: List[dict]) -> dict:
    """
    Build error response when pipeline fails.
    
    Args:
        request_id: Unique request identifier
        error: Error message
        images: List of image dicts
        
    Returns:
        Error response dict with fallback values
    """
    return {
        "request_id": request_id,
        "pipeline_version": "v4.0",
        "image_count": len(images),
        "error": True,
        "error_message": error,
        
        # Fallback values
        "items": [],
        "item_count": 0,
        "volumes": {
            "final": 2.5,  # Minimum fallback
            "lane_a_occupancy": 0,
            "lane_b_catalog": 0,
            "dominant": "Fallback",
            "remainder_ratio": 0,
        },
        "pricing": {
            "tier": "Minimum",
            "base_price": 135,
            "low_price": 135,
            "high_price": 160,
            "currency": "USD",
        },
        "trust": {
            "items_with_masks": 0,
            "mask_coverage_pct": 0,
            "audit_validation": "FAIL",
            "audit_confidence": 0,
            "fallback_used": True,
        },
        "add_on_flags": [],
        "audit": {
            "notes": f"Pipeline error: {error}",
            "missing_items": [],
        },
    }
