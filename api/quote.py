from http.server import BaseHTTPRequestHandler
import json
import os
import io
import asyncio
import base64
import ast
import redis
import requests
from openai import AsyncOpenAI
from google import genai
from google.genai import types

# ==================== VISION WORKER (INLINED) ====================
# Florence-2 + Depth-Anything-V2 Integration using Replicate SDK

print("🔬 Loading Vision Pipeline...")

try:
    import replicate
    from PIL import Image, ImageDraw
    
    # Model versions (from official Replicate pages)
    FLORENCE_MODEL = "lucataco/florence-2-large:da53547e17d45b9cfb48174b2f18af8b83ca020fa76db62136bf9c6616762595"
    DEPTH_MODEL = "chenxwh/depth-anything-v2:b239ea33cff32bb7abb5db39ffe9a09c14cbc2894331d1ef66fe096eed88ebd4"
    
    # Feature flag for camera-aware pipeline (Phases 1-8)
    CAMERA_AWARE_ENABLED = os.environ.get("CAMERA_AWARE", "false").lower() == "true"
    
    # Anchor Trust Registry: trust tiers + validation rules
    ANCHOR_REGISTRY = {
        # HIGH trust - consistent, standardized sizes
        "door": {"size_inches": 80, "trust": "HIGH", "aspect_ratio": (0.3, 0.6), "aliases": ["door frame", "doorway"]},
        "standard door": {"size_inches": 80, "trust": "HIGH", "aspect_ratio": (0.3, 0.6)},
        # MEDIUM trust - common but variable sizes
        "person": {"size_inches": 66, "trust": "MEDIUM", "aspect_ratio": (0.25, 0.5), "size_range": (60, 76)},
        "wheelie bin": {"size_inches": 42, "trust": "MEDIUM", "aspect_ratio": (0.4, 0.8)},
        "trash can": {"size_inches": 36, "trust": "MEDIUM", "aspect_ratio": (0.5, 1.2)},
        # LOW trust - highly variable, use as fallback only
        "chair": {"size_inches": 32, "trust": "LOW", "aspect_ratio": (0.6, 1.4)},
        "bicycle": {"size_inches": 40, "trust": "LOW", "aspect_ratio": (0.6, 1.8)},
        "tv": {"size_inches": 24, "trust": "LOW", "aspect_ratio": (1.2, 2.5), "aliases": ["television", "monitor"]},
    }
    
    # Item Catalog: volume ranges (small, medium, large) in cubic yards + void factors
    # CORRECTED: Industry-standard volumes based on actual truck loading
    ITEM_CATALOG = {
        # Furniture - large items
        "mattress": {"vol_range": (0.8, 1.0, 1.7), "void": 0.1},  # Twin/Full/Queen/King
        "bed": {"vol_range": (1.0, 1.3, 2.0), "void": 0.1},  # Mattress + frame
        "box spring": {"vol_range": (0.8, 1.0, 1.7), "void": 0.1},
        "couch": {"vol_range": (2.0, 2.5, 3.0), "void": 0.15},  # 3-seat sofa
        "sofa": {"vol_range": (2.0, 2.5, 3.0), "void": 0.15},
        "loveseat": {"vol_range": (1.5, 1.75, 2.0), "void": 0.15},
        "sectional": {"vol_range": (4.0, 5.0, 6.0), "void": 0.15},
        "recliner": {"vol_range": (1.0, 1.25, 1.5), "void": 0.15},
        "dresser": {"vol_range": (1.0, 1.25, 1.5), "void": 0.05},
        "nightstand": {"vol_range": (0.3, 0.4, 0.5), "void": 0.05},
        "table": {"vol_range": (1.0, 1.5, 2.0), "void": 0.3},  # Dining table
        "desk": {"vol_range": (1.0, 1.5, 2.0), "void": 0.25},
        "chair": {"vol_range": (0.2, 0.25, 0.3), "void": 0.2},  # Dining chair
        "office chair": {"vol_range": (0.3, 0.4, 0.5), "void": 0.2},
        # Appliances
        "refrigerator": {"vol_range": (2.0, 2.5, 3.0), "void": 0.05},
        "fridge": {"vol_range": (2.0, 2.5, 3.0), "void": 0.05},
        "mini fridge": {"vol_range": (0.4, 0.5, 0.6), "void": 0.05},
        "washer": {"vol_range": (0.9, 1.0, 1.1), "void": 0.05},
        "washing machine": {"vol_range": (0.9, 1.0, 1.1), "void": 0.05},
        "dryer": {"vol_range": (0.9, 1.0, 1.1), "void": 0.05},
        "dishwasher": {"vol_range": (0.75, 0.9, 1.0), "void": 0.05},
        "stove": {"vol_range": (1.0, 1.25, 1.5), "void": 0.05},
        "oven": {"vol_range": (1.0, 1.25, 1.5), "void": 0.05},
        "microwave": {"vol_range": (0.1, 0.15, 0.2), "void": 0.0},
        "water heater": {"vol_range": (0.9, 1.0, 1.1), "void": 0.05},
        "tv": {"vol_range": (0.2, 0.3, 0.4), "void": 0.0},  # Flat screen
        "television": {"vol_range": (0.2, 0.3, 0.4), "void": 0.0},
        "crt tv": {"vol_range": (0.8, 1.0, 1.5), "void": 0.0},  # Old tube TV
        # Small items
        "box": {"vol_range": (0.05, 0.1, 0.15), "void": 0.0},  # Moving box
        "bag": {"vol_range": (0.05, 0.1, 0.2), "void": 0.0},  # Contractor bag
        "trash bag": {"vol_range": (0.03, 0.05, 0.1), "void": 0.0},  # Kitchen bag
        "plastic bag": {"vol_range": (0.02, 0.03, 0.05), "void": 0.0},
        "suitcase": {"vol_range": (0.1, 0.15, 0.2), "void": 0.1},
        # Outdoor/misc
        "bicycle": {"vol_range": (0.3, 0.4, 0.5), "void": 0.4},
        "tire": {"vol_range": (0.1, 0.15, 0.2), "void": 0.3},
        "bbq": {"vol_range": (0.5, 0.75, 1.0), "void": 0.2},
        "grill": {"vol_range": (0.5, 0.75, 1.0), "void": 0.2},
        "treadmill": {"vol_range": (1.0, 1.5, 2.0), "void": 0.2},
        "elliptical": {"vol_range": (1.0, 1.25, 1.5), "void": 0.2},
        "pallet": {"vol_range": (0.2, 0.25, 0.3), "void": 0.1},
        "wheelbarrow": {"vol_range": (0.3, 0.4, 0.5), "void": 0.3},
        "push mower": {"vol_range": (0.5, 0.6, 0.75), "void": 0.2},
    }
    
    # Confidence Factors for degraded mode calculation
    CONFIDENCE_FACTORS = {
        "anchor_high_trust": 1.0,
        "anchor_medium_trust": 0.7,
        "anchor_low_trust": 0.4,
        "no_anchor": 0.2,
        "depth_available": 0.15,
        "multi_image": 0.1,  # per additional image beyond 1
        "catalog_match_ratio": 0.2,  # if >50% items matched catalog
    }
    
    # Mode thresholds determine price band width
    MODE_THRESHOLDS = {
        "FULL": {"threshold": 0.8, "band": 0.10},      # ±10%
        "REDUCED": {"threshold": 0.5, "band": 0.20},   # ±20%
        "LOW": {"threshold": 0.3, "band": 0.35},       # ±35%
        "SHADOW": {"threshold": 0.0, "band": 0.50},    # ±50%
    }
    
    # Camera Intrinsics Database for metric depth calculation
    # K matrix: fx, fy = focal length in pixels; cx, cy = principal point
    CAMERA_INTRINSICS_DB = {
        # Apple iPhones
        "Apple iPhone 15 Pro": {
            "rear_wide": {"ref_res": [4032, 3024], "K": {"fx": 2850, "fy": 2848, "cx": 2016, "cy": 1512}, "focal_mm": 6.765, "uncertainty": 0.08},
            "rear_ultrawide": {"ref_res": [4032, 3024], "K": {"fx": 1420, "fy": 1418, "cx": 2016, "cy": 1512}, "focal_mm": 2.22, "uncertainty": 0.12},
        },
        "Apple iPhone 15": {
            "rear_wide": {"ref_res": [4032, 3024], "K": {"fx": 2750, "fy": 2748, "cx": 2016, "cy": 1512}, "focal_mm": 5.7, "uncertainty": 0.10},
        },
        "Apple iPhone 14 Pro": {
            "rear_wide": {"ref_res": [4032, 3024], "K": {"fx": 2800, "fy": 2798, "cx": 2016, "cy": 1512}, "focal_mm": 6.86, "uncertainty": 0.08},
        },
        "Apple iPhone 14": {
            "rear_wide": {"ref_res": [4032, 3024], "K": {"fx": 2700, "fy": 2698, "cx": 2016, "cy": 1512}, "focal_mm": 5.7, "uncertainty": 0.10},
        },
        "Apple iPhone 13": {
            "rear_wide": {"ref_res": [4032, 3024], "K": {"fx": 2650, "fy": 2648, "cx": 2016, "cy": 1512}, "focal_mm": 5.7, "uncertainty": 0.10},
        },
        "Apple iPhone 12": {
            "rear_wide": {"ref_res": [4032, 3024], "K": {"fx": 2600, "fy": 2598, "cx": 2016, "cy": 1512}, "focal_mm": 4.2, "uncertainty": 0.12},
        },
        # Samsung Galaxy
        "samsung SM-S928B": {  # S24 Ultra
            "rear_wide": {"ref_res": [4000, 3000], "K": {"fx": 2900, "fy": 2898, "cx": 2000, "cy": 1500}, "focal_mm": 6.3, "uncertainty": 0.10},
        },
        "samsung SM-S918B": {  # S23 Ultra
            "rear_wide": {"ref_res": [4000, 3000], "K": {"fx": 2850, "fy": 2848, "cx": 2000, "cy": 1500}, "focal_mm": 6.3, "uncertainty": 0.10},
        },
        "samsung SM-S908B": {  # S22 Ultra
            "rear_wide": {"ref_res": [4000, 3000], "K": {"fx": 2800, "fy": 2798, "cx": 2000, "cy": 1500}, "focal_mm": 6.4, "uncertainty": 0.10},
        },
        # Google Pixel
        "Google Pixel 8 Pro": {
            "rear_wide": {"ref_res": [4080, 3072], "K": {"fx": 2820, "fy": 2818, "cx": 2040, "cy": 1536}, "focal_mm": 6.9, "uncertainty": 0.08},
        },
        "Google Pixel 7 Pro": {
            "rear_wide": {"ref_res": [4080, 3072], "K": {"fx": 2780, "fy": 2778, "cx": 2040, "cy": 1536}, "focal_mm": 6.81, "uncertainty": 0.10},
        },
    }
    
    # Depth Pro model on Replicate
    DEPTH_PRO_MODEL = "garg-aayush/ml-depth-pro"
    
    # ==================== SINGLE ITEM ENGINE ====================
    # Smart Triage: Route items to fast lookup (Tier 1) or measurement (Tier 2)
    
    # Pricing constants (unified with Pile tool)
    MIN_LOAD_PRICE = 95
    RATE_PER_YARD = 55.0
    
    # TIER 1: Price-stable items - NO measurement needed
    # CORRECTED: Industry-standard volumes based on actual truck loading
    TIER_1_CATALOG = {
        # Appliances (standardized sizes)
        "washing machine": 1.0, "washer": 1.0, "dryer": 1.0, 
        "dishwasher": 0.9, "stove": 1.25, "oven": 1.25,
        "microwave": 0.15, "water heater": 1.0,
        # Bedding (Queen size default for margin protection)
        "mattress": 1.3, "box spring": 1.3, "bed": 1.8, "bed frame": 0.75,
        # Exercise equipment
        "treadmill": 1.5, "elliptical": 1.25, "exercise bike": 0.6,
        # Small items
        "tire": 0.15, "bicycle": 0.4, "grill": 0.75, "bbq": 0.75,
        "bag": 0.15, "box": 0.1, "trash bag": 0.05,
        # Office
        "office chair": 0.4, "filing cabinet": 0.5,
        # Additional common items
        "nightstand": 0.4, "dresser": 1.25, "recliner": 1.25,
        "push mower": 0.6, "wheelbarrow": 0.4, "pallet": 0.25,
    }
    
    # TIER 2: Variable items - REQUIRES measurement via Depth Pro
    # Format: "axis" = dimension to measure (h=height, w=width)
    # "bins" = [(max_inches, variant_name, volume_yards), ...]
    # CORRECTED: Industry-standard volumes
    TIER_2_ROUTING = {
        "refrigerator": {
            "axis": "h",  # Measure HEIGHT for fridges
            "bins": [(36, "MINI", 0.5), (60, "APT_SIZE", 1.5), (999, "STANDARD", 2.5)]
        },
        "fridge": {
            "axis": "h",
            "bins": [(36, "MINI", 0.5), (60, "APT_SIZE", 1.5), (999, "STANDARD", 2.5)]
        },
        "sofa": {
            "axis": "w",  # Measure WIDTH for sofas
            "bins": [(65, "LOVESEAT", 1.75), (88, "STANDARD", 2.5), (999, "SECTIONAL", 5.0)]
        },
        "couch": {
            "axis": "w",
            "bins": [(65, "LOVESEAT", 1.75), (88, "STANDARD", 2.5), (999, "SECTIONAL", 5.0)]
        },
        "television": {
            "axis": "w",
            "bins": [(45, "MEDIUM", 0.3), (999, "LARGE", 0.4)]
        },
        "tv": {
            "axis": "w",
            "bins": [(45, "MEDIUM", 0.3), (999, "LARGE", 0.4)]
        },
        "dresser": {
            "axis": "w",
            "bins": [(40, "SMALL", 1.0), (60, "MEDIUM", 1.25), (999, "LARGE", 1.5)]
        },
        "cabinet": {
            "axis": "h",
            "bins": [(48, "SHORT", 0.8), (72, "STANDARD", 1.2), (999, "TALL", 1.5)]
        },
        "wardrobe": {
            "axis": "h",
            "bins": [(60, "SHORT", 1.2), (999, "TALL", 2.0)]
        },
        "table": {
            "axis": "w",
            "bins": [(48, "SMALL", 1.0), (72, "MEDIUM", 1.5), (999, "LARGE", 2.0)]
        },
        "desk": {
            "axis": "w",
            "bins": [(48, "SMALL", 1.0), (60, "MEDIUM", 1.5), (999, "LARGE", 2.0)]
        },
    }
    
    # HIGH RISK: Items requiring GPT-4o audit for surcharges
    HIGH_RISK_KEYWORDS = ["piano", "safe", "hot tub", "spa", "pool table", 
                          "sleeper", "cast iron", "gun safe", "aquarium"]
    
    # ==================== TIERED PRICING ====================
    # Industry-aligned volume buckets - MIN 1 yd³, MAX 18 yd³
    VOLUME_TIERS = [
        {"max_cuft": 27,   "price": 95,  "label": "Dispatch Minimum"},  # 1 yd³
        {"max_cuft": 60,   "price": 99,  "label": "1/8 Load"},          # ~2.2 yd³
        {"max_cuft": 80,   "price": 129, "label": "1/6 Load"},          # ~3.0 yd³
        {"max_cuft": 120,  "price": 149, "label": "1/4 Load"},          # ~4.4 yd³
        {"max_cuft": 180,  "price": 199, "label": "3/8 Load"},          # ~6.7 yd³
        {"max_cuft": 240,  "price": 299, "label": "Half Load"},         # ~8.9 yd³
        {"max_cuft": 300,  "price": 349, "label": "5/8 Load"},          # ~11 yd³
        {"max_cuft": 360,  "price": 399, "label": "3/4 Load"},          # ~13 yd³
        {"max_cuft": 420,  "price": 479, "label": "7/8 Load"},          # ~16 yd³
        {"max_cuft": 486,  "price": 599, "label": "Full Load"},         # 18 yd³ MAX
    ]
    
    # ==================== PRICING v2.1 ====================
    # Hard range caps (tight UX)
    RANGE_CAPS = {250: 50, 400: 75, 999: 100}
    PRICE_FLOOR = 95  # Dispatch Minimum
    MIN_SPREAD = 10   # Minimum range width
    
    # Disposal candidates (flags only, not priced by tool)
    DISPOSAL_CANDIDATES = ["mattress", "refrigerator", "freezer", "ac_unit", "tv", "monitor", "tire", "box_spring"]
    
    # Trust sentence for output
    TRUST_NOTE = "Add-ons may apply based on your selections (stairs, long carry, mattress/tires/TV, freon)."
    
    # ==================== PHASE 2: BOUNDED FALLBACK ====================
    FALLBACK_BY_SUPERCATEGORY = {
        "small_misc": {"vol": 0.15, "range": (0.05, 0.3)},
        "medium_furniture": {"vol": 1.0, "range": (0.75, 1.5)},
        "large_furniture": {"vol": 2.5, "range": (2.0, 4.0)},
        "appliance": {"vol": 2.0, "range": (1.5, 2.5)},
        "ewaste": {"vol": 0.35, "range": (0.2, 0.6)},
        "heavy": {"vol": 0.5, "range": (0.3, 0.8)},
        "unknown": {"vol": 0.5, "range": (0.3, 1.0)},
    }
    
    SUBLABEL_KEYWORDS = {
        "microwave": {"vol": 0.2, "range": (0.1, 0.3), "category": "small_misc"},
        "tv": {"vol": 0.4, "range": (0.2, 0.6), "category": "ewaste"},
        "monitor": {"vol": 0.3, "range": (0.2, 0.5), "category": "ewaste"},
        "concrete": {"vol": 0.5, "range": (0.3, 0.8), "category": "heavy", "flag_only": True},
        "brick": {"vol": 0.4, "range": (0.3, 0.6), "category": "heavy", "flag_only": True},
    }
    
    SUPERCATEGORY_KEYWORDS = {
        "small_misc": ["bag", "plastic", "trash", "box", "small", "bucket", "bin"],
        "medium_furniture": ["dresser", "drawer", "cabinet", "table", "chair", "desk", "nightstand"],
        "large_furniture": ["couch", "sofa", "sectional", "bed", "mattress", "wardrobe"],
        "appliance": ["fridge", "refrigerator", "washer", "dryer", "stove", "oven", "dishwasher"],
        "ewaste": ["computer", "printer", "electronic", "screen"],
    }
    
    # ==================== PHASE 4: DEDUPE CLASSES ====================
    UNIQUE_LABELS = {"sofa", "couch", "dresser", "fridge", "mattress", "bed", "table", "piano", "hot_tub"}
    SEMI_COUNTABLE_LABELS = {"chairs", "chair", "speakers", "boxes", "bins", "cushions", "lamps"}
    COUNTABLE_LABELS = {"bags", "bag", "tires", "tire", "trash_bag", "pallet", "wood_pallet"}
    BASE_SANITY_CAPS = {"bags": 15, "bag": 15, "tires": 8, "tire": 8, "pallet": 4}
    
    # ==================== PHASE 7: HANDLING VS UI-PRICED ====================
    HANDLING_MULTIPLIERS = {
        "mattress": 1.1,
        "hot_tub": 1.3,
        "piano": 1.4,
    }
    UI_PRICED_CATEGORIES = ["freon", "ewaste", "tires", "mattress_disposal", "disassembly"]
    
    # ==================== PHASE 11: HARD CONSTRAINTS ====================
    NO_PACK_LABELS = {"mattress", "box_spring", "sofa", "couch", "sectional", "piano", "hot_tub"}
    RIGID_LABELS = {"dresser", "cabinet", "wardrobe", "desk", "table", "fridge", "refrigerator"}
    MINIMUM_VOLUMES = {"large_furniture": 1.5, "appliance": 1.0}
    COMPRESSION_FLOORS = {"small_misc": 0.75}
    
    # ==================== PHASE 1+9: ROUNDING FUNCTIONS ====================
    def round_down(p: float) -> int:
        """Round price down for min_price."""
        if p > 100: return int(5 * (p // 5))
        return int(p)
    
    def round_up(p: float) -> int:
        """Round price up for max_price."""
        import math
        if p > 100: return int(5 * math.ceil(p / 5))
        return int(math.ceil(p))
    
    def round_nearest(p: float) -> int:
        """Round price to nearest for estimate."""
        if p > 100: return int(5 * round(p / 5))
        return round(p)
    
    def round_to_half(value: float) -> float:
        """Round volume to nearest 0.5."""
        return round(value * 2) / 2
    
    # ==================== PHASE 2: FALLBACK FUNCTIONS ====================
    def infer_supercategory(label: str) -> str:
        """Infer supercategory from label using keyword matching."""
        label_lower = label.lower()
        for category, keywords in SUPERCATEGORY_KEYWORDS.items():
            if any(kw in label_lower for kw in keywords):
                return category
        return "unknown"
    
    def get_fallback_volume_v21(label: str, size_class: str = "medium") -> dict:
        """Get fallback volume with range using substring matching."""
        label_lower = label.lower()
        
        # Check sublabel keywords first
        for keyword, data in SUBLABEL_KEYWORDS.items():
            if keyword in label_lower:
                if data.get("flag_only"):
                    return {"vol": 0, "range": (0, 0), "flag": data["category"], "category": data["category"]}
                return {**data, "used_fallback": True}
        
        # Infer supercategory
        category = infer_supercategory(label_lower)
        base = FALLBACK_BY_SUPERCATEGORY.get(category, FALLBACK_BY_SUPERCATEGORY["unknown"])
        
        # Size adjustment
        if size_class == "large" and category == "medium_furniture":
            return {"vol": 1.5, "range": (1.0, 2.0), "category": category, "used_fallback": True}
        
        return {"vol": base["vol"], "range": base["range"], "category": category, "used_fallback": True}
    
    # ==================== PHASE 8: DELTA CALCULATION ====================
    def calc_volume_delta_v21(billable: float, anchor_trust: str, fallback_uncertainty: float,
                              size_confidence: float, catalog_variance: float, near_cliff: bool, tier_id: int) -> float:
        """Calculate volume delta with all safeguards."""
        base = max(0.2, 0.15 * billable)
        
        if anchor_trust == "LOW": base += 0.3
        if size_confidence < 0.7: base += 0.2
        base += min(0.5, 0.3 * fallback_uncertainty)
        if catalog_variance > 0: base += min(0.5, catalog_variance * 0.25)
        if near_cliff: base += 0.15
        
        # Piecewise caps
        if billable < 2: delta = min(base, 0.5)
        elif billable < 8: delta = min(base, 0.8)
        else: delta = min(base, 1.2)
        
        # 1-tier crossing limit
        current_max = VOLUME_TIERS[tier_id]["max_cuft"] / 27
        next_idx = min(tier_id + 1, len(VOLUME_TIERS) - 1)
        next_max = VOLUME_TIERS[next_idx]["max_cuft"] / 27
        
        if billable + delta > next_max and tier_id < len(VOLUME_TIERS) - 1:
            delta = max(0.2, next_max - billable)
            print(f"⚠️ Delta clamped to prevent 2+ tier crossing: {delta:.2f}")
        
        return delta
    
    # ==================== PHASE 1: TIER SELECTION ====================
    def get_range_cap(base_price: float) -> int:
        """Get dollar cap for range based on price level."""
        for threshold, cap in RANGE_CAPS.items():
            if base_price <= threshold:
                return cap
        return 100
    
    def choose_tier_v2(volume_yards: float, delta_yards: float = 0.3) -> tuple:
        """Choose tier from volume (not price). Returns (tier_id, tier_dict)."""
        cuft = volume_yards * 27
        for tier_id, tier in enumerate(VOLUME_TIERS):
            if cuft <= tier["max_cuft"]:
                return tier_id, tier
        return len(VOLUME_TIERS) - 1, VOLUME_TIERS[-1]
    
    def is_near_cliff(volume: float, tier_id: int, threshold: float = 0.5) -> bool:
        """Check if volume is near tier boundary."""
        tier_max = VOLUME_TIERS[tier_id]["max_cuft"] / 27
        return abs(volume - tier_max) < threshold
    
    # ==================== PHASE 9: FINALIZE PRICES ====================
    def finalize_prices_v21(base_estimate: int, base_min: int, base_max: int, 
                            surcharges: int, tier_id: int) -> tuple:
        """Finalize prices with directional rounding and tier constraints."""
        # Directional rounding
        final_estimate = round_nearest(base_estimate + surcharges)
        final_min = round_down(base_min + surcharges)
        final_max = round_up(base_max + surcharges)
        
        # Fix inversions
        if final_min > final_max:
            final_min = final_max = final_estimate
        
        # Get tier boundaries
        tier_min = VOLUME_TIERS[max(0, tier_id - 1)]["price"] if tier_id > 0 else PRICE_FLOOR
        tier_max_price = VOLUME_TIERS[min(tier_id + 1, len(VOLUME_TIERS) - 1)]["price"]
        
        # Minimum spread (subordinate to tier constraints)
        if final_max - final_min < MIN_SPREAD:
            desired_min = final_estimate - MIN_SPREAD // 2
            desired_max = final_estimate + MIN_SPREAD // 2
            
            if desired_min >= tier_min and desired_max <= tier_max_price:
                final_min = desired_min
                final_max = desired_max
            else:
                # Can't expand within tier: collapse to single point
                final_min = final_max = final_estimate
        
        # Final invariant enforcement
        if final_estimate < final_min: final_estimate = final_min
        if final_estimate > final_max: final_estimate = final_max
        
        # Ensure price floor
        final_min = max(final_min, PRICE_FLOOR)
        final_estimate = max(final_estimate, PRICE_FLOOR)
        
        return final_estimate, final_min, final_max
    
    # ==================== PHASE 10: REASON CODES ====================
    REASON_PHRASES = {
        "anchor_low": {"internal": "anchor_trust=LOW", "customer": "photo angle/scale unclear"},
        "fallback_high": {"internal": "fallback_ratio>0.2", "customer": "some items had limited visibility"},
        "near_cliff": {"internal": "near_cliff=True", "customer": "pile is near a pricing boundary"},
        "size_ambiguous": {"internal": "size_ambiguous", "customer": "uncertain size for some items"},
    }
    
    def get_reason_codes_v21(anchor_trust: str, fallback_ratio: float, near_cliff: bool, 
                             top_ambiguous: list) -> dict:
        """Generate customer-safe and internal reason codes."""
        internal = []
        customer = []
        
        if anchor_trust == "LOW":
            internal.append(REASON_PHRASES["anchor_low"]["internal"])
            customer.append(REASON_PHRASES["anchor_low"]["customer"])
        
        if fallback_ratio > 0.2:
            internal.append(REASON_PHRASES["fallback_high"]["internal"])
            customer.append(REASON_PHRASES["fallback_high"]["customer"])
        
        if near_cliff:
            internal.append(REASON_PHRASES["near_cliff"]["internal"])
            customer.append(REASON_PHRASES["near_cliff"]["customer"])
        
        if top_ambiguous:
            internal.append(REASON_PHRASES["size_ambiguous"]["internal"])
            customer.append(REASON_PHRASES["size_ambiguous"]["customer"])
        
        return {
            "reason_codes_internal": "; ".join(internal) or "standard",
            "reason_codes_customer": ("Range widened because: " + "; ".join(customer)) if customer else "standard estimate"
        }
    
    # ==================== PHASE 6: LABOR FLAGS ====================
    def detect_labor_flags_v21(items: list) -> dict:
        """Detect labor conditions via attributes (not packing group)."""
        supercats = [infer_supercategory(i.get("canonical_label", i.get("label", ""))) for i in items]
        unique_supercats = set(supercats)
        entropy = len(unique_supercats) / max(len(supercats), 1)
        
        return {
            "loose_debris_possible": len(items) > 15 and entropy > 0.5,
            "mixed_debris_possible": entropy > 0.6 and len(unique_supercats) > 4,
            "wet_dirty_possible": False,  # UI-confirmed only
        }
    
    def detect_disposal_flags(items: list) -> dict:
        """Detect disposal candidates as flags (not priced)."""
        flags = {}
        for item in items:
            label = item.get("canonical_label", item.get("label", "")).lower()
            for candidate in DISPOSAL_CANDIDATES:
                if candidate in label:
                    flags[f"{candidate}_detected"] = True
        return flags
    
    def get_tier_price(volume_yards: float) -> tuple:
        """Convert cubic yards to (price, label) using tiers."""
        cuft = volume_yards * 27
        for tier in VOLUME_TIERS:
            if cuft <= tier["max_cuft"]:
                return tier["price"], tier["label"]
        return 599, "Full Load"
    
    # ==================== VOLUME HOTFIX v2.2 ====================
    
    # Fix 2: Synonym canonicalization (deploy before clustering)
    # v2.5: REMOVED wheel → tires (causes double-count)
    SYNONYM_MAP = {
        # Debris
        "debris pile": "mixed_debris",
        "debris": "mixed_debris",
        "trash": "mixed_debris",
        "garbage": "mixed_debris",
        "junk pile": "mixed_debris",
        # Spools - v2.5: only if confirmed, otherwise background
        "wooden spool": "cable_spool_wood",
        "industrial spool": "cable_spool_wood",
        # Tires - v2.5: REMOVED wheel→tires (motorcycle wheels aren't tire piles)
        # "wheel": "tires",  # REMOVED - causes double-count
        "tire": "tires",
        # Crates
        "wood crate": "wood_crate",
        "wood crate shipping crate": "wood_crate",
        # Bags
        "plastic bag": "bags",
        "bag": "bags",
        # Garbage labels - v2.5: stack is banned
        "applian": "unknown_medium",
        "stuff": "unknown_medium",
        "object": "unknown_medium",
        "item": "unknown_medium",
        "stack": "banned_label",  # v2.5: never price directly
        "wooden": "banned_label",  # v2.5: garbage token
    }
    
    # ==================== v2.5: STABLE CATALOG VOLUMES ====================
    # These are fixed volumes that should never use fallback
    STABLE_CATALOG_VOLUMES = {
        # Appliances - accurate volumes
        "washer": 0.7,
        "dryer": 0.7,
        "washer_dryer": 1.4,
        "refrigerator": 1.5,
        "fridge": 1.5,
        "dishwasher": 0.5,
        "oven": 0.6,
        "stove": 0.6,
        "microwave": 0.15,
        # Tires - small amounts
        "tires": 0.35,  # v2.5: default is 2-4 tires, not "tire pile"
        # Furniture
        "couch": 3.0,
        "sofa": 3.0,
        "loveseat": 2.0,
        "mattress": 1.5,
        "box_spring": 1.0,
        "dresser": 1.5,
        "desk": 1.0,
        "table": 0.8,
        "chair": 0.3,
        # Small misc - v2.5: conservative
        "bags": 0.1,
        "boxes": 0.1,
        "wood_crate": 0.3,
        # Unknown - v2.5: conservative fallbacks
        "unknown_large": 0.5,  # v2.5: was 2.0, now conservative
        "unknown_medium": 0.3,
        "unknown_small": 0.1,
    }
    
    # v2.5: DEFAULT BACKGROUND LABELS (skip when Gemini underdelivers)
    DEFAULT_BACKGROUND_LABELS = {
        "industrial spool", "cable_spool_wood",
        "fence panels", "fence_panels",
        "stack", "wood_pallet_stack",
        "metal pipe", "metal_pipe",
        "wooden", "banned_label",
    }
    
    # v2.5: BANNED LABELS (never get volume)
    BANNED_LABELS = {"stack", "wooden", "banned_label", "object", "stuff", "item"}
    
    def canonicalize_synonym(label: str, gemini_correction: str = None) -> str:
        """Aggressive synonym canonicalization."""
        label_lower = label.lower().strip()
        # Check if wheel → tires needs Gemini confirmation
        if label_lower == "wheel" and gemini_correction and gemini_correction.lower() != "tires":
            return "unknown_medium"
        return SYNONYM_MAP.get(label_lower, label_lower)
    
    # Fix 3: Pile height defaults (not flat 24")
    PILE_HEIGHT_DEFAULTS = {
        "furniture": 28,      # 24-30"
        "bags_yard": 20,      # 18-24"
        "mixed_debris": 30,   # 24-36"
        "appliance": 32,      # Tall items
        "unknown": 24,
    }
    
    def get_default_pile_height(pile_type: str) -> int:
        """Get default height by pile type, clamped 12-48\"."""
        height = PILE_HEIGHT_DEFAULTS.get(pile_type, 24)
        return max(12, min(height, 48))
    
    def infer_pile_type(items: list) -> str:
        """Infer pile type from dominant item categories."""
        supercats = [infer_supercategory(i.get("canonical_label", i.get("label", ""))) for i in items]
        from collections import Counter
        if not supercats:
            return "unknown"
        most_common = Counter(supercats).most_common(1)[0][0]
        if most_common in ["large_furniture", "medium_furniture"]:
            return "furniture"
        elif most_common == "small_misc":
            return "bags_yard"
        elif most_common == "appliance":
            return "appliance"
        return "mixed_debris" if "mixed_debris" in [i.get("canonical_label", "") for i in items] else "unknown"
    
    # Fix 4: Remainder cap
    REMAINDER_THRESHOLDS = {"pile": 0.25, "single_item": 0.35}
    REMAINDER_CAP_FACTOR = 0.6  # remainder_vol <= 0.6 * packed_vol
    
    def should_activate_remainder_v22(mode: str, residual: float) -> bool:
        """Fixed remainder trigger using residual, not coverage."""
        return residual >= REMAINDER_THRESHOLDS.get(mode, 0.30)
    
    def cap_remainder_volume(remainder_vol: float, packed_vol: float) -> float:
        """Cap remainder to prevent explosion."""
        max_allowed = packed_vol * REMAINDER_CAP_FACTOR
        if remainder_vol > max_allowed:
            print(f"⚠️ Remainder capped: {remainder_vol:.2f} → {max_allowed:.2f} (max={REMAINDER_CAP_FACTOR}× packed)")
            return max_allowed
        return remainder_vol
    
    # Fix 5: Confidence gates (asymmetric downgrade)
    HIGH_IMPACT_LABELS = {"hot_tub", "mixed_debris", "demo_heavy", "sectional", "piano"}
    GARBAGE_LABELS = {"applian", "stuff", "object", "item", "thing"}
    
    def validate_label_v22(label: str, confidence: float, bbox_area: float, multi_model: bool) -> tuple:
        """Validate high-impact labels with asymmetric downgrade. Returns (label, needs_confirmation)."""
        if label in GARBAGE_LABELS:
            return "unknown_medium", False
        
        if label in HIGH_IMPACT_LABELS:
            if confidence < 0.7 or not multi_model:
                # Asymmetric: downgrade based on bbox size
                if bbox_area > 50000:  # Large bbox
                    return "unknown_large", True
                else:
                    return "unknown_medium", True
        return label, False
    
    # Fix 6: Hybrid clustering (label-type aware, no sklearn)
    def dedupe_by_iou(detections: list, threshold: float = 0.3) -> list:
        """Simple IoU-based deduplication without sklearn."""
        if not detections:
            return []
        
        def calc_iou(box1, box2):
            x1 = max(box1[0], box2[0])
            y1 = max(box1[1], box2[1])
            x2 = min(box1[2], box2[2])
            y2 = min(box1[3], box2[3])
            
            inter = max(0, x2 - x1) * max(0, y2 - y1)
            area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
            area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
            union = area1 + area2 - inter
            return inter / union if union > 0 else 0
        
        result = []
        used = set()
        
        for i, det_a in enumerate(detections):
            if i in used:
                continue
            bbox_a = det_a.get("bbox_pixels", det_a.get("bbox", [0, 0, 0, 0]))
            result.append(det_a)
            used.add(i)
            
            for j, det_b in enumerate(detections):
                if j in used or j <= i:
                    continue
                bbox_b = det_b.get("bbox_pixels", det_b.get("bbox", [0, 0, 0, 0]))
                if calc_iou(bbox_a, bbox_b) > threshold:
                    used.add(j)  # Skip duplicate
        
        return result
    
    def cluster_detections_hybrid(detections: list, image_counts: dict = None) -> list:
        """Hybrid clustering: IoU for unique, max-per-view for countables, merge debris."""
        unique_items = []
        countables = {}
        debris_merged = None
        
        for det in detections:
            label = det.get("canonical_label", det.get("label", "")).lower()
            label = canonicalize_synonym(label)  # Apply synonyms first
            det["canonical_label"] = label
            
            if label in UNIQUE_LABELS:
                unique_items.append(det)
            elif label in COUNTABLE_LABELS:
                img_id = det.get("image_id", 0)
                countables.setdefault(label, {}).setdefault(img_id, 0)
                countables[label][img_id] += 1
            elif label == "mixed_debris":
                # Merge all debris into one
                if debris_merged is None:
                    debris_merged = det.copy()
                    debris_merged["merged_count"] = 1
                else:
                    debris_merged["volume_yards"] = debris_merged.get("volume_yards", 0) + det.get("volume_yards", 0)
                    debris_merged["merged_count"] = debris_merged.get("merged_count", 0) + 1
            else:
                unique_items.append(det)  # Treat as unique by default
        
        # Dedupe unique items by IoU
        unique_final = dedupe_by_iou(unique_items, threshold=0.3)
        
        # Count countables: max + buffer
        countable_final = []
        for label, counts in countables.items():
            max_count = max(counts.values())
            min_count = min(counts.values())
            buffer = 1 if len(counts) > 1 and max_count != min_count else 0
            sanity_cap = BASE_SANITY_CAPS.get(label, 10)
            final_count = min(max_count + buffer, sanity_cap)
            
            # Create detection entries
            for _ in range(final_count):
                countable_final.append({"canonical_label": label, "source": "countable_dedupe"})
        
        result = unique_final + countable_final
        if debris_merged:
            print(f"🗑️ Merged {debris_merged.get('merged_count', 1)} debris detections into one")
            result.append(debris_merged)
        
        return result
    
    # Fix 7: Volume sanity check before tiering
    def sanity_check_volume(final_vol: float, packed_sum: float, footprint_sqft: float = None) -> float:
        """Sanity check volume before tiering."""
        # Check 1: final_vol should >= packed_sum * 0.8
        if packed_sum > 0 and final_vol < packed_sum * 0.8:
            print(f"⚠️ SANITY: final_vol ({final_vol:.2f}) < packed_sum ({packed_sum:.2f}), forcing recompute")
            return packed_sum
        
        # Check 2: volume vs footprint sanity (if available)
        if footprint_sqft and footprint_sqft > 0:
            max_vol_by_footprint = footprint_sqft * 0.5 / 27  # Rough estimate
            if final_vol > max_vol_by_footprint and final_vol > 18:
                print(f"⚠️ SANITY: final_vol ({final_vol:.2f}) exceeds footprint limit, capping at 18")
                return 18.0  # Cap at full load
        
        return final_vol
    
    
    # ==================== PIPELINE v2.4: DETECTION IDENTITY ARCHITECTURE ====================
    
    import hashlib
    
    def generate_detection_id(image_id: int, bbox: list, model_source: str) -> str:
        """Generate stable detection ID from image + bbox + model."""
        bbox_str = "_".join([f"{b:.1f}" for b in bbox]) if bbox else "0_0_0_0"
        raw = f"{image_id}_{bbox_str}_{model_source}"
        return hashlib.md5(raw.encode()).hexdigest()[:12]
    
    # High-impact labels that require confidence gating
    HIGH_IMPACT_GATED = {"hot_tub", "piano", "pool_table", "safe", "demo_heavy"}
    HIGH_IMPACT_VOLUMES = {
        "hot_tub": 6.0,
        "piano": 4.0,
        "pool_table": 5.0,
        "safe": 2.0,
        "demo_heavy": 8.0,
    }
    
    def gate_high_impact_labels(detections: list) -> list:
        """Gate high-impact labels: require 2-model agreement + high confidence."""
        result = []
        for det in detections:
            label = det.get("normalized_label", det.get("label", "")).lower()
            
            if label in HIGH_IMPACT_GATED:
                confidence = det.get("confidence", 0.5)
                model_sources = det.get("model_sources", [det.get("source", "unknown")])
                two_model = len(set(model_sources)) >= 2
                
                if two_model and confidence >= 0.7:
                    # Trusted: use correct high-impact volume
                    det["volume_yards"] = HIGH_IMPACT_VOLUMES.get(label, 3.0)
                    det["gated"] = "APPROVED"
                    print(f"✅ v2.4: {label} approved (2-model, conf={confidence:.2f})")
                else:
                    # Downgrade to unknown_large
                    det["original_label"] = label
                    det["normalized_label"] = "unknown_large"
                    det["label"] = "unknown_large"
                    det["volume_yards"] = 2.0  # Capped
                    det["gated"] = "DOWNGRADED"
                    det["needs_user_confirmation"] = True
                    print(f"⚠️ v2.4: {label} → unknown_large (low conf or single-model)")
            
            result.append(det)
        return result
    
    def collapse_debris_to_bucket(detections: list) -> list:
        """Collapse all debris-like detections into a single bucket."""
        DEBRIS_LABELS = {"mixed_debris", "debris", "debris_pile", "trash", "garbage", "junk_pile"}
        
        debris_items = []
        non_debris = []
        
        for det in detections:
            label = det.get("normalized_label", det.get("label", "")).lower()
            if label in DEBRIS_LABELS:
                debris_items.append(det)
            else:
                non_debris.append(det)
        
        if not debris_items:
            return detections
        
        # Sum all debris footprints
        total_footprint = sum(
            (det.get("bbox", [0,0,0,0])[2] - det.get("bbox", [0,0,0,0])[0]) *
            (det.get("bbox", [0,0,0,0])[3] - det.get("bbox", [0,0,0,0])[1])
            for det in debris_items
        )
        
        # Create single debris bucket
        debris_bucket = {
            "detection_id": "debris_bucket",
            "normalized_label": "mixed_debris",
            "canonical_label": "mixed_debris",
            "label": "mixed_debris",
            "source": "debris_bucket",
            "merged_count": len(debris_items),
            "total_footprint_px": total_footprint,
            "volume_yards": 2.75,  # Default, will be overridden by footprint estimator
            "is_bucket": True,
        }
        
        print(f"🗑️ v2.4: Collapsed {len(debris_items)} debris → 1 bucket (footprint={total_footprint:.0f}px²)")
        
        return non_debris + [debris_bucket]
    
    def normalize_detection_labels(detections: list) -> list:
        """Apply synonym normalization and set normalized_label field."""
        for det in detections:
            original = det.get("label", "unknown")
            normalized = canonicalize_synonym(original.lower())
            det["original_label"] = original
            det["normalized_label"] = normalized
            if normalized != original.lower():
                print(f"🔀 v2.4: {original} → {normalized}")
        return detections
    
    def apply_skip_by_id(detections: list, skip_ids: set) -> list:
        """Filter detections by detection_id (not label)."""
        before = len(detections)
        result = [det for det in detections if det.get("detection_id") not in skip_ids]
        skipped = before - len(result)
        if skipped > 0:
            print(f"🚫 v2.4: Removed {skipped} detections by ID")
        return result
    
    def apply_skip_by_normalized_label(detections: list, skip_labels: set) -> list:
        """Fallback: filter by normalized_label if skip_ids not available."""
        before = len(detections)
        result = [det for det in detections 
                  if det.get("normalized_label", det.get("label", "")).lower() not in skip_labels]
        skipped = before - len(result)
        if skipped > 0:
            print(f"🚫 v2.4: Removed {skipped} detections by normalized label")
        return result
    
    def finalize_detections(detections: list, skip_ids: set = None, skip_labels: set = None, gemini_underdelivered: bool = False) -> list:
        """
        v2.5: Finalize detection list BEFORE any volume math.
        Order: normalize → banned filter → skip → debris bucket → gating → unique/count rules → volume assign
        """
        print("🔒 v2.5: Finalizing detection list...")
        
        # Step 1: Normalize all labels (set normalized_label field)
        detections = normalize_detection_labels(detections)
        
        # Step 2: v2.5 - Filter banned labels (stack, wooden, etc.)
        before_ban = len(detections)
        detections = [det for det in detections 
                      if det.get("normalized_label", det.get("label", "")).lower() not in BANNED_LABELS]
        banned_count = before_ban - len(detections)
        if banned_count > 0:
            print(f"⛔ v2.5: Removed {banned_count} banned labels")
        
        # Step 3: v2.5 - Apply default skip list when Gemini underdelivers
        effective_skip = skip_labels.copy() if skip_labels else set()
        if gemini_underdelivered:
            effective_skip.update(DEFAULT_BACKGROUND_LABELS)
            print(f"⚠️ v2.5: Gemini underdelivered, applying default skip list")
        
        # Step 4: Apply skip (by ID if available, else by normalized label)
        if skip_ids:
            detections = apply_skip_by_id(detections, skip_ids)
        elif effective_skip:
            detections = apply_skip_by_normalized_label(detections, effective_skip)
        
        # Step 5: Collapse debris to single bucket
        detections = collapse_debris_to_bucket(detections)
        
        # Step 6: Gate high-impact labels (hot_tub, piano, etc.)
        detections = gate_high_impact_labels(detections)
        
        # Step 7: v2.5 - Apply STABLE_CATALOG_VOLUMES to all items
        for det in detections:
            label = det.get("normalized_label", det.get("label", "")).lower()
            if label in STABLE_CATALOG_VOLUMES:
                det["volume_yards"] = STABLE_CATALOG_VOLUMES[label]
                det["volume_source"] = "stable_catalog_v2.5"
                print(f"📏 v2.5: {label} → {STABLE_CATALOG_VOLUMES[label]} yd³ (stable)")
        
        # Step 8: Merge duplicate UNIQUE labels
        from collections import Counter
        label_counts = Counter(det.get("normalized_label", det.get("label", "")).lower() for det in detections)
        merged = 0
        for label in UNIQUE_LABELS:
            if label_counts.get(label, 0) > 1:
                instances = [d for d in detections if d.get("normalized_label", d.get("label", "")).lower() == label]
                keep = max(instances, key=lambda x: x.get("bbox_area", 0) or 
                          ((x.get("bbox", [0,0,0,0])[2] - x.get("bbox", [0,0,0,0])[0]) * 
                           (x.get("bbox", [0,0,0,0])[3] - x.get("bbox", [0,0,0,0])[1])))
                detections = [d for d in detections if d.get("normalized_label", d.get("label", "")).lower() != label]
                detections.append(keep)
                merged += label_counts[label] - 1
                print(f"🔀 v2.5: Merged {label_counts[label]} × {label} → 1")
        
        if merged > 0:
            print(f"🔀 v2.5: Total merged: {merged} duplicate unique labels")
        
        print(f"🔒 v2.5: Finalized {len(detections)} detections")
        return detections
    
    # ==================== BILLABLE VOLUME MULTIPLIERS ====================
    # Convert raw volume to billable volume based on item handling difficulty
    CATEGORY_MULTIPLIERS = {
        "furniture": 1.0,        # Standard handling
        "mattress": 1.1,         # Awkward, bulky
        "appliance": 1.2,        # Heavy, loading time
        "appliance_freon": 1.3,  # Handling + disposal (fridge, freezer, AC)
        "ewaste": 1.15,          # Handling + recycling (TVs, monitors)
        "yard_green": 0.9,       # Compressible (bagged leaves)
        "yard_branches": 1.0,    # Awkward, air gaps
        "demo_light": 1.25,      # Heavier + messy (wood, drywall)
        "demo_heavy": 1.6,       # Weight cap risk (concrete, tile, dirt)
        "tires_metal": 1.2,      # Disposal rules
        "bulky_outdoor": 1.4,    # Labor + disassembly (hot tub, shed)
    }
    
    # Map detected item labels to pricing categories
    ITEM_TO_CATEGORY = {
        # Furniture (1.0×)
        "couch": "furniture", "sofa": "furniture", "loveseat": "furniture",
        "sectional": "furniture", "recliner": "furniture", "chair": "furniture",
        "table": "furniture", "desk": "furniture", "dresser": "furniture",
        "nightstand": "furniture", "cabinet": "furniture", "wardrobe": "furniture",
        "bookshelf": "furniture", "shelf": "furniture", "office chair": "furniture",
        
        # Mattress (1.1×)
        "mattress": "mattress", "box spring": "mattress", "bed": "mattress",
        "bed frame": "mattress",
        
        # Appliances - no freon (1.2×)
        "washer": "appliance", "washing machine": "appliance",
        "dryer": "appliance", "stove": "appliance", "oven": "appliance",
        "dishwasher": "appliance", "water heater": "appliance",
        "microwave": "appliance",
        
        # Appliances - freon (1.3×)
        "refrigerator": "appliance_freon", "fridge": "appliance_freon",
        "freezer": "appliance_freon", "mini fridge": "appliance_freon",
        "ac unit": "appliance_freon", "air conditioner": "appliance_freon",
        
        # E-waste (1.15×)
        "tv": "ewaste", "television": "ewaste", "monitor": "ewaste",
        "computer": "ewaste", "crt tv": "ewaste", "printer": "ewaste",
        
        # Yard - green (0.9×)
        "leaves": "yard_green", "grass": "yard_green", "clippings": "yard_green",
        
        # Yard - branches (1.0×)
        "branches": "yard_branches", "brush": "yard_branches", 
        "wood": "yard_branches", "lumber": "yard_branches",
        
        # Demo - light (1.25×)
        "drywall": "demo_light", "carpet": "demo_light", "cardboard": "demo_light",
        "debris": "demo_light",
        
        # Demo - heavy (1.6×)
        "concrete": "demo_heavy", "tile": "demo_heavy", "brick": "demo_heavy",
        "dirt": "demo_heavy", "rocks": "demo_heavy", "rubble": "demo_heavy",
        
        # Tires/Metal (1.2×)
        "tire": "tires_metal", "tires": "tires_metal", 
        "scrap metal": "tires_metal", "metal": "tires_metal",
        
        # Bulky outdoor (1.4×)
        "hot tub": "bulky_outdoor", "spa": "bulky_outdoor",
        "shed": "bulky_outdoor", "playset": "bulky_outdoor",
        "trampoline": "bulky_outdoor", "swing set": "bulky_outdoor",
        "pool": "bulky_outdoor", "gazebo": "bulky_outdoor",
    }
    
    # Add-on fees for special handling (expanded for GPT-5.2)
    ADD_ON_FEES = {
        "mounted": 50,              # Wall-mounted TV removal
        "disassembly": 75,          # Legacy key
        "disassembly_needed": 75,   # Shed, playset, etc. teardown
        "stairs_present": 50,       # Stairs to navigate
        "long_carry": 50,           # Long distance to truck
        "two_person_lift": 100,     # Heavy item requiring 2 people
        "heavy_material": 75,       # Extra handling for heavy debris
        "freon": 25,                # Freon appliance handling
        "ewaste": 0,                # Covered by multiplier
        "tires": 0,                 # Covered by multiplier
        "mattress": 0,              # Covered by multiplier
        "hazmat_possible": 100,     # Potential hazardous materials
    }
    
    # GPT-5.2 category to multiplier mapping
    GPT_CATEGORY_TO_MULTIPLIER = {
        "furniture": 1.0,
        "mattress": 1.1,
        "appliance_non_freon": 1.2,
        "appliance": 1.2,          # Legacy key
        "appliance_freon": 1.3,
        "ewaste_crt": 1.2,         # CRT TVs - heavier
        "ewaste_flat_tv": 1.15,    # Flat screen TVs
        "ewaste_tv": 1.15,         # Legacy key
        "ewaste_other": 1.15,
        "yard_green": 0.9,
        "yard_heavy": 1.6,
        "yard_branches": 1.0,
        "demo_light": 1.25,
        "demo_heavy": 1.6,
        "tires": 1.2,
        "tires_metal": 1.2,        # Legacy key
        "scrap_metal": 1.2,
        "pallets": 1.25,           # Wood pallets
        "boxes_bags": 1.0,
        "bulky_outdoor": 1.4,
        "misc": 1.0,
    }
    
    # Size bucket to volume mapping (for GPT-5.2 missed items)
    SIZE_BUCKET_VOLUMES = {
        "xs": 0.1,
        "small": 0.25,
        "medium": 0.75,
        "large": 1.5,
        "xl": 3.0,
        "unknown": 0.5,
    }
    
    # Default volumes by category (for re-lookup when label is corrected)
    # Used when GPT-5.2 says "this isn't a car, it's a TV" but Florence gave tiny volume
    CATEGORY_DEFAULT_VOLUMES = {
        "furniture": 1.0,           # Average chair/table
        "mattress": 1.3,            # Queen mattress default
        "appliance_non_freon": 1.0, # Washer/dryer default
        "appliance": 1.0,           # Legacy key
        "appliance_freon": 2.5,     # Standard fridge
        "ewaste_tv": 1.2,           # CRT TV default
        "ewaste_other": 0.5,        # Monitor/printer
        "ewaste": 0.8,              # Legacy key
        "yard_green": 0.8,          # Bagged leaves
        "yard_heavy": 2.0,          # Dirt/rocks pile
        "yard_branches": 1.0,       # Brush pile
        "demo_light": 1.5,          # Wood/drywall pile
        "demo_heavy": 2.0,          # Concrete pile
        "tires": 0.5,               # Stack of tires
        "tires_metal": 0.5,         # Legacy key
        "scrap_metal": 1.0,         # Metal pile
        "boxes_bags": 0.3,          # Boxes/bags default
        "bulky_outdoor": 5.0,       # Hot tub default
        "misc": 0.5,                # Unknown items
        "pallets": 1.0,             # 4-pallet stack default
    }
    
    # Missed item volume estimates by variant (legacy support)
    MISSED_ITEM_VOLUMES = {
        # Tires
        "tire_single": 0.15,
        "tire_stack_3": 0.45,
        "tire_stack_6": 0.9,
        
        # Bags
        "bag_kitchen": 0.05,
        "bag_contractor": 0.2,
        "bags_contractor_5": 1.0,
        "bags_contractor_10": 2.0,
        
        # Debris piles
        "debris_small": 0.5,
        "debris_medium": 2.0,
        "debris_large": 5.0,
        
        # Common items
        "box_single": 0.1,
        "boxes_stack": 0.5,
        "furniture_small": 0.5,
        "furniture_large": 2.0,
        
        # Defaults
        "unknown_small": 0.25,
        "unknown_medium": 0.75,
        "unknown_large": 1.5,
    }
    
    # Labels that require Gemma classification (ambiguous)
    AMBIGUOUS_LABELS = ["pile", "debris", "unknown", "junk", "stuff", "items", "trash"]
    
    # Background objects to filter out (not junk items)
    BACKGROUND_LABELS = [
        "car", "truck", "vehicle", "bus", "motorcycle",
        "building", "house", "tree", "sky", "grass", "road", 
        "person", "people", "dog", "cat", "bird",
        "window", "door", "fence", "wall", "parking lot",
        "taillight", "license plate", "tire"  # Parts of cars
    ]
    
    # ==================== OPEN-VOCABULARY DETECTION (Pattern 73) ====================
    # Tiered prompts for GroundingDINO (Progressive Discovery)
    GROUNDING_DINO_PROMPTS = {
        # Tier 1: Broad categories (always run)
        # Includes yard waste, wood pile, construction materials for non-household scenes
        "tier1": (
            "furniture . appliance . mattress . electronics . "
            "debris pile . construction debris . construction materials . "
            "wood pile . boxes . bags . yard waste"
        ),

        # Tier 2: Specific high-value items (run if Tier 1 finds <5 items)
        # Includes cable spools, lumber, plywood, scrap wood, pallet stacks
        "tier2": (
            "pallet . wooden pallet . shipping pallet . pallet stack . stack of pallets . "
            "cable spool . cable reel . wire spool . wooden spool . industrial spool . "
            "lumber stack . stack of wood boards . wood planks . plywood sheet . sheet wood . wood panel . "
            "scrap wood . broken pallets . wood debris . "
            "CRT television . flat screen TV . shelving unit . "
            "refrigerator . washer . dryer . couch . sofa . dresser . desk . table . "
            "tires . scrap metal . metal pipe . "
            "drywall . concrete . bricks"
        ),

        # Tier 3: Edge cases (run if Tier 2 still finds <3 items)
        # Includes crates and large reels for industrial sites
        "tier3": (
            "hot tub . spa . exercise equipment . treadmill . elliptical . piano . "
            "pool table . trampoline . swing set . shed components . fence panels . "
            "wood crate . shipping crate . large cable reel"
        )
    }
    
    # GroundingDINO model identifier (Replicate)
    GROUNDING_DINO_MODEL = "adirik/grounding-dino:efd10a8ddc57ea28773327e881ce95e20cc1d734c589f7dd01d2036921ed78aa"
    
    # Confidence threshold for GroundingDINO detections
    GROUNDING_DINO_CONFIDENCE = 0.35
    
    # Label priority: open-vocab labels take precedence over Florence generic labels
    OPEN_VOCAB_PRIORITY_LABELS = [
        "pallet", "wooden pallet", "shipping pallet", "pallet stack", "stack of pallets",
        "cable spool", "cable reel", "wire spool", "wooden spool", "industrial spool",
        "lumber stack", "wood planks", "plywood sheet", "scrap wood", "wood debris",
        "crt television", "flat screen tv", "shelving unit", 
        "construction debris", "construction materials", "scrap metal", "metal pipe",
        "hot tub", "exercise equipment", "treadmill", "piano", "pool table",
        "wood crate", "shipping crate", "large cable reel"
    ]
    
    # ==================== FIX 1: VALID LABEL DICTIONARY ====================
    # Canonical labels that are allowed (used for similarity matching and filtering)
    VALID_LABELS = {
        # Furniture
        "couch", "sofa", "chair", "table", "desk", "dresser", "bed", "mattress", "bookshelf",
        "shelving unit", "cabinet", "nightstand", "ottoman", "recliner", "futon",
        # Appliances
        "refrigerator", "washer", "dryer", "dishwasher", "microwave", "stove", "oven",
        "air conditioner", "water heater", "freezer", "appliance",
        # Electronics
        "television", "tv", "crt television", "flat screen tv", "computer", "monitor", "printer",
        # Outdoor/Yard
        "yard waste", "wood pile", "debris pile", "construction debris", "construction materials",
        "fence panels", "shed components", "trampoline", "swing set", "lawn mower",
        # Industrial/Commercial
        "pallet", "wooden pallet", "shipping pallet", "pallet stack", "stack of pallets",
        "cable spool", "cable reel", "wire spool", "wooden spool", "industrial spool",
        "cable spool wood", "cable spool mixed", "cable spool metal",
        "lumber stack", "wood planks", "plywood sheet", "scrap wood", "wood debris",
        "wood crate", "shipping crate", "large cable reel",
        "scrap metal", "metal pipe", "drywall", "concrete", "bricks",
        # Misc
        "boxes", "bags", "tires", "hot tub", "spa", "exercise equipment", "treadmill",
        "elliptical", "piano", "pool table", "wheel", "box", "bag", "tire",
        "broken pallets", "sheet wood", "wood panel"
    }
    
    # ==================== FIX 2: SCENE-TYPE GATE ====================
    # Indoor-only categories to suppress in outdoor/construction scenes
    INDOOR_ONLY_CATEGORIES = [
        "appliance", "dresser", "desk", "nightstand", "bookshelf", "ottoman",
        "cabinet", "recliner", "dishwasher", "microwave", "computer", "printer",
        "bed", "futon"
    ]
    
    # Outdoor/construction scene indicators (from detected labels)
    OUTDOOR_SCENE_INDICATORS = [
        "pallet", "wooden pallet", "wood pile", "lumber", "construction debris",
        "yard waste", "fence", "shed", "concrete", "bricks", "drywall",
        "cable spool", "cable reel", "scrap metal", "metal pipe"
    ]
    
    # Minimum bbox area ratio (relative to image) to keep indoor category in outdoor scene
    INDOOR_CATEGORY_MIN_BBOX_RATIO = 0.05  # 5% of image area
    INDOOR_CATEGORY_MIN_CONFIDENCE = 0.6
    
    # ==================== FIX 3: SPOOL CATEGORY MAPPING ====================
    # Explicit spool categories with volumes (in cubic yards)
    SPOOL_CATEGORIES = {
        "cable spool wood": {"volume": 0.8, "category": "misc", "multiplier": 1.0},
        "cable spool mixed": {"volume": 1.0, "category": "misc", "multiplier": 1.1},
        "cable spool metal": {"volume": 1.2, "category": "scrap_metal", "multiplier": 1.2},
        "wooden spool": {"volume": 0.8, "category": "misc", "multiplier": 1.0},
        "industrial spool": {"volume": 1.5, "category": "misc", "multiplier": 1.1},
        "cable spool": {"volume": 0.8, "category": "misc", "multiplier": 1.0},  # Default to wood
        "cable reel": {"volume": 0.8, "category": "misc", "multiplier": 1.0},
        "wire spool": {"volume": 0.6, "category": "misc", "multiplier": 1.0},
        "large cable reel": {"volume": 2.0, "category": "misc", "multiplier": 1.1},
    }
    
    # ==================== CANONICAL LABEL SYSTEM (Recommendations 1-3) ====================
    # Maps detector labels → canonical keys (only canonical drives volume_yards)
    CANONICAL_LABEL_MAP = {
        # Spools → cable_spool_wood (unless clearly metal)
        "wooden spool": "cable_spool_wood",
        "industrial spool": "cable_spool_wood",
        "cable spool": "cable_spool_wood",
        "wire spool": "cable_spool_wood",
        "cable reel": "cable_spool_wood",
        "wooden spool industrial": "cable_spool_wood",
        "wooden spool industrial spool": "cable_spool_wood",
        "large cable reel": "cable_spool_wood",
        "cable spool wood": "cable_spool_wood",
        "cable spool mixed": "cable_spool_mixed",
        "cable spool metal": "cable_spool_metal",
        
        # Pallets → wood_pallet_single or wood_pallet_stack (size determines)
        "wooden pallet": "wood_pallet",
        "wood pallets": "wood_pallet",
        "pallet": "wood_pallet",
        "shipping pallet": "wood_pallet",
        "pallet stack": "wood_pallet_stack",
        "stack of pallets": "wood_pallet_stack",
        "broken pallets": "wood_pallet",
        "wood pallets pile": "wood_pallet_stack",
        
        # Wood piles → wood_boards_stack or scrap_wood_pile
        "wood pile": "wood_boards_stack",
        "lumber stack": "wood_boards_stack",
        "wood planks": "wood_boards_stack",
        "wood boards": "wood_boards_stack",
        "boards pile": "wood_boards_stack",
        "stack of wood boards": "wood_boards_stack",
        "scrap wood": "scrap_wood_pile",
        "wood debris": "scrap_wood_pile",
        "plywood sheet": "plywood_sheets",
        "sheet wood": "plywood_sheets",
        "wood panel": "plywood_sheets",
        
        # Debris → mixed_debris
        "debris pile": "mixed_debris",
        "debris": "mixed_debris",
        "construction debris": "mixed_debris",
        "mixed construction debris": "mixed_debris",
        "pile of mixed debris": "mixed_debris",
        "construction materials": "mixed_debris",
        
        # Tires
        "tires": "tires",
        "tire": "tires",
        "wheel": "tires",  # Will be overridden by Gemini if it's actually a spool
        
        # Pass-through for known items (keeps original)
        "couch": "couch", "sofa": "sofa", "mattress": "mattress",
        "refrigerator": "refrigerator", "washer": "washer", "dryer": "dryer",
        "television": "television", "tv": "television",
        "crt television": "crt_television", "flat screen tv": "flat_screen_tv",
        "hot tub": "hot_tub", "spa": "hot_tub",
        "boxes": "boxes", "bags": "bags", "box": "boxes", "bag": "bags",
        "yard waste": "yard_waste",
    }
    
    # Volume catalog: (canonical_label, size_class) → default yd³
    CANONICAL_VOLUME_CATALOG = {
        # A) cable_spool_wood
        ("cable_spool_wood", "small"): 0.75,
        ("cable_spool_wood", "medium"): 1.40,
        ("cable_spool_wood", "large"): 2.40,
        ("cable_spool_wood", "xl"): 3.75,
        
        # cable_spool_mixed (10% heavier)
        ("cable_spool_mixed", "small"): 0.85,
        ("cable_spool_mixed", "medium"): 1.55,
        ("cable_spool_mixed", "large"): 2.65,
        
        # cable_spool_metal (20% heavier)
        ("cable_spool_metal", "small"): 0.90,
        ("cable_spool_metal", "medium"): 1.70,
        ("cable_spool_metal", "large"): 2.90,
        
        # B) wood_pallet_single
        ("wood_pallet", "small"): 0.35,
        ("wood_pallet", "medium"): 0.45,
        ("wood_pallet", "large"): 0.55,  # Oversized single pallet
        
        # C) wood_pallet_stack
        ("wood_pallet_stack", "small"): 1.00,  # 2-3 pallets
        ("wood_pallet_stack", "medium"): 1.50,  # 3-5 pallets
        ("wood_pallet_stack", "large"): 2.75,  # 6-10 pallets
        ("wood_pallet_stack", "xl"): 3.75,  # Big messy stack
        
        # D) wood_boards_stack
        ("wood_boards_stack", "small"): 0.85,
        ("wood_boards_stack", "medium"): 1.75,
        ("wood_boards_stack", "large"): 2.50,
        
        # E) plywood_sheets
        ("plywood_sheets", "small"): 0.75,
        ("plywood_sheets", "medium"): 1.50,
        ("plywood_sheets", "large"): 2.75,
        
        # F) scrap_wood_pile
        ("scrap_wood_pile", "small"): 1.00,
        ("scrap_wood_pile", "medium"): 2.25,
        ("scrap_wood_pile", "large"): 4.50,
        
        # G) mixed_debris
        ("mixed_debris", "small"): 1.00,
        ("mixed_debris", "medium"): 2.75,
        ("mixed_debris", "large"): 6.00,
        
        # H) tires
        ("tires", "small"): 0.35,  # 1 tire
        ("tires", "medium"): 0.85,  # 2-3 tires
        ("tires", "large"): 1.50,  # 4+ tires
        
        # Yard waste
        ("yard_waste", "small"): 0.50,
        ("yard_waste", "medium"): 1.50,
        ("yard_waste", "large"): 3.00,
    }
    
    # Set of valid canonical labels (for is_valid_label check)
    VALID_CANONICAL_LABELS = set(CANONICAL_LABEL_MAP.values())
    
    # ==================== VOLUME STAGE MACHINE (v3.1) ====================
    VOLUME_STAGES = {"raw": 0, "canonical": 1, "clustered": 2, "final": 3}
    
    # Union coverage grid (memory-safe)
    UNION_GRID_SIZE = 512
    RESIDUAL_ACTIVATION_THRESHOLD = 0.30  # Only activate remainder if > 30%
    
    # DBSCAN clustering config
    DBSCAN_EPS_RATIO = 0.08  # 8% of image diagonal
    DBSCAN_EPS_MAX = 400     # Cap to prevent mega-clusters
    
    # Packing groups (by physical stacking behavior)
    PACKING_GROUPS = {
        "stackable": 0.80,     # Pallets, boxes, lumber
        "nestable": 0.85,      # Tires, spools, buckets
        "compressible": 0.70,  # Bags, yard waste
        "loose": 1.20,         # Debris, scrap (more air gaps)
        "rigid": 1.00,         # Furniture, appliances
    }
    
    LABEL_TO_PACKING_GROUP = {
        "wood_pallet": "stackable", "wood_pallet_stack": "stackable",
        "boxes": "stackable", "wood_boards_stack": "stackable",
        "cable_spool_wood": "nestable", "tires": "nestable",
        "bags": "compressible", "yard_waste": "compressible",
        "mixed_debris": "loose", "scrap_wood_pile": "loose", "demo_debris_pile": "loose",
    }
    
    STACK_LABEL_BONUS = 0.9  # Labels ending in _stack get 10% tighter packing
    
    # ==================== V3.3 ENHANCEMENTS ====================
    # Cluster diameter guard
    MAX_CLUSTER_DIAMETER_RATIO = 0.45  # If cluster > 45% of image, no packing
    
    # Scene mode detection
    SCENE_MODE_THRESHOLDS = {
        "pile_detection_count": 6,      # >= 6 detections = pile mode
        "pile_coverage_threshold": 0.5, # < 50% coverage = pile mode
        "pile_depth_range": 0.5,        # > 0.5 depth range = pile mode
        "single_item_remainder": 0.60,  # Single-item mode: 60% residual threshold
    }
    
    # Remainder multi-trigger config
    REMAINDER_TRIGGERS = {
        "residual_threshold_pile": 0.30,
        "residual_threshold_single": 0.60,
        "min_detections": 6,
        "depth_range_threshold": 0.4
    }
    
    # ==================== PILE VS ITEM ARCHITECTURE ====================
    # Detection types: single_item, stack, pile
    DETECTION_TYPES = {
        "single_item": {"description": "Individual discrete item", "count_range": (1, 2)},
        "stack": {"description": "3-10 items stacked/grouped", "count_range": (3, 10)},
        "pile": {"description": "Bulk/unstructured pile", "count_range": (10, 999)},
    }
    
    # Classification thresholds
    PILE_BBOX_RATIO_THRESHOLD = 0.15  # If bbox > 15% of image, likely pile
    PILE_RESIDUAL_THRESHOLD = 0.30   # If residual > 30%, activate pile estimator
    STACK_COUNT_THRESHOLD = 3        # 3+ same label = stack
    
    # Meta-label pile families (catch-all buckets)
    PILE_FAMILIES = {
        "boxes_bags_stack": {"base_vol": 0.5, "stack_mult": 2.5, "density": 0.6},
        "mixed_household_pile": {"base_vol": 1.0, "stack_mult": 3.0, "density": 0.5},
        "demo_debris_pile": {"base_vol": 2.0, "stack_mult": 4.0, "density": 0.7},
        "yard_waste_pile": {"base_vol": 1.5, "stack_mult": 3.5, "density": 0.4},
        "wood_boards_pile": {"base_vol": 1.5, "stack_mult": 3.0, "density": 0.65},
        "scrap_metal_pile": {"base_vol": 1.0, "stack_mult": 2.5, "density": 0.8},
    }
    
    # Stack modifiers by label type (multiplier for stacked items)
    STACK_MODIFIERS = {
        "wood_pallet": 1.8,      # Pallets stack efficiently
        "cable_spool_wood": 1.5, # Spools stack somewhat
        "boxes": 2.0,            # Boxes stack very efficiently
        "bags": 1.3,             # Bags don't stack well
        "tires": 1.6,            # Tires stack in columns
        "mattress": 1.2,         # Mattresses don't stack well
        "default": 1.5,          # Default stack modifier
    }
    
    # Density modifiers by pile type (compaction factor)
    DENSITY_MODIFIERS = {
        "demo_debris_pile": 1.3,   # Heavy, compacts more
        "yard_waste_pile": 0.7,    # Light, fluffy
        "scrap_metal_pile": 1.4,   # Very heavy
        "wood_boards_pile": 1.0,   # Medium
        "mixed_household_pile": 0.8, # Variable
        "boxes_bags_stack": 0.6,   # Light
        "default": 1.0,
    }
    
    # Heavy materials strict list (Fix 5B)
    HEAVY_MATERIALS = {
        "concrete", "brick", "bricks", "dirt", "soil", "gravel", "rocks", "stone",
        "asphalt", "tile", "ceramic", "cast iron", "lead", "sand", "roofing"
    }
    
    # NOT heavy materials (explicitly exclude)
    NOT_HEAVY_MATERIALS = {
        "wooden spool", "cable spool", "wood", "pallet", "lumber", "drywall",
        "boxes", "bags", "mattress", "furniture", "electronics"
    }
    
    GPT5_AUDIT_PROMPT = """You are an audit model for a junk-removal instant-quote pipeline. Your job is to validate detections and classifications from upstream models and catch missed items. You do not compute prices. You do not write code. You output valid JSON only matching the schema.

Inputs you will receive:
- scene_image: the original photo with bounding boxes drawn and item IDs
- detections: list of detected items (label + bbox + item_id)
- measurements (optional): per-item size buckets or estimated dimensions
- initial_classification: per-item category + variant + add_on_flags

Your tasks:
1. Identify missed items visible in the image that are not in detections.
2. Identify incorrect classifications (wrong category or wrong variant).
3. Identify missing add_on_flags (mounted, disassembly_needed, stairs_present, long_carry, two_person_lift, heavy_material, freon, ewaste, tires, mattress, hazmat_possible).
4. For any missed item, provide a type and size bucket so the pricing engine can assign a default volume.

Hard rules:
- If you are unsure, include the item but mark low confidence and use size_bucket: "unknown".
- Do not invent items that are not visible.
- Do not output explanations. JSON only.
- Use the exact enums provided in the schema below.

Output JSON Schema:
{
  "missed_items": [
    {
      "label": "string",
      "proposed_category": "one_of: [furniture, mattress, appliance_non_freon, appliance_freon, ewaste_tv, ewaste_other, yard_green, yard_heavy, demo_light, demo_heavy, tires, scrap_metal, boxes_bags, misc]",
      "variant": "string_or_unknown",
      "size_bucket": "one_of: [xs, small, medium, large, xl, unknown]",
      "count": "integer>=1",
      "confidence": "number_0_to_1",
      "reason_code": "one_of: [VISIBLE_CLEAR, PARTIALLY_OCCLUDED, EDGE_OF_FRAME, CLUTTERED_SCENE]"
    }
  ],
  "classification_corrections": [
    {
      "item_id": "string",
      "current_category": "string",
      "suggested_category": "string",
      "current_variant": "string_or_unknown",
      "suggested_variant": "string_or_unknown",
      "confidence": "number_0_to_1",
      "reason_code": "one_of: [WRONG_TYPE, WRONG_SIZE_BUCKET, WRONG_MATERIAL_CLASS, MISLABELED_PILE]"
    }
  ],
  "add_on_flag_corrections": [
    {
      "item_id_or_missed_label": "string",
      "add_on_flag": "one_of: [mounted, disassembly_needed, stairs_present, long_carry, two_person_lift, heavy_material, freon, ewaste, tires, mattress, hazmat_possible]",
      "should_be": "boolean",
      "confidence": "number_0_to_1",
      "reason_code": "one_of: [VISUAL_CUE, CONTEXT_CUE, MATERIAL_CUE]"
    }
  ],
  "scene_confidence": "number_0_to_1",
  "uncertainty_band": {
    "risk_level": "one_of: [low, medium, high]",
    "drivers": ["one_of: [OCCLUSION, DEPTH_UNRELIABLE, CLUTTER, REFLECTIONS, FAR_DISTANCE, HEAVY_MATERIAL_UNCERTAINTY]"]
  }
}

Now run the audit using the provided inputs. Output JSON only."""

    class VisionWorker:
        """Handles vision tasks using Florence-2, Depth Pro, and camera intrinsics."""
        
        def __init__(self):
            token = os.environ.get("REPLICATE_API_TOKEN")
            if not token:
                raise ValueError("REPLICATE_API_TOKEN environment variable not set")
            print(f"✅ VisionWorker initialized with token: {token[:8]}...")
        
        # ===== PHASE 1: CAMERA IDENTIFICATION =====
        
        def extract_exif(self, image_bytes: bytes) -> dict:
            """Extract camera info from EXIF metadata."""
            from PIL.ExifTags import TAGS
            try:
                img = Image.open(io.BytesIO(image_bytes))
                exif_raw = img._getexif() or {}
                
                exif = {}
                for tag_id, value in exif_raw.items():
                    tag = TAGS.get(tag_id, tag_id)
                    exif[tag] = value
                
                return {
                    "make": str(exif.get("Make", "")).strip(),
                    "model": str(exif.get("Model", "")).strip(),
                    "focal_length": float(exif.get("FocalLength", 0) or 0),
                    "focal_35mm": int(exif.get("FocalLengthIn35mmFilm", 0) or 0),
                    "image_width": exif.get("ExifImageWidth", img.width),
                    "image_height": exif.get("ExifImageHeight", img.height),
                }
            except Exception as e:
                print(f"⚠️ EXIF extraction failed: {e}")
                return {"make": "", "model": "", "focal_length": 0}
        
        def infer_camera_module(self, exif: dict, device_config: dict) -> tuple:
            """Determine which camera module was used based on focal length."""
            focal_mm = exif.get("focal_length", 0)
            
            best_match = "rear_wide"  # default
            best_diff = float('inf')
            
            for module_name, spec in device_config.items():
                diff = abs(focal_mm - spec.get("focal_mm", 0))
                if diff < best_diff:
                    best_diff = diff
                    best_match = module_name
            
            confidence = "high" if best_diff < 0.5 else "medium"
            return best_match, confidence
        
        def scale_intrinsics(self, K: dict, ref_res: list, actual_res: tuple) -> dict:
            """Scale K matrix when image is resized from reference resolution."""
            scale_x = actual_res[0] / ref_res[0]
            scale_y = actual_res[1] / ref_res[1]
            
            return {
                "fx": K["fx"] * scale_x,
                "fy": K["fy"] * scale_y,
                "cx": K["cx"] * scale_x,
                "cy": K["cy"] * scale_y,
            }
        
        def get_camera_intrinsics(self, image_bytes: bytes, actual_resolution: tuple) -> dict:
            """Main entry point for camera identification. Returns K matrix if known."""
            exif = self.extract_exif(image_bytes)
            device_key = f"{exif['make']} {exif['model']}".strip()
            
            if device_key not in CAMERA_INTRINSICS_DB:
                print(f"📷 Unknown device: {device_key}")
                return {"available": False, "reason": "unknown_device", "device": device_key}
            
            device_config = CAMERA_INTRINSICS_DB[device_key]
            module, module_conf = self.infer_camera_module(exif, device_config)
            
            if module not in device_config:
                module = list(device_config.keys())[0]
            
            spec = device_config[module]
            scaled_K = self.scale_intrinsics(spec["K"], spec["ref_res"], actual_resolution)
            
            print(f"📷 Device: {device_key} ({module}) - K available")
            return {
                "available": True,
                "device": device_key,
                "module": module,
                "K": scaled_K,
                "uncertainty": spec.get("uncertainty", 0.10),
                "module_confidence": module_conf,
            }
        
        # ===== PHASE 2: SCALE CALCULATION =====
        
        def run_depth_pro(self, image_b64: str) -> dict:
            """Run Depth Pro for metric depth estimation."""
            import time
            print("🔬 Running Depth Pro (Metric Depth)...")
            
            try:
                output = replicate.run(
                    DEPTH_PRO_MODEL,
                    input={"image": f"data:image/jpeg;base64,{image_b64}"}
                )
                
                # Depth Pro outputs depth map and optionally focal length
                depth_url = None
                focal_px = None
                
                if isinstance(output, dict):
                    depth_url = str(output.get("depth", output.get("depth_map", "")))
                    focal_px = output.get("focal_length_px") or output.get("focallength_px")
                else:
                    depth_url = str(output)
                
                if depth_url:
                    # Download and parse depth map
                    response = requests.get(depth_url, timeout=30)
                    depth_img = Image.open(io.BytesIO(response.content))
                    import numpy as np
                    depth_array = np.array(depth_img).astype(float)
                    
                    # Normalize if 16-bit (0-65535) to meters
                    if depth_array.max() > 255:
                        # Assume millimeters, convert to meters
                        depth_array = depth_array / 1000.0
                    elif depth_array.max() <= 1:
                        # Already normalized 0-1, scale to reasonable depth (0-10m)
                        depth_array = depth_array * 10.0
                    
                    print(f"✅ Depth Pro: shape={depth_array.shape}, range=[{depth_array.min():.2f}, {depth_array.max():.2f}]m")
                    return {
                        "success": True,
                        "depth_map": depth_array,
                        "focal_px": focal_px,
                        "units": "meters",
                    }
                else:
                    return {"success": False, "error": "No depth URL in output"}
                    
            except Exception as e:
                print(f"❌ Depth Pro Error: {e}")
                import traceback
                traceback.print_exc()
                return {"success": False, "error": str(e)}
        
        def calculate_metric_scale(self, K: dict, depth_map, reference_point: tuple = None) -> dict:
            """Calculate px_per_inch from intrinsics + metric depth using pinhole model."""
            import numpy as np
            
            if reference_point is None:
                h, w = depth_map.shape[:2]
                reference_point = (w // 2, h // 2)
            
            ref_x, ref_y = reference_point
            Z = float(depth_map[ref_y, ref_x])
            
            if Z <= 0.1 or Z > 20:
                return {"success": False, "error": f"Invalid depth: {Z:.2f}m"}
            
            fx = K["fx"]
            px_per_meter = fx / Z
            px_per_inch = px_per_meter / 39.37
            
            return {
                "success": True,
                "px_per_inch": round(px_per_inch, 2),
                "reference_depth_m": round(Z, 2),
                "scale_source": "metric_depth",
            }
        
        def find_anchor(self, detections: list) -> dict:
            """Find best anchor from detections for fallback scale."""
            for det in detections:
                label = det.get("label", "")
                bbox = det.get("bbox", [])
                if len(bbox) == 4:
                    validation = self.validate_anchor(label, bbox)
                    # Check for valid anchor (validate_anchor returns None for non-anchors)
                    if validation and validation.get("aspect_valid"):
                        return {
                            "found": True,
                            "anchor_type": validation["anchor_name"],
                            "anchor_height_px": bbox[3] - bbox[1],
                            "anchor_height_in": validation["size_inches"],
                            "trust": validation["trust"],
                            "bbox": bbox,
                        }
            return {"found": False}
        
        def get_scale(self, image_bytes: bytes, image_b64: str, 
                      intrinsics: dict, detections: list) -> dict:
            """
            Main scale calculation - tries metric path first, falls back to anchor.
            Returns px_per_inch and scale source.
            """
            depth_map = None
            
            # Path A: Metric depth (if intrinsics available)
            if intrinsics.get("available"):
                depth_result = self.run_depth_pro(image_b64)
                
                if depth_result.get("success"):
                    depth_map = depth_result["depth_map"]
                    scale = self.calculate_metric_scale(intrinsics["K"], depth_map)
                    
                    if scale.get("success"):
                        print(f"📐 Metric Scale: {scale['px_per_inch']} px/inch at {scale['reference_depth_m']}m")
                        return {
                            **scale,
                            "depth_map": depth_map,
                            "uncertainty": intrinsics.get("uncertainty", 0.10),
                        }
            
            # Path B: Anchor fallback
            anchor = self.find_anchor(detections)
            if anchor.get("found"):
                px_per_inch = anchor["anchor_height_px"] / anchor["anchor_height_in"]
                uncertainty = {"HIGH": 0.08, "MEDIUM": 0.15, "LOW": 0.25}.get(anchor["trust"], 0.20)
                print(f"📐 Anchor Scale: {px_per_inch:.2f} px/inch from {anchor['anchor_type']} ({anchor['trust']})")
                return {
                    "success": True,
                    "px_per_inch": round(px_per_inch, 2),
                    "scale_source": "anchor",
                    "anchor_type": anchor["anchor_type"],
                    "anchor_trust": anchor["trust"],
                    "uncertainty": uncertainty,
                    "depth_map": depth_map,  # may be None
                }
            
            # No scale available
            print("⚠️ No scale source available (no intrinsics or anchor)")
            return {
                "success": False,
                "scale_source": "none",
                "error": "No intrinsics or anchor available",
                "uncertainty": 0.40,
            }
        
        def validate_anchor(self, label: str, bbox: list) -> dict:
            """Validate an anchor by checking aspect ratio against expected range."""
            for anchor_name, config in ANCHOR_REGISTRY.items():
                names_to_check = [anchor_name] + config.get("aliases", [])
                if any(name in label.lower() for name in names_to_check):
                    width = bbox[2] - bbox[0]
                    height = bbox[3] - bbox[1]
                    if height <= 0:
                        continue
                    aspect = width / height
                    min_aspect, max_aspect = config["aspect_ratio"]
                    is_valid = min_aspect <= aspect <= max_aspect
                    
                    result = {
                        "anchor_name": anchor_name,
                        "size_inches": config["size_inches"],
                        "trust": config["trust"],
                        "aspect_valid": is_valid,
                        "aspect_ratio": round(aspect, 2),
                        "bbox_height_px": height
                    }
                    print(f"🔑 Anchor validated: {anchor_name} ({config['trust']} trust, aspect={result['aspect_ratio']}, valid={is_valid})")
                    return result
            return None
        
        def cross_validate_anchors(self, validated_anchors: list) -> dict:
            """Cross-validate multiple anchors to derive px_per_inch scale."""
            if not validated_anchors:
                return {"scale": None, "confidence": "NONE", "anchor_used": None}
            
            trust_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
            sorted_anchors = sorted(validated_anchors, key=lambda a: (trust_order.get(a["trust"], 3), not a["aspect_valid"]))
            
            best = sorted_anchors[0]
            if not best["aspect_valid"]:
                return {"scale": None, "confidence": "LOW", "reason": "No aspect-valid anchors", "anchor_used": best["anchor_name"]}
            
            px_per_inch = best["bbox_height_px"] / best["size_inches"]
            result = {
                "scale": round(px_per_inch, 3),
                "anchor_used": best["anchor_name"],
                "trust": best["trust"],
                "confidence": "HIGH" if best["trust"] == "HIGH" else "MEDIUM"
            }
            print(f"📐 Scale: {result['scale']} px/inch from {best['anchor_name']} ({result['confidence']} confidence)")
            return result
        
        def lookup_item_volume(self, label: str, bbox: list, image_dims: tuple) -> dict:
            """Lookup item volume from catalog, inferring size from bbox area."""
            norm_label = label.lower().strip()
            
            for item_name, config in ITEM_CATALOG.items():
                if item_name in norm_label or norm_label in item_name:
                    bbox_area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
                    image_area = image_dims[0] * image_dims[1] if image_dims[0] > 0 and image_dims[1] > 0 else 1
                    area_ratio = bbox_area / image_area
                    
                    # Size thresholds: <5% = small, 5-15% = medium, >15% = large
                    if area_ratio < 0.05:
                        size_idx, size_label = 0, "small"
                    elif area_ratio < 0.15:
                        size_idx, size_label = 1, "medium"
                    else:
                        size_idx, size_label = 2, "large"
                    
                    vol = config["vol_range"][size_idx]
                    return {"volume": vol, "void": config["void"], "size": size_label, "matched": item_name}
            
            return {"volume": 0.05, "void": 0.0, "size": "unknown", "matched": None}
        
        def calculate_catalog_volume(self, detections: list, image_dims: tuple = (320, 320)) -> dict:
            """Calculate total volume from catalog lookups."""
            total_vol = 0.0
            total_void = 0.0
            items = []
            
            for det in detections:
                if det.get("type") == "anchor":
                    continue
                result = self.lookup_item_volume(det["label"], det.get("bbox", [0,0,0,0]), image_dims)
                total_vol += result["volume"]
                total_void += result["volume"] * result["void"]
                items.append({"label": det["label"], **result})
            
            catalog_result = {
                "gross_volume": round(total_vol, 2),
                "void_volume": round(total_void, 2),
                "net_volume": round(total_vol - total_void, 2),
                "item_count": len(items),
                "items": items
            }
            print(f"📦 Catalog Volume: {catalog_result['net_volume']} yd³ ({len(items)} items)")
            return catalog_result
        
        def bbox_area(self, bbox: list) -> float:
            """Calculate area of a bounding box."""
            if len(bbox) != 4:
                return 0
            return (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
        
        def bbox_intersection(self, box1: list, box2: list) -> float:
            """Calculate intersection area of two bboxes."""
            if len(box1) != 4 or len(box2) != 4:
                return 0
            x1 = max(box1[0], box2[0])
            y1 = max(box1[1], box2[1])
            x2 = min(box1[2], box2[2])
            y2 = min(box1[3], box2[3])
            if x2 <= x1 or y2 <= y1:
                return 0
            return (x2 - x1) * (y2 - y1)
        
        def calculate_residual_pile_area(self, detections: list) -> dict:
            """Subtract solid item footprints from pile area to estimate loose debris."""
            if not detections:
                return {"pile_area": 0, "subtracted_area": 0, "residual_area": 0, "coverage_ratio": 0}
            
            pile_bbox = self.get_pile_bbox(detections)
            if not pile_bbox:
                return {"pile_area": 0, "subtracted_area": 0, "residual_area": 0, "coverage_ratio": 0}
            
            pile_area = self.bbox_area(pile_bbox)
            subtracted_area = 0
            
            for det in detections:
                bbox = det.get("bbox", [])
                if len(bbox) == 4:
                    intersection = self.bbox_intersection(pile_bbox, bbox)
                    subtracted_area += intersection
            
            residual_area = max(0, pile_area - subtracted_area)
            coverage = subtracted_area / pile_area if pile_area > 0 else 0
            
            result = {
                "pile_area": round(pile_area, 1),
                "subtracted_area": round(subtracted_area, 1),
                "residual_area": round(residual_area, 1),
                "coverage_ratio": round(coverage, 2)
            }
            print(f"📐 Pile Analysis: {result['coverage_ratio']*100:.0f}% covered by items, {result['residual_area']:.0f}px² residual")
            return result
        
        def calculate_pipeline_confidence(self, context: dict) -> dict:
            """Calculate overall confidence score from all inputs."""
            score = 0.0
            factors = []
            
            # Anchor contribution
            trust = context.get("anchor_trust")
            if trust == "HIGH":
                score += CONFIDENCE_FACTORS["anchor_high_trust"]
                factors.append("HIGH anchor")
            elif trust == "MEDIUM":
                score += CONFIDENCE_FACTORS["anchor_medium_trust"]
                factors.append("MEDIUM anchor")
            elif trust == "LOW":
                score += CONFIDENCE_FACTORS["anchor_low_trust"]
                factors.append("LOW anchor")
            else:
                score += CONFIDENCE_FACTORS["no_anchor"]
                factors.append("No anchor")
            
            # Depth contribution
            if context.get("depth_available"):
                score += CONFIDENCE_FACTORS["depth_available"]
                factors.append("Depth")
            
            # Multi-image contribution
            image_count = context.get("image_count", 1)
            if image_count > 1:
                score += CONFIDENCE_FACTORS["multi_image"] * (image_count - 1)
                factors.append(f"{image_count} imgs")
            
            # Catalog match contribution
            if context.get("catalog_match_ratio", 0) > 0.5:
                score += CONFIDENCE_FACTORS["catalog_match_ratio"]
                factors.append("Good catalog")
            
            # Determine mode and band width
            mode = "SHADOW"
            band = 0.50
            for mode_name, config in MODE_THRESHOLDS.items():
                if score >= config["threshold"]:
                    mode = mode_name
                    band = config["band"]
                    break
            
            result = {"score": round(min(score, 1.5), 2), "mode": mode, "band": band, "factors": factors}
            print(f"🎯 Confidence: {result['score']} ({mode}) - {', '.join(factors)}")
            return result
        
        def _base64_to_file(self, image_base64: str):
            img_bytes = base64.b64decode(image_base64)
            return io.BytesIO(img_bytes)
        
        def run_florence_detection(self, image_base64: str) -> dict:
            print("🔍 Running Florence-2 Object Detection...")
            try:
                img_file = self._base64_to_file(image_base64)
                output = replicate.run(
                    FLORENCE_MODEL,
                    input={"image": img_file, "task_input": "Object Detection"}
                )
                print(f"✅ Florence-2 output: {output}")
                return self._parse_florence_output(output)
            except Exception as e:
                print(f"❌ Florence-2 Error: {e}")
                return {"detections": [], "error": str(e)}
        
        def run_grounding_dino(self, image_base64: str, tier: str = "tier1") -> list:
            """Run GroundingDINO open-vocabulary detection with tiered prompting."""
            try:
                prompt = GROUNDING_DINO_PROMPTS.get(tier, GROUNDING_DINO_PROMPTS["tier1"])
                print(f"🎯 GroundingDINO ({tier}): '{prompt[:50]}...'")
                
                img_file = self._base64_to_file(image_base64)
                
                output = replicate.run(
                    GROUNDING_DINO_MODEL,
                    input={
                        "image": img_file,
                        "query": prompt,
                        "box_threshold": GROUNDING_DINO_CONFIDENCE,
                        "text_threshold": GROUNDING_DINO_CONFIDENCE
                    }
                )
                
                # Parse GroundingDINO output format
                detections = []
                if output:
                    # GroundingDINO returns list of detections directly
                    if isinstance(output, list):
                        for det in output:
                            detections.append({
                                "label": det.get("label", "unknown"),
                                "bbox": det.get("box", [0, 0, 0, 0]),
                                "confidence": det.get("score", 0.0),
                                "source": "grounding_dino",
                                "tier": tier
                            })
                    elif isinstance(output, dict) and "detections" in output:
                        for det in output["detections"]:
                            detections.append({
                                "label": det.get("label", "unknown"),
                                "bbox": det.get("box", [0, 0, 0, 0]),
                                "confidence": det.get("score", 0.0),
                                "source": "grounding_dino",
                                "tier": tier
                            })
                
                print(f"   ✓ GroundingDINO found {len(detections)} items")
                return detections
                
            except Exception as e:
                print(f"⚠️ GroundingDINO failed: {e}")
                return []
        
        def run_tiered_detection(self, image_base64: str) -> list:
            """Run tiered GroundingDINO detection with progressive refinement."""
            all_detections = []
            
            # Tier 1: Broad categories
            tier1_results = self.run_grounding_dino(image_base64, "tier1")
            all_detections.extend(tier1_results)
            
            # Tier 2: Specific items (if Tier 1 sparse)
            if len(tier1_results) < 5:
                print("   📈 Tier 1 sparse, running Tier 2...")
                import time
                time.sleep(12)  # Rate limit mitigation
                tier2_results = self.run_grounding_dino(image_base64, "tier2")
                all_detections.extend(tier2_results)
                
                # Tier 3: Edge cases (if still sparse)
                if len(tier1_results) + len(tier2_results) < 3:
                    print("   📈 Tier 2 sparse, running Tier 3...")
                    time.sleep(12)
                    tier3_results = self.run_grounding_dino(image_base64, "tier3")
                    all_detections.extend(tier3_results)
            
            return all_detections
        
        def is_valid_label(self, label: str) -> bool:
            """FIX 1: Filter out tokenization garbage and invalid labels."""
            if not label:
                return False
            label_lower = label.lower().strip()
            
            # Filter subword tokens (## prefix from BERT tokenization)
            if "##" in label_lower:
                print(f"   ⛔ Filtered garbage token: {label}")
                return False
            
            # Filter too short labels
            if len(label_lower) < 4:
                print(f"   ⛔ Filtered short label: {label}")
                return False
            
            # Check if label is in valid dictionary or is a substring match
            if label_lower in VALID_LABELS:
                return True
            
            # Check for partial matches (e.g., "wooden pallet" contains "pallet")
            for valid in VALID_LABELS:
                if valid in label_lower or label_lower in valid:
                    return True
            
            print(f"   ⚠️ Unknown label, allowing with caution: {label}")
            return True  # Allow unknown labels but log them
        
        def normalize_to_canonical(self, label: str) -> str:
            """Normalize detector label to canonical key."""
            label_lower = label.lower().strip()
            
            # Direct lookup in canonical map
            if label_lower in CANONICAL_LABEL_MAP:
                return CANONICAL_LABEL_MAP[label_lower]
            
            # Check for substring matches
            for raw, canonical in CANONICAL_LABEL_MAP.items():
                if raw in label_lower or label_lower in raw:
                    return canonical
            
            # Fallback: return as-is (will use default volume)
            return label_lower.replace(" ", "_")
        
        def get_canonical_volume(self, canonical_label: str, size_class: str) -> float:
            """Get volume from canonical catalog, with fallbacks."""
            # Small scrap exception - intentionally keep tiny
            SMALL_SCRAP_LABELS = {"loose_scrap", "plastic_pieces", "tiny_debris", "small_trash"}
            if canonical_label in SMALL_SCRAP_LABELS:
                return 0.15
            
            # Try exact match
            key = (canonical_label, size_class)
            if key in CANONICAL_VOLUME_CATALOG:
                return CANONICAL_VOLUME_CATALOG[key]
            
            # Try with medium as fallback
            if (canonical_label, "medium") in CANONICAL_VOLUME_CATALOG:
                return CANONICAL_VOLUME_CATALOG[(canonical_label, "medium")]
            
            # Try with small as fallback
            if (canonical_label, "small") in CANONICAL_VOLUME_CATALOG:
                return CANONICAL_VOLUME_CATALOG[(canonical_label, "small")]
            
            # v2.2 HOTFIX: Use bounded supercategory fallback instead of flat values
            fallback_data = get_fallback_volume_v21(canonical_label, size_class)
            vol = fallback_data.get("vol", 0.75)
            category = fallback_data.get("category", "unknown")
            vol_range = fallback_data.get("range", (0.3, 1.0))
            print(f"   ⚠️ No catalog entry for ({canonical_label}, {size_class}), using v2.2 fallback: {vol:.2f} yd³ ({category}, range={vol_range})")
            return vol
        
        def apply_canonical_labels(self, detections: list, gemini_classifications: list = None) -> list:
            """Apply canonical label system to detections (Recommendation 4)."""
            gemini_map = {}
            if gemini_classifications:
                for gc in gemini_classifications:
                    item_label = gc.get("item", "").lower()
                    gemini_map[item_label] = gc
            
            for det in detections:
                raw_label = det.get("label", "")
                det["raw_label"] = raw_label
                
                # Priority: Gemini's corrected_label > detector label
                gemini_info = gemini_map.get(raw_label.lower(), {})
                corrected_label = gemini_info.get("corrected_label", raw_label)
                det["corrected_label"] = corrected_label
                
                # Normalize to canonical
                canonical_label = self.normalize_to_canonical(corrected_label)
                det["canonical_label"] = canonical_label
                det["label"] = canonical_label  # Overwrite for consistency
                
                # Validate canonical label
                det["is_valid_label"] = (
                    canonical_label in VALID_CANONICAL_LABELS or
                    not ("##" in raw_label) and len(raw_label) >= 4
                )
                
                # Get size class (from existing or default)
                size_class = det.get("size_class", "medium")
                
                # Apply canonical volume
                det["volume_yards"] = self.get_canonical_volume(canonical_label, size_class)
                
                # Add Gemini fields if present
                if gemini_info:
                    det["category"] = gemini_info.get("category", "misc")
                    det["add_on_flags"] = gemini_info.get("add_on_flags", [])
                    det["gemini_confidence"] = gemini_info.get("confidence", 0.5)
                
                print(f"   📝 {raw_label} → {canonical_label} ({size_class}) = {det['volume_yards']} yd³")
            
            return detections
        
        def classify_detection_type(self, detections: list, image_area: float) -> list:
            """Classify each detection as single_item, stack, or pile."""
            # Count labels across detections
            label_counts = {}
            for det in detections:
                label = det.get("canonical_label", det.get("label", "")).lower()
                label_counts[label] = label_counts.get(label, 0) + 1
            
            for det in detections:
                label = det.get("canonical_label", det.get("label", "")).lower()
                bbox = det.get("bbox", [0, 0, 0, 0])
                confidence = det.get("confidence", 0.5)
                
                # Calculate bbox area ratio
                bbox_area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1]) if len(bbox) >= 4 else 0
                bbox_ratio = bbox_area / image_area if image_area > 0 else 0
                
                # Classification rules
                detection_type = "single_item"
                
                # Rule 1: Large bbox = pile
                if bbox_ratio >= PILE_BBOX_RATIO_THRESHOLD:
                    detection_type = "pile"
                    print(f"   📦 {label}: pile (bbox {bbox_ratio:.1%} of image)")
                
                # Rule 2: Multiple same labels = stack
                elif label_counts.get(label, 0) >= STACK_COUNT_THRESHOLD:
                    detection_type = "stack"
                    print(f"   📦 {label}: stack ({label_counts[label]} instances)")
                
                # Rule 3: Check if label is a known pile family
                elif any(pile_name in label for pile_name in PILE_FAMILIES.keys()):
                    detection_type = "pile"
                    print(f"   📦 {label}: pile (pile family)")
                
                det["detection_type"] = detection_type
                det["label_count"] = label_counts.get(label, 1)
            
            return detections
        
        def calculate_modifier_volume(self, det: dict) -> float:
            """Calculate volume using base × modifiers (not static)."""
            canonical_label = det.get("canonical_label", det.get("label", ""))
            detection_type = det.get("detection_type", "single_item")
            size_class = det.get("size_class", "medium")
            base_volume = det.get("volume_yards", 0.5)
            
            # Get stack modifier
            stack_mod = 1.0
            if detection_type in ["stack", "pile"]:
                stack_mod = STACK_MODIFIERS.get(canonical_label, STACK_MODIFIERS.get("default", 1.5))
            
            # Get density modifier for piles
            density_mod = 1.0
            if detection_type == "pile":
                density_mod = DENSITY_MODIFIERS.get(canonical_label, DENSITY_MODIFIERS.get("default", 1.0))
            
            # Calculate final volume
            final_volume = base_volume * stack_mod * density_mod
            
            # Store modifiers for debug
            det["stack_modifier"] = stack_mod
            det["density_modifier"] = density_mod
            det["volume_yards_modified"] = round(final_volume, 2)
            
            if detection_type != "single_item":
                print(f"   🔢 {canonical_label}: {base_volume:.2f} × stack({stack_mod}) × density({density_mod}) = {final_volume:.2f} yd³")
            
            return final_volume
        
        def estimate_pile_remainder(self, detections: list, image_width: int, image_height: int, 
                                     depth_stats: dict = None) -> dict:
            """Estimate residual volume for undetected pile portions."""
            image_area = image_width * image_height
            
            # Calculate total detected bbox area
            total_bbox_area = 0
            for det in detections:
                bbox = det.get("bbox", [0, 0, 0, 0])
                if bbox and len(bbox) >= 4:
                    total_bbox_area += (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
            
            detected_coverage = total_bbox_area / image_area if image_area > 0 else 0
            residual_coverage = max(0, 1.0 - detected_coverage)
            
            # Check if pile remainder needs to be calculated
            if residual_coverage < PILE_RESIDUAL_THRESHOLD:
                return {"remainder_volume_yards": 0, "activated": False}
            
            # Estimate pile footprint (conservative: 40% of residual actually has stuff)
            pile_footprint_ratio = residual_coverage * 0.4
            
            # Convert to approximate square feet (assume image covers ~100-200 sqft area)
            estimated_sqft = pile_footprint_ratio * 150  # Conservative estimate
            
            # Estimate height from depth or use default (3ft)
            estimated_height_ft = 3.0
            if depth_stats:
                depth_range = depth_stats.get("max", 1.0) - depth_stats.get("min", 0.0)
                if depth_range > 0.2:
                    estimated_height_ft = min(depth_range * 6, 5.0)  # Scale, cap at 5ft
            
            # Volume in cubic yards
            remainder_cuft = estimated_sqft * estimated_height_ft
            remainder_yards = remainder_cuft / 27
            
            print(f"   📊 Pile Remainder: residual={residual_coverage:.1%}, footprint={estimated_sqft:.0f}sqft, height={estimated_height_ft:.1f}ft → {remainder_yards:.1f} yd³")
            
            return {
                "remainder_volume_yards": round(remainder_yards, 2),
                "activated": True,
                "residual_coverage": residual_coverage,
                "estimated_sqft": estimated_sqft,
                "estimated_height_ft": estimated_height_ft
            }
        
        def spatial_cluster_detections(self, detections: list, img_w: int, img_h: int) -> list:
            """DBSCAN spatial clustering with diagonal-based eps."""
            import math
            try:
                from sklearn.cluster import DBSCAN
                import numpy as np
            except ImportError:
                print("   ⚠️ sklearn not available, skipping DBSCAN")
                for det in detections:
                    det["spatial_cluster_id"] = 0
                    det["cluster_size"] = 1
                return detections
            
            # Diagonal-based eps
            diagonal = math.sqrt(img_w**2 + img_h**2)
            eps = min(diagonal * DBSCAN_EPS_RATIO, DBSCAN_EPS_MAX)
            
            # Group by canonical label first
            label_groups = {}
            for det in detections:
                label = det.get("canonical_label", det.get("label", ""))
                label_groups.setdefault(label, []).append(det)
            
            for label, items in label_groups.items():
                if len(items) == 1:
                    items[0]["spatial_cluster_id"] = 0
                    items[0]["cluster_size"] = 1
                    continue
                
                # Extract centroids
                centroids = []
                for item in items:
                    bbox = self.normalize_bbox_v31(item.get("bbox"), img_w, img_h)
                    cx = (bbox[0] + bbox[2]) / 2
                    cy = (bbox[1] + bbox[3]) / 2
                    centroids.append([cx, cy])
                
                # DBSCAN clustering
                X = np.array(centroids)
                clustering = DBSCAN(eps=eps, min_samples=1).fit(X)
                
                for i, item in enumerate(items):
                    item["spatial_cluster_id"] = int(clustering.labels_[i])
            
            return detections
        
        def calculate_cluster_volumes_v31(self, detections: list, img_w: int, img_h: int) -> list:
            """Calculate cluster volumes with DBSCAN and packing groups."""
            detections = self.spatial_cluster_detections(detections, img_w, img_h)
            
            # Group by (label, spatial_cluster_id)
            clusters = {}
            for det in detections:
                key = (det.get("canonical_label"), det.get("spatial_cluster_id", 0))
                clusters.setdefault(key, []).append(det)
            
            for (label, cluster_id), items in clusters.items():
                n = len(items)
                sum_base = sum(d.get("volume_yards", 0.75) for d in items)
                
                # Get packing factor from group
                group = LABEL_TO_PACKING_GROUP.get(label, "rigid")
                packing = PACKING_GROUPS.get(group, 1.0)
                
                # Stack-type override for _stack labels
                if label and (label.endswith("_stack") or any(d.get("pile_type") == "stack" for d in items)):
                    packing *= STACK_LABEL_BONUS
                
                # Only apply packing to 2+ items
                if n == 1:
                    packing = 1.0
                
                cluster_vol = round(sum_base * packing, 2)
                
                # First item holds cluster data
                items[0]["cluster_volume"] = cluster_vol
                items[0]["cluster_size"] = n
                items[0]["packing_group"] = group
                items[0]["packing_factor"] = packing
                
                # Mark other items as cluster members
                for item in items[1:]:
                    item["in_cluster"] = f"{label}_{cluster_id}"
                    item["volume_yards"] = 0
                
                # Set volume stage
                for item in items:
                    item["volume_stage"] = VOLUME_STAGES["clustered"]
                    item["volume_stage_name"] = "clustered"
                
                if n > 1:
                    print(f"   📦 {label}[{cluster_id}]: {n}× × pack({packing:.2f}) = {cluster_vol:.2f} yd³")
            
            return detections
        
        def estimate_pile_remainder_v31(self, detections: list, img_w: int, img_h: int, 
                                         total_item_vol: float, depth_stats: dict = None) -> dict:
            """v3.1 remainder with union coverage and % threshold."""
            covered = self.calculate_union_coverage(detections, img_w, img_h)
            residual_pct = max(0, 1.0 - covered)
            
            # Only activate if residual > 30%
            if residual_pct < RESIDUAL_ACTIVATION_THRESHOLD:
                print(f"   📊 Residual {residual_pct:.1%} < {RESIDUAL_ACTIVATION_THRESHOLD:.0%}, skipping remainder")
                return {"remainder_yards": 0, "activated": False, "residual_pct": residual_pct}
            
            footprint = residual_pct * 0.4 * 150
            height = 3.0
            if depth_stats:
                depth_range = depth_stats.get("range", depth_stats.get("max", 1.0) - depth_stats.get("min", 0.0))
                if depth_range > 0.2:
                    height = min(depth_range * 6, 5.0)
            
            remainder = (footprint * height) / 27
            
            # Two-part cap
            max_remainder = max(total_item_vol * 0.5, 2.0)
            remainder = min(remainder, max_remainder)
            
            print(f"   📊 Pile Remainder v3.1: coverage={covered:.1%}, residual={residual_pct:.1%}, remainder={remainder:.2f} yd³")
            
            return {"remainder_yards": round(remainder, 2), "activated": True, "residual_pct": residual_pct}
        
        def is_heavy_material(self, label: str, add_on_flags: list = None) -> bool:
            """Fix 5B: Strict check for heavy materials."""
            label_lower = label.lower()
            
            # Explicit exclude
            for not_heavy in NOT_HEAVY_MATERIALS:
                if not_heavy in label_lower:
                    return False
            
            # Explicit include
            for heavy in HEAVY_MATERIALS:
                if heavy in label_lower:
                    return True
            
            return False
        
        def create_audit_item(self, label: str, category: str, volume: float, bbox: list) -> dict:
            """Create fresh audit item - no inherited cluster state."""
            return {
                "canonical_label": label,
                "label": label,
                "category": category,
                "volume_yards": volume,
                "bbox": bbox,
                "volume_stage": VOLUME_STAGES["raw"],
                "volume_stage_name": "raw",
                "in_cluster": None,
                "cluster_volume": None,
                "spatial_cluster_id": None,
                "needs_volume_recompute": True,
                "source": "audit_added"
            }
        
        def normalize_bbox_v31(self, bbox: list, img_w: int, img_h: int) -> list:
            """Normalize bbox with robust coordinate detection."""
            if not bbox or len(bbox) < 4:
                return [0, 0, 0, 0]
            x1, y1, x2, y2 = bbox
            
            # Invalid bbox check
            if x2 <= x1 or y2 <= y1:
                return [0, 0, 0, 0]
            
            # Detect coordinate space
            if x2 > 1.5 or y2 > 1.5:
                # Pixels - clamp to image bounds
                return [max(0, x1), max(0, y1), min(img_w, x2), min(img_h, y2)]
            else:
                # Normalized - convert to pixels
                return [x1 * img_w, y1 * img_h, x2 * img_w, y2 * img_h]
        
        def calculate_union_coverage(self, detections: list, img_w: int, img_h: int) -> float:
            """Calculate union coverage on 512×512 grid (memory-safe)."""
            import numpy as np
            grid = np.zeros((UNION_GRID_SIZE, UNION_GRID_SIZE), dtype=bool)
            scale_x = UNION_GRID_SIZE / img_w
            scale_y = UNION_GRID_SIZE / img_h
            
            for det in detections:
                bbox = self.normalize_bbox_v31(det.get("bbox"), img_w, img_h)
                x1, y1, x2, y2 = bbox
                
                gx1 = max(0, int(x1 * scale_x))
                gy1 = max(0, int(y1 * scale_y))
                gx2 = min(UNION_GRID_SIZE, int(x2 * scale_x))
                gy2 = min(UNION_GRID_SIZE, int(y2 * scale_y))
                
                # Ensure at least 1 pixel for tiny boxes
                gx2 = max(gx2, gx1 + 1)
                gy2 = max(gy2, gy1 + 1)
                
                grid[gy1:gy2, gx1:gx2] = True
            
            coverage = np.sum(grid) / (UNION_GRID_SIZE ** 2)
            return coverage
        
        # ==================== V3.3 FUNCTIONS ====================
        
        def normalize_all_bboxes(self, detections: list, img_w: int, img_h: int) -> list:
            """Phase 1: Normalize ALL bboxes to pixels immediately after merge."""
            for det in detections:
                det["bbox_pixels"] = self.normalize_bbox_v31(det.get("bbox"), img_w, img_h)
            return detections
        
        def detect_scene_mode(self, detections: list, depth_stats: dict, coverage: float) -> str:
            """Phase 5: Detect if scene is pile or single_item mode."""
            if len(detections) >= SCENE_MODE_THRESHOLDS["pile_detection_count"]:
                return "pile"
            if coverage < SCENE_MODE_THRESHOLDS["pile_coverage_threshold"]:
                return "pile"
            if depth_stats and depth_stats.get("range", 0) > SCENE_MODE_THRESHOLDS["pile_depth_range"]:
                return "pile"
            return "single_item"
        
        def validate_cluster_diameter(self, cluster_items: list, img_w: int, img_h: int):
            """Phase 4: Check if cluster is too spread out for packing."""
            import math
            if not cluster_items:
                return None
            
            # Get union of all bboxes in cluster
            x1_min = min(d.get("bbox_pixels", [0,0,0,0])[0] for d in cluster_items)
            y1_min = min(d.get("bbox_pixels", [0,0,0,0])[1] for d in cluster_items)
            x2_max = max(d.get("bbox_pixels", [0,0,0,0])[2] for d in cluster_items)
            y2_max = max(d.get("bbox_pixels", [0,0,0,0])[3] for d in cluster_items)
            
            cluster_diag = math.sqrt((x2_max - x1_min)**2 + (y2_max - y1_min)**2)
            img_diag = math.sqrt(img_w**2 + img_h**2)
            
            if cluster_diag > img_diag * MAX_CLUSTER_DIAMETER_RATIO:
                print(f"   ⚠️ Cluster too spread ({cluster_diag:.0f} / {img_diag:.0f}), packing=1.0")
                return 1.0  # No packing for spread-out items
            return None
        
        def should_activate_remainder(self, mode: str, residual_pct: float, detections: list, 
                                       anchor_present: bool, depth_stats: dict) -> bool:
            """Phase 5: Mode-aware remainder trigger."""
            if mode == "pile":
                return (
                    residual_pct > REMAINDER_TRIGGERS["residual_threshold_pile"] or
                    len(detections) < REMAINDER_TRIGGERS["min_detections"] or
                    not anchor_present or
                    (depth_stats and depth_stats.get("range", 0) > REMAINDER_TRIGGERS["depth_range_threshold"])
                )
            else:  # single_item
                return residual_pct > REMAINDER_TRIGGERS["residual_threshold_single"]
        
        def compute_pipeline_hash(self, detections: list, remainder: dict) -> str:
            """Phase 8: SHA-256 hash with full signature."""
            import hashlib
            import json
            
            signature = {
                "labels": sorted([d.get("canonical_label", "") for d in detections]),
                "bboxes": [[int(b) for b in d.get("bbox_pixels", [0,0,0,0])] for d in detections],
                "sizes": [d.get("size_class", "medium") for d in detections],
                "clusters": [(d.get("canonical_label", ""), d.get("spatial_cluster_id", 0)) for d in detections],
                "remainder": {
                    "activated": remainder.get("activated", False),
                    "yards": remainder.get("remainder_yards", 0)
                }
            }
            return hashlib.sha256(json.dumps(signature, sort_keys=True).encode()).hexdigest()[:16]
        
        def finalize_volumes(self, detections: list, remainder: dict) -> str:
            """Phase 8: Auto-lock with hash."""
            pipeline_hash = self.compute_pipeline_hash(detections, remainder)
            for det in detections:
                det["volume_stage"] = VOLUME_STAGES["final"]
                det["volume_stage_name"] = "final"
                det["pipeline_hash"] = pipeline_hash
            print(f"   🔒 Volumes locked, hash={pipeline_hash}")
            return pipeline_hash
        
        def validate_and_heal(self, detections: list, remainder: dict, expected_hash: str,
                               img_w: int, img_h: int, depth_stats: dict, anchor_present: bool):
            """Phase 8: Self-heal on hash mismatch (no crash)."""
            current_hash = self.compute_pipeline_hash(detections, remainder)
            if current_hash != expected_hash:
                print("   ⚠️ Pipeline drift detected, auto-healing...")
                detections, remainder = self.recompute_full_pipeline(
                    detections, img_w, img_h, depth_stats, anchor_present
                )
                self.finalize_volumes(detections, remainder)
            return detections, remainder
        
        def recompute_full_pipeline(self, detections: list, img_w: int, img_h: int, 
                                     depth_stats: dict = None, anchor_present: bool = False):
            """Phase 7: Full recompute: canon → cluster → union → remainder."""
            print("   🔄 Full recompute: canonical → cluster → union → remainder")
            
            # 1. Re-lookup volumes from base
            for det in detections:
                if det.get("needs_volume_recompute"):
                    det["base_volume_yards"] = self.get_canonical_volume(
                        det.get("canonical_label", ""), det.get("size_class", "medium")
                    )
                    det["volume_yards"] = det["base_volume_yards"]
            
            # 2. DBSCAN + packing
            detections = self.calculate_cluster_volumes_v33(detections, img_w, img_h)
            
            # 3. Union coverage (junk only)
            junk_items = [d for d in detections if d.get("is_junk", True) and not d.get("is_background")]
            coverage = self.calculate_union_coverage(junk_items, img_w, img_h)
            residual = max(0, 1.0 - coverage)
            
            # 4. Mode-aware remainder
            mode = self.detect_scene_mode(detections, depth_stats, coverage)
            total_item_vol = sum(
                d.get("cluster_volume", 0) or d.get("volume_yards", 0.75)
                for d in detections if not d.get("in_cluster")
            )
            
            if self.should_activate_remainder(mode, residual, detections, anchor_present, depth_stats):
                remainder = self.estimate_pile_remainder_v31(detections, img_w, img_h, total_item_vol, depth_stats)
            else:
                remainder = {"remainder_yards": 0, "activated": False, "residual_pct": residual}
            
            # 5. Clear flags
            for det in detections:
                det["needs_volume_recompute"] = False
            
            return detections, remainder
        
        def calculate_cluster_volumes_v33(self, detections: list, img_w: int, img_h: int) -> list:
            """Phase 3-4: Cluster with base_volume + diameter guard."""
            detections = self.spatial_cluster_detections(detections, img_w, img_h)
            
            clusters = {}
            for det in detections:
                key = (det.get("canonical_label"), det.get("spatial_cluster_id", 0))
                clusters.setdefault(key, []).append(det)
            
            for (label, cluster_id), items in clusters.items():
                n = len(items)
                # Use base_volume_yards for cluster math
                sum_base = sum(d.get("base_volume_yards", d.get("volume_yards", 0.75)) for d in items)
                
                group = LABEL_TO_PACKING_GROUP.get(label, "rigid")
                packing = PACKING_GROUPS.get(group, 1.0)
                
                # Stack-type override
                if label and (label.endswith("_stack") or any(d.get("pile_type") == "stack" for d in items)):
                    packing *= STACK_LABEL_BONUS
                
                # Diameter guard
                override = self.validate_cluster_diameter(items, img_w, img_h)
                if override is not None:
                    packing = override
                
                # Only apply packing to 2+ items
                if n == 1:
                    packing = 1.0
                
                cluster_vol = round(sum_base * packing, 2)
                
                items[0]["cluster_volume"] = cluster_vol
                items[0]["cluster_size"] = n
                items[0]["packing_factor"] = packing
                
                for item in items[1:]:
                    item["in_cluster"] = f"{label}_{cluster_id}"
                    item["volume_yards"] = 0  # For summation
                    # base_volume_yards preserved
                
                for item in items:
                    item["volume_stage"] = VOLUME_STAGES["clustered"]
                    item["volume_stage_name"] = "clustered"
                
                if n > 1:
                    print(f"   📦 {label}[{cluster_id}]: {n}× base={sum_base:.2f} × pack({packing:.2f}) = {cluster_vol:.2f} yd³")
            
            return detections
        
        def detect_scene_type(self, detections: list) -> str:
            """FIX 2: Detect if scene is outdoor/construction or indoor/residential."""
            outdoor_count = 0
            indoor_count = 0
            
            for det in detections:
                label = det.get("label", "").lower()
                for indicator in OUTDOOR_SCENE_INDICATORS:
                    if indicator in label:
                        outdoor_count += 1
                        break
                for indoor_cat in INDOOR_ONLY_CATEGORIES:
                    if indoor_cat in label:
                        indoor_count += 1
                        break
            
            if outdoor_count >= 2 or (outdoor_count > 0 and indoor_count == 0):
                return "outdoor"
            elif indoor_count >= 2:
                return "indoor"
            return "mixed"
        
        def should_suppress_indoor_category(self, label: str, confidence: float, bbox: list, image_area: float, scene_type: str) -> bool:
            """FIX 2: Determine if indoor category should be suppressed in outdoor scene."""
            if scene_type != "outdoor":
                return False
            
            label_lower = label.lower()
            is_indoor_category = any(cat in label_lower for cat in INDOOR_ONLY_CATEGORIES)
            
            if not is_indoor_category:
                return False
            
            # Calculate bbox area ratio
            if bbox and len(bbox) >= 4 and image_area > 0:
                bbox_area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
                bbox_ratio = bbox_area / image_area
                
                # Allow if large enough and high confidence
                if bbox_ratio >= INDOOR_CATEGORY_MIN_BBOX_RATIO and confidence >= INDOOR_CATEGORY_MIN_CONFIDENCE:
                    return False
            
            print(f"   ⛔ Suppressing indoor category in outdoor scene: {label}")
            return True
        
        def merge_detections(self, florence_dets: list, gdino_dets: list) -> list:
            """Merge Florence-2 and GroundingDINO detections, prioritizing open-vocab labels."""
            merged = []
            used_gdino_indices = set()
            
            # FIX 1: Pre-filter invalid labels from both detection lists
            florence_dets = [d for d in florence_dets if self.is_valid_label(d.get("label", ""))]
            gdino_dets = [d for d in gdino_dets if self.is_valid_label(d.get("label", ""))]
            print(f"   After label filter: Florence={len(florence_dets)}, DINO={len(gdino_dets)}")
            
            for f_det in florence_dets:
                f_bbox = f_det.get("bbox", [0, 0, 0, 0])
                f_label = f_det["label"].lower()
                best_match = None
                best_iou = 0.0
                
                # Find overlapping GroundingDINO detection
                for i, g_det in enumerate(gdino_dets):
                    if i in used_gdino_indices:
                        continue
                    g_bbox = g_det.get("bbox", [0, 0, 0, 0])
                    iou = self._calculate_iou(f_bbox, g_bbox)
                    
                    if iou > 0.5 and iou > best_iou:
                        best_match = (i, g_det)
                        best_iou = iou
                
                if best_match:
                    i, g_det = best_match
                    used_gdino_indices.add(i)
                    g_label = g_det["label"].lower()
                    
                    # Priority: use open-vocab label if it's more specific
                    if g_label in OPEN_VOCAB_PRIORITY_LABELS or f_label in AMBIGUOUS_LABELS:
                        merged.append({
                            "label": g_det["label"],
                            "bbox": g_det["bbox"],
                            "confidence": g_det["confidence"],
                            "source": "grounding_dino",
                            "original_florence_label": f_det["label"]
                        })
                    else:
                        # Keep Florence label but note the match
                        merged.append({
                            **f_det,
                            "source": "florence",
                            "gdino_agreement": g_label
                        })
                else:
                    # No match - keep Florence detection
                    merged.append({**f_det, "source": "florence"})
            
            # Add unmatched GroundingDINO detections (new discoveries)
            for i, g_det in enumerate(gdino_dets):
                if i not in used_gdino_indices:
                    merged.append({
                        **g_det,
                        "source": "grounding_dino_new"
                    })
                    print(f"   🆕 GroundingDINO discovered: {g_det['label']}")
            
            return merged
        
        def _calculate_iou(self, box1: list, box2: list) -> float:
            """Calculate Intersection over Union for two bounding boxes."""
            x1 = max(box1[0], box2[0])
            y1 = max(box1[1], box2[1])
            x2 = min(box1[2], box2[2])
            y2 = min(box1[3], box2[3])
            
            if x2 <= x1 or y2 <= y1:
                return 0.0
            
            intersection = (x2 - x1) * (y2 - y1)
            area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
            area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
            union = area1 + area2 - intersection
            
            return intersection / union if union > 0 else 0.0
        
        def estimate_residual_volume(self, detections: list, image_width: int, image_height: int, 
                                      item_coverage_ratio: float, depth_stats: dict = None) -> dict:
            """FIX 4: Estimate residual pile volume when item coverage is low."""
            image_area = image_width * image_height
            
            # Calculate total bbox coverage
            total_bbox_area = 0
            for det in detections:
                bbox = det.get("bbox", [0, 0, 0, 0])
                if bbox and len(bbox) >= 4:
                    bbox_area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
                    total_bbox_area += bbox_area
            
            detected_coverage = total_bbox_area / image_area if image_area > 0 else 0
            residual_coverage = max(0, item_coverage_ratio - detected_coverage)
            
            # Estimate pile footprint (assume pile fills ~60% of unexplained area)
            estimated_footprint_sqft = (residual_coverage * 0.6) * 100  # Rough conversion
            
            # Estimate height from depth stats or use default
            estimated_height_ft = 3.0  # Default 3 feet
            if depth_stats:
                # Use depth variance to estimate pile height
                depth_range = depth_stats.get("max", 1.0) - depth_stats.get("min", 0.0)
                if depth_range > 0.3:
                    estimated_height_ft = min(depth_range * 8, 6.0)  # Scale and cap at 6ft
            
            # Calculate residual volume in cubic yards (27 cubic feet per yard)
            residual_volume_cuft = estimated_footprint_sqft * estimated_height_ft
            residual_volume_yards = residual_volume_cuft / 27
            
            print(f"   📊 Residual Estimator: coverage={residual_coverage:.1%}, footprint={estimated_footprint_sqft:.0f}sqft, height={estimated_height_ft:.1f}ft → {residual_volume_yards:.1f} yd³")
            
            return {
                "residual_volume_yards": round(residual_volume_yards, 2),
                "detected_coverage": detected_coverage,
                "residual_coverage": residual_coverage,
                "estimated_footprint_sqft": estimated_footprint_sqft,
                "estimated_height_ft": estimated_height_ft
            }
        
        def reconcile_volumes(self, catalog_volume: float, residual_estimate: dict) -> float:
            """FIX 4: Reconcile catalog sum with residual estimate."""
            residual_vol = residual_estimate.get("residual_volume_yards", 0)
            
            if residual_vol > catalog_volume * 0.5:  # Residual is significant
                # Use weighted blend: 60% max, 40% catalog
                final = 0.6 * max(catalog_volume, residual_vol) + 0.4 * catalog_volume
                print(f"   📊 Volume reconciled: catalog={catalog_volume:.1f}, residual={residual_vol:.1f} → final={final:.1f}")
                return round(final, 2)
            
            return catalog_volume
        
        def _parse_florence_output(self, raw_output) -> dict:
            """Parse Florence-2 output with anchor validation."""
            result = {"detections": [], "anchor_found": False, "anchor_scale_inches": None, "anchor_trust": None, "validated_anchors": []}
            
            try:
                if isinstance(raw_output, dict) and 'text' in raw_output:
                    text_str = raw_output['text']
                    print(f"🔬 Florence text field: {text_str[:200]}..." if len(text_str) > 200 else f"🔬 Florence text field: {text_str}")
                    
                    parsed = ast.literal_eval(text_str)
                    od_data = parsed.get('<OD>', {})
                    
                    if 'bboxes' in od_data and 'labels' in od_data:
                        bboxes = od_data['bboxes']
                        labels = od_data['labels']
                        
                        for i, bbox in enumerate(bboxes):
                            label = labels[i] if i < len(labels) else "unknown"
                            detection = {"label": label, "bbox": bbox, "type": "item"}
                            
                            # Use anchor validation with trust tiers
                            anchor_info = self.validate_anchor(label, bbox)
                            if anchor_info:
                                detection["type"] = "anchor"
                                detection["anchor_info"] = anchor_info
                                result["validated_anchors"].append(anchor_info)
                                
                                # Only set anchor_found if aspect is valid
                                if anchor_info["aspect_valid"]:
                                    result["anchor_found"] = True
                                    result["anchor_scale_inches"] = anchor_info["size_inches"]
                                    result["anchor_trust"] = anchor_info["trust"]
                            
                            result["detections"].append(detection)
                else:
                    print(f"⚠️ Unexpected Florence output format: {type(raw_output)}")
                    
            except Exception as e:
                print(f"❌ Florence parsing error: {e}")
                import traceback
                traceback.print_exc()
            
            print(f"📦 Parsed {len(result['detections'])} detections, {len(result['validated_anchors'])} anchors validated")
            return result
        
        # ===== PHASE 3: DETECTION + DEPTH =====
        
        def attach_depth_to_detections(self, detections: list, depth_map) -> list:
            """Add depth value to each detection from depth map."""
            import numpy as np
            
            if depth_map is None:
                return detections
            
            h, w = depth_map.shape[:2]
            
            for det in detections:
                bbox = det.get("bbox", [])
                if len(bbox) == 4:
                    x1, y1, x2, y2 = [int(c) for c in bbox]
                    cx = (x1 + x2) // 2
                    cy = (y1 + y2) // 2
                    
                    # Clamp to image bounds
                    cx = min(max(cx, 0), w - 1)
                    cy = min(max(cy, 0), h - 1)
                    
                    det["depth_m"] = float(depth_map[cy, cx])
            
            return detections
        
        # ===== PHASE 4: DEPTH-CORRECTED SIZING =====
        
        def calculate_real_dimensions(self, det: dict, base_px_per_inch: float,
                                       reference_depth: float, depth_map=None) -> dict:
            """Convert bbox pixels to inches with parallax correction."""
            bbox = det.get("bbox", [0, 0, 0, 0])
            item_depth = det.get("depth_m", reference_depth)
            
            # Safety clamps
            if reference_depth <= 0.1:
                reference_depth = 1.0
            if item_depth <= 0.1:
                item_depth = reference_depth
            
            # Parallax correction: closer items have more px/inch
            depth_ratio = item_depth / reference_depth
            
            # Clamp correction ratio to avoid extreme values
            depth_ratio = max(0.25, min(depth_ratio, 4.0))
            
            corrected_px_per_inch = base_px_per_inch / depth_ratio
            
            width_px = bbox[2] - bbox[0]
            height_px = bbox[3] - bbox[1]
            
            width_in = width_px / corrected_px_per_inch if corrected_px_per_inch > 0 else 0
            height_in = height_px / corrected_px_per_inch if corrected_px_per_inch > 0 else 0
            
            # Sanity check: if dimensions are unreasonable, fallback
            if width_in > 200 or height_in > 200 or width_in < 1 or height_in < 1:
                # Fallback to uncorrected
                width_in = width_px / base_px_per_inch if base_px_per_inch > 0 else 0
                height_in = height_px / base_px_per_inch if base_px_per_inch > 0 else 0
            
            return {
                "width_in": round(width_in, 1),
                "height_in": round(height_in, 1),
                "depth_m": round(item_depth, 2),
                "px_per_inch_used": round(corrected_px_per_inch, 2),
                "parallax_corrected": abs(depth_ratio - 1.0) > 0.1,
            }
        
        # ===== PHASE 5: DIMENSION-BASED CLASSIFICATION =====
        
        # Size thresholds in inches (width-based)
        SIZE_THRESHOLDS = {
            "mattress": {"king": 76, "queen": 60, "full": 54, "twin": 38},
            "bed": {"king": 76, "queen": 60, "full": 54, "twin": 38},
            "couch": {"large": 84, "medium": 72, "small": 60},
            "sofa": {"large": 84, "medium": 72, "small": 60},
            "dresser": {"large": 60, "medium": 48, "small": 36},
            "table": {"large": 72, "medium": 48, "small": 30},
            "desk": {"large": 60, "medium": 48, "small": 36},
            "chair": {"large": 36, "medium": 24, "small": 18},
            "box": {"large": 24, "medium": 18, "small": 12},
            "bag": {"large": 36, "medium": 24, "small": 12},
            "refrigerator": {"large": 36, "medium": 30, "small": 24},
            "washer": {"large": 30, "medium": 27, "small": 24},
            "dryer": {"large": 30, "medium": 27, "small": 24},
        }
        
        def classify_size_by_dimensions(self, label: str, width_in: float) -> str:
            """Classify item size using measured width in inches."""
            label_lower = label.lower()
            
            for item_type, thresholds in self.SIZE_THRESHOLDS.items():
                if item_type in label_lower:
                    for size_name, min_width in thresholds.items():
                        if width_in >= min_width:
                            return size_name
                    return "small"
            
            # Unknown item: generic classification
            if width_in > 60:
                return "large"
            elif width_in > 30:
                return "medium"
            return "small"
        
        # ===== PHASE 7: UNCERTAINTY CALCULATION =====
        
        def calculate_uncertainty(self, context: dict) -> dict:
            """Calculate price band uncertainty from all sources."""
            uncertainty = 0.0
            factors = []
            
            # Scale source uncertainty
            scale_source = context.get("scale_source", "none")
            if scale_source == "metric_depth":
                base_unc = context.get("intrinsics_uncertainty", 0.10)
                uncertainty += base_unc
                factors.append(f"metric +{base_unc*100:.0f}%")
            elif scale_source == "anchor":
                trust = context.get("anchor_trust", "LOW")
                anchor_unc = {"HIGH": 0.08, "MEDIUM": 0.15, "LOW": 0.25}.get(trust, 0.20)
                uncertainty += anchor_unc
                factors.append(f"anchor ({trust}) +{anchor_unc*100:.0f}%")
            else:
                uncertainty += 0.40
                factors.append("no scale +40%")
            
            # Detection quality penalty
            if context.get("detection_conflicts"):
                uncertainty += 0.10
                factors.append("conflicts +10%")
            
            # Multi-image bonus (reduces uncertainty)
            image_count = context.get("image_count", 1)
            if image_count > 1:
                reduction = min(0.05 * (image_count - 1), 0.10)
                uncertainty -= reduction
                factors.append(f"{image_count} images -{reduction*100:.0f}%")
            
            # Clamp to reasonable range
            uncertainty = max(0.08, min(uncertainty, 0.45))
            
            print(f"📊 Uncertainty: ±{uncertainty*100:.0f}% ({', '.join(factors)})")
            return {
                "uncertainty": round(uncertainty, 2),
                "factors": factors,
            }
        
        def run_depth_estimation(self, image_base64: str) -> dict:
            """Run Depth-Anything-V2. Output is {'color_depth': <url>, 'grey_depth': <url>}."""
            print("🔍 Running Depth-Anything-V2...")
            try:
                img_file = self._base64_to_file(image_base64)
                output = replicate.run(
                    DEPTH_MODEL,
                    input={"image": img_file, "model_size": "Large"}
                )
                print(f"✅ Depth-Anything-V2 raw output: {output}")
                
                # Extract the color_depth URL from the output dict
                # Output format: {'color_depth': <FileOutput or URL>, 'grey_depth': <FileOutput or URL>}
                depth_url = None
                if isinstance(output, dict):
                    color_depth = output.get('color_depth')
                    if color_depth is not None:
                        # Handle both string URLs and FileOutput objects
                        depth_url = str(color_depth)
                        print(f"🔬 Extracted depth URL: {depth_url[:80]}..." if len(depth_url) > 80 else f"🔬 Extracted depth URL: {depth_url}")
                else:
                    print(f"⚠️ Unexpected depth output format: {type(output)}")
                
                if depth_url:
                    return {"depth_map_url": depth_url, "success": True}
                else:
                    return {"depth_map_url": None, "success": False, "error": "Could not extract depth URL"}
                    
            except Exception as e:
                print(f"❌ Depth Error: {e}")
                import traceback
                traceback.print_exc()
                return {"success": False, "error": str(e)}
        
        def create_visual_bridge(self, original_b64: str, detections: dict, depth_url: str = None) -> str:
            print("🎨 Creating Visual Bridge...")
            img_bytes = base64.b64decode(original_b64)
            original = Image.open(io.BytesIO(img_bytes)).convert("RGB")
            annotated = original.copy()
            draw = ImageDraw.Draw(annotated)
            
            for det in detections.get("detections", []):
                bbox = det.get("bbox", [])
                if len(bbox) >= 4:
                    x1, y1, x2, y2 = bbox[:4]
                    color = "red" if det.get("type") == "anchor" else "blue"
                    draw.rectangle([x1, y1, x2, y2], outline=color, width=3)
                    draw.text((x1, y1 - 15), det.get("label", ""), fill=color)
            
            if depth_url:
                try:
                    resp = requests.get(depth_url, timeout=30)
                    depth_img = Image.open(io.BytesIO(resp.content)).convert("RGB").resize(annotated.size)
                    composite = Image.new("RGB", (annotated.width * 2, annotated.height))
                    composite.paste(annotated, (0, 0))
                    composite.paste(depth_img, (annotated.width, 0))
                    annotated = composite
                    print("✅ Side-by-side composite created")
                except Exception as e:
                    print(f"⚠️ Could not fetch depth map: {e}")
            
            buffer = io.BytesIO()
            annotated.save(buffer, format="JPEG", quality=85)
            return base64.b64encode(buffer.getvalue()).decode()
        
        def extract_depth_statistics(self, depth_url: str) -> dict:
            """Download depth map and extract statistical metrics."""
            try:
                import numpy as np
                response = requests.get(depth_url, timeout=10)
                depth_img = Image.open(io.BytesIO(response.content)).convert("L")
                depth_array = np.array(depth_img)
                
                stats = {
                    "mean": round(float(np.mean(depth_array)), 1),
                    "median": round(float(np.median(depth_array)), 1),
                    "std": round(float(np.std(depth_array)), 1),
                    "min": int(np.min(depth_array)),
                    "max": int(np.max(depth_array)),
                    "range": int(np.max(depth_array) - np.min(depth_array))
                }
                print(f"📊 Depth Stats: mean={stats['mean']}, std={stats['std']}, range={stats['range']}")
                return stats
            except Exception as e:
                print(f"⚠️ Depth stats error: {e}")
                return None
        
        def get_pile_bbox(self, detections: list) -> list:
            """Calculate bounding box encompassing all detections."""
            valid_dets = [d for d in detections if "bbox" in d and len(d["bbox"]) == 4]
            if not valid_dets:
                return None
            x1 = min(d["bbox"][0] for d in valid_dets)
            y1 = min(d["bbox"][1] for d in valid_dets)
            x2 = max(d["bbox"][2] for d in valid_dets)
            y2 = max(d["bbox"][3] for d in valid_dets)
            return [x1, y1, x2, y2]
        
        def analyze_image(self, image_base64: str, image_bytes: bytes = None) -> dict:
            """
            Main entry point for image analysis.
            Routes to camera-aware or legacy path based on feature flag.
            """
            import time
            
            # Route to camera-aware path if enabled and image_bytes provided
            if CAMERA_AWARE_ENABLED and image_bytes:
                print("🚀 Starting Camera-Aware Vision Pipeline...")
                try:
                    return self.analyze_image_camera_aware(image_base64, image_bytes)
                except Exception as e:
                    print(f"⚠️ Camera-aware failed, falling back to legacy: {e}")
                    # Fall through to legacy
            
            # Legacy path
            print("🚀 Starting Vision Pipeline (Legacy + GroundingDINO)...")
            
            # Run Florence detection
            florence_result = self.run_florence_detection(image_base64)
            florence_dets = florence_result.get("detections", [])
            print(f"   Florence-2: {len(florence_dets)} items")
            
            # Rate limit delay before GroundingDINO
            import time
            time.sleep(12)
            
            # Run GroundingDINO with tiered prompting
            gdino_dets = self.run_tiered_detection(image_base64)
            print(f"   GroundingDINO: {len(gdino_dets)} items")
            
            # Merge detections, prioritizing open-vocab labels
            merged_detections = self.merge_detections(florence_dets, gdino_dets)
            print(f"   Merged: {len(merged_detections)} unique items")
            
            # Rebuild detections dict with merged results
            detections = {
                **florence_result,
                "detections": merged_detections,
                "florence_count": len(florence_dets),
                "gdino_count": len(gdino_dets)
            }
            
            depth_result = self.run_depth_estimation(image_base64)
            depth_url = depth_result.get("depth_map_url") if depth_result.get("success") else None
            
            # Phase 5: Extract depth statistics
            depth_stats = None
            if depth_url:
                depth_stats = self.extract_depth_statistics(depth_url)
            
            visual_bridge = self.create_visual_bridge(image_base64, detections, depth_url)
            print(f"✅ Vision Complete: {len(merged_detections)} objects (F:{len(florence_dets)} + G:{len(gdino_dets)})")
            return {
                "detections": detections,
                "visual_bridge_image": visual_bridge,
                "depth_map_url": depth_url,
                "depth_available": depth_result.get("success", False),
                "depth_stats": depth_stats
            }
        
        def analyze_image_camera_aware(self, image_b64: str, image_bytes: bytes) -> dict:
            """Camera-aware analysis with metric depth (Phases 1-5)."""
            import time
            
            # Get image resolution
            img = Image.open(io.BytesIO(image_bytes))
            resolution = (img.width, img.height)
            print(f"📷 Image resolution: {resolution[0]}x{resolution[1]}")
            
            # Phase 1: Get camera intrinsics
            intrinsics = self.get_camera_intrinsics(image_bytes, resolution)
            
            # Run Florence detection
            florence_result = self.run_florence_detection(image_b64)
            florence_dets = florence_result.get("detections", [])
            print(f"   Florence-2: {len(florence_dets)} items")
            
            # Rate limit delay before GroundingDINO
            import time
            time.sleep(12)
            
            # Run GroundingDINO with tiered prompting
            gdino_dets = self.run_tiered_detection(image_b64)
            print(f"   GroundingDINO: {len(gdino_dets)} items")
            
            # Merge detections, prioritizing open-vocab labels
            merged_detections = self.merge_detections(florence_dets, gdino_dets)
            print(f"   Merged: {len(merged_detections)} unique items")
            
            # Rebuild detections dict with merged results
            detections = {
                **florence_result,
                "detections": merged_detections,
                "florence_count": len(florence_dets),
                "gdino_count": len(gdino_dets)
            }
            
            # Phase 2: Get scale (metric or anchor fallback)
            scale = self.get_scale(image_bytes, image_b64, intrinsics, 
                                   detections.get("detections", []))
            
            # Phase 3: Attach depth to detections if available
            depth_map = scale.get("depth_map")
            if depth_map is not None:
                detections["detections"] = self.attach_depth_to_detections(
                    detections["detections"], depth_map)
            
            # Phase 4-5: Calculate real dimensions and classify for non-anchors
            reference_depth = scale.get("reference_depth_m", 2.0)
            base_px_per_inch = scale.get("px_per_inch", 3.0)
            
            for det in detections.get("detections", []):
                if det.get("type") != "anchor" and base_px_per_inch > 0:
                    dims = self.calculate_real_dimensions(det, base_px_per_inch, reference_depth)
                    det.update(dims)
                    det["size_class"] = self.classify_size_by_dimensions(
                        det["label"], det.get("width_in", 0))
            
            # Create visual bridge (use depth URL from Depth-Anything for visualization)
            depth_result = self.run_depth_estimation(image_b64)
            depth_url = depth_result.get("depth_map_url") if depth_result.get("success") else None
            visual_bridge = self.create_visual_bridge(image_b64, detections, depth_url)
            
            print(f"✅ Camera-Aware Complete: {len(detections.get('detections', []))} objects, scale={scale.get('scale_source')}")
            return {
                "detections": detections,
                "visual_bridge_image": visual_bridge,
                "depth_map_url": depth_url,
                "depth_available": scale.get("success", False),
                "scale": scale,
                "intrinsics": intrinsics,
            }
        
        def fuse_detection_results(self, all_results: list) -> dict:
            """
            Merge detections from multiple images.
            Deduplicates by normalized label, keeping the largest bbox.
            """
            fused = {"detections": [], "anchor_found": False, "anchor_scale_inches": None}
            seen_labels = {}  # normalized_label -> {"det": detection, "area": float}
            
            for result in all_results:
                dets = result.get("detections", {})
                
                # Aggregate anchor across all images (first anchor wins)
                if dets.get("anchor_found") and not fused["anchor_found"]:
                    fused["anchor_found"] = True
                    fused["anchor_scale_inches"] = dets.get("anchor_scale_inches")
                
                for det in dets.get("detections", []):
                    norm_label = self._normalize_label(det["label"])
                    bbox = det.get("bbox", [0, 0, 0, 0])
                    area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1]) if len(bbox) == 4 else 0
                    
                    if norm_label not in seen_labels or area > seen_labels[norm_label]["area"]:
                        seen_labels[norm_label] = {"det": det, "area": area}
            
            fused["detections"] = [v["det"] for v in seen_labels.values()]
            print(f"🔗 Fusion: {len(seen_labels)} unique labels from {len(all_results)} images")
            return fused
        
        def _normalize_label(self, label: str) -> str:
            """Normalize label for deduplication (lowercase, strip, remove plural 's')."""
            label = label.lower().strip()
            if label.endswith("s") and len(label) > 3:
                label = label[:-1]
            return label

    # Singleton
    _vision_worker = None
    def get_vision_worker():
        global _vision_worker
        if _vision_worker is None:
            _vision_worker = VisionWorker()
        return _vision_worker
    
    # Test initialization
    _test_worker = get_vision_worker()
    VISION_ENABLED = True
    VISION_ERROR = None
    print("✅ Vision Pipeline ENABLED (Replicate SDK)")

except Exception as e:
    VISION_ENABLED = False
    VISION_ERROR = f"{type(e).__name__}: {e}"
    print(f"❌ Vision Pipeline DISABLED: {VISION_ERROR}")
    
    def get_vision_worker():
        raise RuntimeError(f"Vision Pipeline not available: {VISION_ERROR}")

# ==================== END VISION WORKER ====================

# Heavy Material Surcharge Tiers (DISABLED - user inputs on booking-details page)
HEAVY_SURCHARGES = {
    "none": 0,
    "some": 0,
    "mixed": 0,
    "mostly": 0,
    "all": 0
}

class PricingEngine:
    def __init__(self):
        # 1. Initialize Google Client (Sync client, wrapped in async later)
        self.google_client = genai.Client(api_key=os.environ.get("GOOGLE_API_KEY"))
        
        # 2. Initialize OpenAI Client (Async)
        self.openai_client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

        # 3. Initialize Redis (for Rate Limiting)
        try:
            self.redis_client = redis.from_url(os.environ.get('REDIS_URL'))
            # Test connection lightly
            self.redis_client.ping()
            print("✅ REDIS CONNECTED")
        except Exception as e:
            print(f"⚠️ REDIS CONNECTION FAILED: {e}")
            self.redis_client = None

    def check_rate_limit(self, user_ip):
        """Enforce 5 requests per hour limit using Redis."""
        if not self.redis_client:
            return True # Fail open

        key = f"rate_limit:{user_ip}"
        try:
            # Atomic increment
            request_count = self.redis_client.incr(key)
            
            # If this is the first request, set expiry to 1 hour (3600 seconds)
            if request_count == 1:
                self.redis_client.expire(key, 3600)
                
            print(f"🛡️ RATE LIMIT: IP {user_ip} is at {request_count}/50 requests.")

            if request_count > 50:
                # Temporarily raised to 50 for testing (was 5)
                return False
            
            return True
        except Exception as e:
            print(f"⚠️ RATE LIMIT ERROR: {e}")
            return True

    def _get_system_prompt(self):
        return """
        You are a Veteran Junk Removal Load Master. Output JSON ONLY.
        Your Goal: Calculate the *Billable Truck Space* (Total Cubic Feet) required for this job.

        ### PHASE 1: ANCHOR LOCK (CRITICAL)
        - **Primary Anchor:** The Mattress (Standard 80" tall) or The Pallets (Standard 40" x 48").
        - **Secondary Anchor:** Wheelie Bin (42" tall).
        - **FORBIDDEN:** Do NOT use cars, houses, garage doors, or windows in the background. They are distant and will distort scale.
        - **Fallback:** If no standard scale exists, assume the tallest item in the pile is 6ft (approx human height).

        ### PHASE 2: CALCULATION STRATEGY (The "Sum of Parts" Protocol)
        Do NOT draw a giant bounding box around a scattered pile (this captures too much air).
        Instead, calculate by **SUMMATION**:
        1. **Identify the "Big 3":** Find the 3 largest distinct items (e.g., Mattress, Sofa, Shelf).
        2. **Calculate their tight volume:** (L x W x H) for each.
        3. **Add the "Scatter":** Estimate the volume of the remaining loose bags/boxes and add it to the total.
        4. **Apply Physics:**
           - **Compressible items (Bags):** Reduce volume by 30%.
           - **Irregular items (Bikes/Brush):** Add 15% "Void Space" for stacking inefficiency.

        ### PHASE 3: REALITY CHECK
        - **Heuristic:** Most residential driveway piles are between 3 and 6 cubic yards.
        - If your calculation exceeds 10 yards, re-evaluate: Did you include the driveway width in the pile? Did you use a background house for scale?

        ### PHASE 4: FINAL OUTPUT
        Output the dimensions of the final theoretical stack in DECIMAL FEET.

        ### OUTPUT JSON:
        {
          "packed_dimensions": {
              "l": 0.0,
              "w": 0.0,
              "h": 0.0
          },
          "confidence_score": 1.0, 
          "risk_factor": "String",
          "density": 1.0,
          "debug_items": "String (List the 'Big 3' items used for scale)",
          "anchor_used": "String"
        }
        """
    
    def _get_vision_enhanced_prompt(self):
        """Gemini auditor prompt - validates labels only, cannot override measured dimensions."""
        return """
        You are a FORENSIC AUDITOR for junk removal detection. Your role is LIMITED:

        **IMAGE LAYOUT:**
        - LEFT SIDE: Annotated view with bounding boxes (RED=anchors, BLUE=items)
        - RIGHT SIDE: Depth heatmap (white=near, black=far)

        **ALLOWED ACTIONS:**
        
        1. **CORRECT MISLABELED ITEMS:**
           - "box" should be "microwave" or "TV"
           - "chair" should be "office chair" or "stool"
           
        2. **ADD MISSED ITEMS:**
           - Items hidden behind others
           - Items at image edges
           - Small items not detected

        **NOT ALLOWED (sensors measured these):**
        - DO NOT classify item sizes (small/medium/large)
        - DO NOT estimate dimensions
        - DO NOT override depth measurements
        - DO NOT estimate volumes

        ### OUTPUT JSON (only these fields):
        {
          "label_corrections": [{"original": "box", "corrected": "microwave"}],
          "missed_items": ["lamp behind dresser", "bags in corner"],
          "visibility_notes": "Brief observation about image quality"
        }
        """

    async def ask_gemini(self, images):
        try:
            # Gemini 3 Pro Preview
            # Wrap synchronous call in thread for async compatibility
            prompt = self._get_system_prompt()
            
            def _call():
                return self.google_client.models.generate_content(
                    model='gemini-3-pro-preview',
                    contents=[prompt, *images],
                    config=types.GenerateContentConfig(
                        temperature=0.0,
                        response_mime_type='application/json'
                    )
                )

            response = await asyncio.to_thread(_call)
            
            # Safety check: handle None or empty response
            response_text = response.text if response and response.text else None
            if not response_text:
                print("⚠️ Gemini returned empty/None response")
                return None
            
            return json.loads(response_text)
        except Exception as e:
            print(f"❌ GEMINI ERROR: {e}")
            return None

    # NOTE: GPT-4o removed - using only GPT-5.2 for auditing
    
    async def classify_with_gemma(self, image_b64: str, items: list) -> list:
        """Use GPT-5-mini via Replicate to classify ambiguous items into pricing categories."""
        try:
            items_json = json.dumps([{"label": i.get("label", "unknown"), "bbox": i.get("bbox", [])} for i in items])
            
            prompt = f"""Analyze these junk removal items detected in the image: {items_json}

For EACH item, return:
- item: original detected label
- is_junk: true/false (false if this is a background object like parked cars, buildings, people)
- corrected_label: what this item actually is (if different from detection, e.g., "car" might be "CRT TV")
- category: one of the categories listed below
- size: xs/small/medium/large/xl (estimate physical size)
- add_on_flags: ["mounted", "disassembly", "heavy_material"] if applicable (empty array if none)
- confidence: 0.0-1.0

Categories:
- furniture: couches, chairs, tables, bookcases, shelves (1.0×)
- mattress: beds, mattresses, box springs (1.1×)
- appliance: washer, dryer, stove, dishwasher (1.2×)
- appliance_freon: fridge, freezer, AC unit (1.3×)
- ewaste_crt: CRT TVs (boxy, deep, heavy) (1.2×)
- ewaste_flat_tv: flat screen TVs (1.15×)
- ewaste_other: monitors, computers, printers (1.15×)
- yard_green: bagged leaves, grass clippings (0.9×)
- yard_branches: brush, branches, lumber scraps (1.0×)
- demo_light: wood, drywall, carpet (1.25×)
- demo_heavy: concrete, tile, dirt, rocks (1.6×)
- tires: tires, tire stacks (1.2×)
- scrap_metal: scrap metal, metal parts (1.2×)
- pallets: wood pallets (count them individually!) (1.25×)
- boxes_bags: cardboard boxes, trash bags (1.0×)
- bulky_outdoor: hot tub, shed, playset, trampoline (1.4×)
- misc: anything else (1.0×)

Special instructions:
1. For background objects (parked cars, trucks, buildings, fences, industrial spools), set is_junk: false
2. For TVs: distinguish CRT (boxy, deep) from flat screens - different categories!
3. For piles: estimate what material it is (wood, concrete, mixed)
4. Count pallets if stacked together (put count in corrected_label: "4 pallets")
5. If unsure, mark is_junk: false to be safe

Return JSON array ONLY. No explanation."""

            print(f"🤖 Calling GPT-5-mini via Replicate for {len(items)} items...")
            
            # Use GPT-5-mini via Replicate
            output = replicate.run(
                "openai/gpt-5-mini",
                input={
                    "prompt": prompt,
                    "image": f"data:image/jpeg;base64,{image_b64}",
                    "max_tokens": 1500,
                    "temperature": 0.2,
                }
            )
            
            # Handle streaming output from Replicate
            if hasattr(output, '__iter__') and not isinstance(output, str):
                result_text = "".join(output)
            else:
                result_text = str(output) if output else ""
            
            print(f"🤖 GPT-5-mini raw response length: {len(result_text)} chars")
            
            if not result_text:
                raise ValueError("Empty response from GPT-5-mini")
            
            # Clean up any markdown formatting
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0]
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0]
            
            result = json.loads(result_text.strip())
            
            # FIX 5: Validate response has expected number of items
            if isinstance(result, list):
                if len(result) < len(items):
                    print(f"   ⚠️ FIX 5: GPT-5-mini returned {len(result)}/{len(items)} items - filling missing with static mapping")
                    # Fill missing items with static fallback
                    result_labels = {r.get("item", "").lower() for r in result}
                    for item in items:
                        if item.get("label", "").lower() not in result_labels:
                            result.append({
                                "item": item.get("label", "unknown"),
                                "category": ITEM_TO_CATEGORY.get(item.get("label", "").lower(), "misc"),
                                "add_on_flags": [],
                                "confidence": 0.3,
                                "source": "fallback"
                            })
                            print(f"      Added fallback for missing: {item.get('label')}")
            
            print(f"🤖 GPT-5-mini classifications: {len(result)} items validated")
            return result
            
        except Exception as e:
            print(f"⚠️ GPT-5-mini classification failed: {e}, using static mapping")
            # Fallback to static mapping
            return [
                {"item": i.get("label", "unknown"), 
                 "category": ITEM_TO_CATEGORY.get(i.get("label", "").lower(), "furniture"),
                 "add_on_flags": [],
                 "confidence": 0.5}
                for i in items
            ]
    
    async def audit_with_gpt5(
        self, 
        visual_bridge_b64: str, 
        detections: list,
        measurements: dict,
        initial_classifications: list
    ) -> dict:
        """Use GPT-5.2 to audit detections, catch missed items, and validate classifications."""
        try:
            # Build structured input for GPT-5.2
            audit_input = {
                "detections": [
                    {"item_id": f"item_{i}", "label": d.get("label", "unknown"), "bbox": d.get("bbox", [])}
                    for i, d in enumerate(detections)
                ],
                "measurements": {
                    f"item_{i}": item.get("size_bucket", "unknown")
                    for i, item in enumerate(measurements.get("items", []))
                },
                "initial_classification": [
                    {"item_id": f"item_{i}", 
                     "category": cls.get("category", "furniture"),
                     "variant": cls.get("variant", "unknown"),
                     "add_on_flags": cls.get("add_on_flags", [])}
                    for i, cls in enumerate(initial_classifications)
                ]
            }
            
            print(f"🔍 Calling GPT-5.2 audit for {len(detections)} items...")
            
            response = await self.openai_client.chat.completions.create(
                model="gpt-5.2-2025-12-11",
                messages=[
                    {"role": "system", "content": GPT5_AUDIT_PROMPT},
                    {"role": "user", "content": [
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{visual_bridge_b64}"}},
                        {"type": "text", "text": f"Audit input:\n{json.dumps(audit_input, indent=2)}"}
                    ]}
                ],
                response_format={"type": "json_object"},
                max_completion_tokens=1500
            )
            
            raw_content = response.choices[0].message.content
            if not raw_content:
                print("⚠️ GPT-5.2 returned empty response")
                return self._default_audit_result()
            
            result = json.loads(raw_content)
            
            # Log audit results
            missed = result.get("missed_items", [])
            corrections = result.get("classification_corrections", [])
            addon_corrections = result.get("add_on_flag_corrections", [])
            scene_conf = result.get("scene_confidence", 0.8)
            
            print(f"🔍 GPT-5.2 Audit: {len(missed)} missed, {len(corrections)} corrections, {len(addon_corrections)} add-on flags, scene_conf={scene_conf:.2f}")
            
            return result
            
        except Exception as e:
            print(f"❌ GPT-5.2 Audit Error: {e}")
            return self._default_audit_result()
    
    def _default_audit_result(self) -> dict:
        """Return default audit result when GPT-5.2 fails."""
        return {
            "missed_items": [],
            "classification_corrections": [],
            "add_on_flag_corrections": [],
            "scene_confidence": 0.7,
            "uncertainty_band": {
                "risk_level": "medium",
                "drivers": ["DEPTH_UNRELIABLE"]
            }
        }
    
    def apply_audit_corrections(
        self,
        classifications: list,
        audit_result: dict
    ) -> tuple:
        """Apply GPT-5.2 audit corrections and calculate missed item volume."""
        
        # Track volume corrections for items where category changed significantly
        volume_corrections = {}  # item_idx -> new_volume
        
        # 1. Apply category corrections
        corrections = audit_result.get("classification_corrections", [])
        for corr in corrections:
            if corr.get("confidence", 0) >= 0.7:
                item_idx = int(corr.get("item_id", "item_0").replace("item_", ""))
                if 0 <= item_idx < len(classifications):
                    old_cat = classifications[item_idx].get("category", "unknown")
                    new_cat = corr.get("suggested_category", old_cat)
                    classifications[item_idx]["category"] = new_cat
                    print(f"🔄 Correction: item_{item_idx} {old_cat} → {new_cat}")
                    
                    # If category changed significantly, re-lookup volume
                    # This handles cases like "car" (0.05 yd³) being corrected to "ewaste_tv" (1.2 yd³)
                    if old_cat != new_cat:
                        new_vol = CATEGORY_DEFAULT_VOLUMES.get(new_cat, 0.5)
                        volume_corrections[item_idx] = new_vol
                        print(f"📏 Volume re-lookup: item_{item_idx} → {new_vol:.2f} yd³ ({new_cat} default)")
        
        # 2. Calculate missed item volumes with GPT-5.2 size buckets
        missed_vol = 0.0
        for item in audit_result.get("missed_items", []):
            if item.get("confidence", 0) >= 0.5:  # Include if moderately confident
                size_bucket = item.get("size_bucket", "unknown")
                base_vol = SIZE_BUCKET_VOLUMES.get(size_bucket, 0.5)
                count = item.get("count", 1)
                category = item.get("proposed_category", "misc")
                multiplier = GPT_CATEGORY_TO_MULTIPLIER.get(category, 1.0)
                
                item_vol = base_vol * count * multiplier
                missed_vol += item_vol
                print(f"🔍 Missed: {item.get('label', 'unknown')} ({size_bucket}×{count}) = {base_vol:.2f} × {multiplier} = {item_vol:.2f} yd³")
        
        # 3. Collect add-on flags
        add_on_flags = []
        for corr in audit_result.get("add_on_flag_corrections", []):
            if corr.get("should_be", False) and corr.get("confidence", 0) >= 0.7:
                flag = corr.get("add_on_flag")
                if flag and flag not in add_on_flags:
                    add_on_flags.append(flag)
                    print(f"➕ GPT-5.2 detected add-on: {flag}")
        
        return classifications, missed_vol, add_on_flags, volume_corrections
    
    async def ask_gemini_with_vision(self, visual_bridge_b64: str, detections: dict) -> dict:
        """
        Send annotated visual bridge image to Gemini 3 Pro for enhanced analysis.
        Uses vision-specific prompt that understands RED/BLUE boxes and depth heatmap.
        """
        try:
            # Build context from detections
            detection_context = ""
            if detections.get("anchor_found"):
                detection_context += f"ANCHOR DETECTED: {detections.get('anchor_scale_inches')} inches scale available.\n"
            detection_context += f"Items detected: {len(detections.get('detections', []))}\n"
            
            # Build Gemini-compatible prompt
            prompt = f"{self._get_vision_enhanced_prompt()}\n\nPRE-ANALYSIS CONTEXT:\n{detection_context}"
            
            # Decode base64 image for Gemini
            img_bytes = base64.b64decode(visual_bridge_b64)
            image_part = types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg")
            
            def _call():
                return self.google_client.models.generate_content(
                    model='gemini-3-pro-preview',
                    contents=[prompt, image_part],
                    config=types.GenerateContentConfig(
                        temperature=0.0,
                        response_mime_type='application/json'
                    )
                )

            response = await asyncio.to_thread(_call)
            
            # Safety check: handle None or empty response
            response_text = response.text if response and response.text else None
            if not response_text:
                print("⚠️ Gemini returned empty/None response")
                return None
            
            print(f"✅ Gemini Vision Response: {response_text[:200]}..." if len(response_text) > 200 else f"✅ Gemini Vision Response: {response_text}")
            return json.loads(response_text)
        except Exception as e:
            print(f"❌ GEMINI VISION ERROR: {e}")
            import traceback
            traceback.print_exc()
            return None

    def calculate_volume(self, json_data):
        if not json_data or 'packed_dimensions' not in json_data: 
            return 0.0
        d = json_data['packed_dimensions']
        return (d.get('l', 0) * d.get('w', 0) * d.get('h', 0)) / 27.0

    async def process_quote(self, images, base64_images, heavy_level='none'):
        print("🚀 STARTING GEMINI-ONLY QUOTE (GPT-4o removed)...")
        
        # Heavy Surcharge from user selection
        heavy_surcharge = HEAVY_SURCHARGES.get(heavy_level, 0)
        print(f"📦 Heavy Material Level: {heavy_level} -> +${heavy_surcharge}")
        
        # 1. Prepare Gemini Inputs
        gemini_inputs = []
        for img_bytes in images:
             gemini_inputs.append(types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg"))

        # 2. Gemini-only execution (GPT-4o removed)
        try:
            res_gemini = await self.ask_gemini(gemini_inputs)
        except Exception as e:
            print(f"❌ Gemini Exception: {e}")
            res_gemini = None

        # 3. Fail-Over Check
        if not res_gemini:
            return {"status": "SHADOW_MODE", "message": "Gemini Failed", "reason": "System Outage"}

        # 4. Confidence Gate (Gemini-only)
        conf_gemini = res_gemini.get('confidence_score', 0)
        
        if conf_gemini < 0.5:
             return {"status": "SHADOW_MODE", "message": "Image Unclear", "debug": f"Conf: {conf_gemini}"}

        # 5. Volume Calculation (Gemini-only)
        vol_gemini = self.calculate_volume(res_gemini)
        
        if vol_gemini <= 0:
            return {"status": "SHADOW_MODE", "message": "Could not calculate volume", "debug": "vol=0"}

        print(f"🧮 MATH: Gemini({vol_gemini:.2f} yd³)")

        final_vol = vol_gemini

        # 6. Pricing Math
        final_vol = round(final_vol, 1)
        base_price = max(95, final_vol * 35) # $35/yd, $95 min
        
        # Apply heavy surcharge
        total_base = base_price + heavy_surcharge
        min_price = max(95, round(total_base * 0.90))
        max_price = round(total_base * 1.10)
        
        # Pretty Rounding
        def round_pretty(p):
            if p > 100: return 5 * round(p / 5)
            return round(p)

        min_price = round_pretty(min_price)
        max_price = round_pretty(max_price)

        return {
            "status": "SUCCESS",
            "volume_yards": final_vol,
            "min_price": min_price,
            "max_price": max_price,
            "price": round(total_base, 2),
            "heavy_surcharge": heavy_surcharge,
            "debug": {
                "gemini_vol": vol_gemini,
                "confidence": conf_gemini,
                "gemini_raw": res_gemini,
                "heavy_level": heavy_level
            }
        }
    
    async def process_quote_with_vision(self, base64_images, heavy_level='none'):
        """
        Vision-only quote processing using Florence-2 + Depth-Anything-V2.
        Uses Replicate SDK for model inference.
        """
        print("🔬 STARTING VISION-ENHANCED ANALYSIS...")
        
        # Heavy Surcharge from user selection
        heavy_surcharge = HEAVY_SURCHARGES.get(heavy_level, 0)
        print(f"📦 Heavy Material Level: {heavy_level} -> +${heavy_surcharge}")
        
        try:
            # 1. Run Vision Pipeline on ALL images
            vision_worker = get_vision_worker()
            
            # Process ALL images through vision pipeline
            all_vision_results = []
            print(f"📸 Processing {len(base64_images)} image(s)...")
            
            for i, img_b64 in enumerate(base64_images):
                print(f"🔍 Analyzing image {i+1}/{len(base64_images)}...")
                try:
                    # Decode bytes for camera-aware path (EXIF extraction)
                    img_bytes = base64.b64decode(img_b64)
                    result = vision_worker.analyze_image(img_b64, img_bytes)
                    result["image_index"] = i
                    det_count = len(result.get("detections", {}).get("detections", []))
                    anchor = result.get("detections", {}).get("anchor_found", False)
                    depth = result.get("depth_available", False)
                    print(f"   ✅ Image {i+1}: {det_count} detections, anchor={anchor}, depth={depth}")
                    all_vision_results.append(result)
                except Exception as img_error:
                    print(f"   ⚠️ Image {i+1} failed: {img_error}")
            
            # Check for minimum success
            if not all_vision_results:
                raise ValueError("All image analyses failed")
            
            print(f"✅ Successfully analyzed {len(all_vision_results)}/{len(base64_images)} images")
            
            # Phase 2: Fuse detections from all images
            detections = vision_worker.fuse_detection_results(all_vision_results)
            
            # Phase 3: Filter out background objects (cars, trucks, buildings, etc.)
            raw_detection_count = len(detections.get("detections", []))
            filtered_detections = [
                d for d in detections.get("detections", [])
                if d.get("label", "").lower() not in BACKGROUND_LABELS
            ]
            detections["detections"] = filtered_detections
            filtered_count = raw_detection_count - len(filtered_detections)
            if filtered_count > 0:
                print(f"🚫 Filtered {filtered_count} background objects (cars, trucks, etc.)")
            
            # Phase 4: Calculate catalog-based volume
            catalog_volume = vision_worker.calculate_catalog_volume(detections.get("detections", []))
            
            # Phase 6: Calculate residual pile area (IoU subtraction)
            residual_pile = vision_worker.calculate_residual_pile_area(detections.get("detections", []))
            
            # Phase 7: Calculate uncertainty using new propagation model
            catalog_matched = sum(1 for item in catalog_volume.get("items", []) if item.get("matched"))
            catalog_total = catalog_volume.get("item_count", 1) or 1
            
            # Determine scale source from best anchor
            scale_source = "anchor" if detections.get("anchor_found") else "none"
            anchor_trust = detections.get("anchor_trust", "LOW")
            
            uncertainty_ctx = {
                "scale_source": scale_source,
                "anchor_trust": anchor_trust,
                "image_count": len(all_vision_results),
                "detection_conflicts": False,  # TODO: detect conflicts across images
            }
            
            # Use new uncertainty calculation
            uncertainty_result = vision_worker.calculate_uncertainty(uncertainty_ctx)
            
            # Also calculate old confidence for backward compatibility
            confidence_ctx = {
                "anchor_trust": anchor_trust,
                "depth_available": any(r.get("depth_available", False) for r in all_vision_results),
                "image_count": len(all_vision_results),
                "catalog_match_ratio": catalog_matched / catalog_total
            }
            confidence = vision_worker.calculate_pipeline_confidence(confidence_ctx)
            
            # Use visual bridge from image with anchor, or first image
            visual_bridge = None
            for result in all_vision_results:
                if result.get("detections", {}).get("anchor_found"):
                    visual_bridge = result.get("visual_bridge_image")
                    print(f"📍 Using visual bridge from image {result['image_index']+1} (has anchor)")
                    break
            if not visual_bridge:
                visual_bridge = all_vision_results[0].get("visual_bridge_image")
            
            print(f"👁️ Vision: Anchor={detections.get('anchor_found')}, Items={len(detections.get('detections', []))}")
            
            if not visual_bridge:
                raise ValueError("Vision pipeline failed to create visual bridge")
            
            # 2a. Classify ambiguous items with Gemma 3 27B
            gemma_categories = {}  # label -> category override
            gemma_add_ons = []     # add-on flags from Gemma
            gemini_skip_labels = set()  # v2.3: Labels marked as background by Gemini
            gemini_underdelivered = False  # v2.5: Track if Gemini returned fewer items than expected
            
            all_detections = detections.get("detections", [])
            ambiguous_items = [d for d in all_detections 
                               if d.get("label", "").lower() in AMBIGUOUS_LABELS 
                               or d.get("label", "").lower() not in ITEM_TO_CATEGORY]
            
            if ambiguous_items and visual_bridge:
                print(f"🔮 {len(ambiguous_items)} ambiguous items found, calling Gemini Vision...")
                classifications = await self.classify_with_gemma(visual_bridge, ambiguous_items)
                
                # v2.5: Detect if Gemini underdelivered (returned fewer than 50% of items)
                fallback_items = [c for c in classifications if c.get("source") == "fallback"]
                if len(fallback_items) >= len(ambiguous_items) * 0.5:
                    gemini_underdelivered = True
                    print(f"⚠️ v2.5: Gemini underdelivered ({len(fallback_items)}/{len(ambiguous_items)} fallback)")
                
                # Store Gemini classifications for volume calculation
                gemma_sizes = {}  # label -> size bucket
                for cls in classifications:
                    label = cls.get("item", "").lower()
                    
                    # Skip if Gemini says this isn't junk (background object)
                    if cls.get("is_junk") == False:
                        print(f"🚫 Gemini identified {label} as background object, skipping")
                        # v2.3: Mark label for skip (propagate to catalog_items later)
                        gemini_skip_labels.add(label)
                        continue
                    
                    # Store category
                    gemma_categories[label] = cls.get("category", "furniture")
                    
                    # Store size for volume lookup
                    if cls.get("size"):
                        gemma_sizes[label] = cls["size"]
                    
                    # Store corrected label for logging
                    if cls.get("corrected_label") and cls["corrected_label"] != label:
                        print(f"🔄 Gemini corrected: {label} → {cls['corrected_label']}")
                    
                    # Store add-on flags
                    if cls.get("add_on_flags"):
                        gemma_add_ons.extend(cls["add_on_flags"])
                        print(f"➕ Gemini detected add-ons for {label}: {cls['add_on_flags']}")
            
            # 2a.5 Apply Canonical Label System (Recommendation 4)
            # This normalizes all labels and applies proper volumes from catalog
            print("📝 Applying canonical label system...")
            catalog_items = catalog_volume.get("items", [])
            
            # v2.3 FIX: Apply synonym canonicalization BEFORE volume lookup
            for item in catalog_items:
                original_label = item.get("label", "")
                canonical = canonicalize_synonym(original_label.lower())
                if canonical != original_label.lower():
                    item["original_label"] = original_label
                    item["label"] = canonical
                    print(f"🔀 Synonym: {original_label} → {canonical}")
            
            gemini_classifications_list = [
                {"item": label, "category": cat, "corrected_label": label, "add_on_flags": gemma_add_ons}
                for label, cat in gemma_categories.items()
            ]
            catalog_items = vision_worker.apply_canonical_labels(catalog_items, gemini_classifications_list)
            
            # ==================== v2.5: DETECTION FINALIZATION ====================
            # PIPELINE INVARIANT: No volume math until detection list is finalized
            catalog_items = finalize_detections(
                catalog_items, 
                skip_ids=None,  # TODO: wire detection IDs from Gemini
                skip_labels=gemini_skip_labels,
                gemini_underdelivered=gemini_underdelivered  # v2.5: apply default skip if underdelivered
            )
            
            # Filter out invalid labels before audit
            valid_items = [item for item in catalog_items if item.get("is_valid_label", True)]
            invalid_count = len(catalog_items) - len(valid_items)
            if invalid_count > 0:
                print(f"   ⛔ Filtered {invalid_count} invalid labels before audit")
            catalog_items = valid_items
            catalog_volume["items"] = catalog_items
            
            # 2a.6 v3.3: Normalize bboxes + DBSCAN Spatial Clustering
            print("📦 Running v3.3: bbox normalization + DBSCAN clustering...")
            # Get image dimensions
            img_width = 1024
            img_height = 768
            for r in all_vision_results:
                if r.get("detections", {}).get("detections"):
                    first_det = r["detections"]["detections"][0]
                    bbox = first_det.get("bbox", [0, 0, 1024, 768])
                    img_width = max(img_width, int(bbox[2]) if len(bbox) > 2 else 1024)
                    img_height = max(img_height, int(bbox[3]) if len(bbox) > 3 else 768)
                    break
            
            # Phase 1: Normalize all bboxes first
            catalog_items = vision_worker.normalize_all_bboxes(catalog_items, img_width, img_height)
            
            # Phase 3: Store base_volume_yards (never zeroed)
            for item in catalog_items:
                item["base_volume_yards"] = item.get("volume_yards", 0.75)
            
            # Apply v3.3 cluster volumes with DBSCAN + diameter guard
            catalog_items = vision_worker.calculate_cluster_volumes_v33(catalog_items, img_width, img_height)
            
            # 2a.7 v3.3: Mode-aware pile remainder
            print("📊 Calculating pile remainder (v3.3 mode-aware)...")
            depth_stats = None
            for r in all_vision_results:
                if r.get("depth_stats"):
                    depth_stats = r["depth_stats"]
                    break
            
            # Phase 6: Union coverage (junk only)
            junk_items = [item for item in catalog_items if item.get("is_junk", True) and not item.get("is_background")]
            coverage = vision_worker.calculate_union_coverage(junk_items, img_width, img_height)
            
            # v2.3 RULE 2: Coverage sanity check - if 0% but valid bboxes exist, recalculate
            valid_bboxes = [item for item in catalog_items if item.get("bbox") or item.get("bbox_pixels")]
            if coverage == 0 and len(valid_bboxes) > 0:
                # Force recalculate from bbox areas
                total_bbox_area = sum(
                    (b[2] - b[0]) * (b[3] - b[1]) 
                    for item in valid_bboxes 
                    for b in [item.get("bbox", item.get("bbox_pixels", [0,0,0,0]))]
                )
                image_area = img_width * img_height
                coverage = min(1.0, total_bbox_area / image_area) if image_area > 0 else 0
                print(f"⚠️ v2.3: Coverage was 0% with {len(valid_bboxes)} bboxes, recalculated to {coverage:.1%}")
            
            residual = max(0, 1.0 - coverage)
            
            # Sum cluster volumes
            total_item_vol = sum(
                item.get("cluster_volume", 0) or item.get("volume_yards", 0.75)
                for item in catalog_items if not item.get("in_cluster")
            )
            
            # Phase 5: Mode-aware remainder trigger
            anchor_present = any(item.get("is_anchor") for item in catalog_items)
            mode = vision_worker.detect_scene_mode(catalog_items, depth_stats, coverage)
            print(f"   🎯 Scene mode: {mode}, coverage={coverage:.1%}, residual={residual:.1%}")
            
            # v2.5: Check for debris bucket - mutual exclusion with remainder
            debris_bucket_vol = sum(
                item.get("volume_yards", 0) for item in catalog_items 
                if item.get("is_bucket") or item.get("normalized_label", item.get("label", "")).lower() == "mixed_debris"
            )
            
            if vision_worker.should_activate_remainder(mode, residual, catalog_items, anchor_present, depth_stats):
                pile_remainder = vision_worker.estimate_pile_remainder_v31(catalog_items, img_width, img_height, total_item_vol, depth_stats)
                
                # v2.3 FIX: Cap remainder volume
                raw_remainder = pile_remainder.get("remainder_yards", 0)
                capped_remainder = cap_remainder_volume(raw_remainder, total_item_vol)
                
                # v2.5: Debris-remainder mutual exclusion
                if debris_bucket_vol > 1.5:
                    # Sharply reduce remainder when debris is already counted
                    reduced_remainder = min(capped_remainder, 1.0)  # Cap at 1.0 yd³ max
                    if reduced_remainder != capped_remainder:
                        print(f"⚠️ v2.5: Debris bucket={debris_bucket_vol:.2f} yd³, reducing remainder {capped_remainder:.2f} → {reduced_remainder:.2f}")
                        capped_remainder = reduced_remainder
                
                if capped_remainder != raw_remainder:
                    pile_remainder["remainder_yards"] = capped_remainder
                    pile_remainder["raw_remainder_yards"] = raw_remainder
            else:
                pile_remainder = {"remainder_yards": 0, "activated": False, "residual_pct": residual}
                print(f"   📊 Remainder skipped (mode={mode}, residual={residual:.1%})")
            
            # Final total
            remainder_vol = pile_remainder.get("remainder_yards", 0)
            total_with_remainder = total_item_vol + remainder_vol
            
            print(f"   📊 Total volume (v3.3): items={total_item_vol:.2f} + remainder={remainder_vol:.2f} = {total_with_remainder:.2f} yd³")
            
            # Phase 8: Auto-lock with hash
            pipeline_hash = vision_worker.finalize_volumes(catalog_items, pile_remainder)
            catalog_volume["items"] = catalog_items
            catalog_volume["pile_remainder"] = pile_remainder
            catalog_volume["total_volume_yards"] = total_with_remainder
            catalog_volume["pipeline_hash"] = pipeline_hash
            
            # 2b. GPT-5.2 Audit (replaces Gemini)
            # Build initial classifications list for audit
            initial_classifications = [
                {"category": gemma_categories.get(item.get("label", "").lower()) or 
                            ITEM_TO_CATEGORY.get(item.get("label", "").lower(), "furniture"),
                 "variant": "unknown",
                 "label": item.get("label", "unknown"),  # Include label for matching
                 "add_on_flags": gemma_add_ons if item.get("label", "").lower() in gemma_categories else []}
                for item in catalog_items
            ]
            
            # Pass catalog_items (not detections) so indices match the volume calculation loop
            audit_result = await self.audit_with_gpt5(
                visual_bridge,
                catalog_items,  # Use catalog items for consistent indexing
                catalog_volume,
                initial_classifications
            )
            
            # Apply GPT-5.2 audit corrections
            corrected_classifications, missed_vol, gpt_add_ons, volume_corrections = self.apply_audit_corrections(
                initial_classifications,
                audit_result
            )
            
            # Merge GPT-5.2 add-ons with Gemma add-ons
            for flag in gpt_add_ons:
                if flag not in gemma_add_ons:
                    gemma_add_ons.append(flag)
            
            # 3. Calculate Billable Volume with corrected categories and volumes
            raw_vol = catalog_volume.get("net_volume", 0.0)
            
            # Apply category multipliers per detected item
            billable_vol = 0.0
            for i, item in enumerate(catalog_volume.get("items", [])):
                label = item.get("label", "").lower()
                
                # Use corrected volume if available (for mis-labeled items like "car" → "ewaste_tv")
                if i in volume_corrections:
                    item_vol = volume_corrections[i]
                    print(f"📏 Using corrected volume for item_{i}: {item_vol:.2f} yd³")
                else:
                    item_vol = item.get("volume", 0.0) * (1 - item.get("void", 0.0))  # Net volume
                
                # Use corrected category if available, else Gemma, else static lookup
                if i < len(corrected_classifications):
                    category = corrected_classifications[i].get("category", "furniture")
                else:
                    category = gemma_categories.get(label) or ITEM_TO_CATEGORY.get(label, "furniture")
                
                # Use GPT-5.2 multipliers for GPT categories, else fall back to existing
                multiplier = GPT_CATEGORY_TO_MULTIPLIER.get(category) or CATEGORY_MULTIPLIERS.get(category, 1.0)
                billable_item_vol = item_vol * multiplier
                billable_vol += billable_item_vol
                print(f"📦 {label}: {item_vol:.2f} × {multiplier} ({category}) = {billable_item_vol:.2f} yd³")
            
            # Add missed item volume from GPT-5.2 audit
            if missed_vol > 0:
                billable_vol += missed_vol
                print(f"➕ Added missed items volume: +{missed_vol:.2f} yd³")
            
            # Use billable volume if we have item breakdown, else apply default 1.1×
            if billable_vol > 0:
                final_vol = billable_vol
            else:
                final_vol = raw_vol * 1.1  # Fallback multiplier
            
            # Add residue volume (pile area not covered by detected items)
            residual_area = residual_pile.get("residual_area", 0)
            if residual_area > 0:
                # Get scale from best available source
                best_scale = None
                for result in all_vision_results:
                    if result.get("scale_result", {}).get("px_per_inch"):
                        best_scale = result["scale_result"]["px_per_inch"]
                        break
                
                if best_scale and best_scale > 0:
                    # Convert residual px² to volume: assume 12" average debris height
                    residue_sq_inches = residual_area / (best_scale ** 2)
                    residue_vol_yd3 = (residue_sq_inches * 12) / (27 * 1728)  # 1728 cu in = 1 cu ft
                    # Apply demo_light multiplier for unknown residue
                    residue_vol_yd3 *= CATEGORY_MULTIPLIERS.get("demo_light", 1.25)
                    final_vol += residue_vol_yd3
                    print(f"📐 Added residue: {residue_vol_yd3:.2f} yd³ (with 1.25× demo_light mult)")
            
            if final_vol <= 0:
                final_vol = 0.5  # Minimum estimate if nothing detected
            
            # v2.2 HOTFIX: Calculate packed_sum for sanity check
            packed_sum = sum(
                item.get("cluster_volume", 0) or item.get("volume_yards", 0)
                for item in catalog_items
            )
            
            # v2.2 HOTFIX: Volume stage logging
            catalog_vol = catalog_volume.get("net_volume", 0.0)
            remainder_vol = residual_pile.get("remainder_yards", 0)
            print(f"📊 Volume stages: catalog={catalog_vol:.2f}, packed={packed_sum:.2f}, remainder={remainder_vol:.2f}, final={final_vol:.2f}")
            
            # v2.2 HOTFIX: Sanity check before tiering
            final_vol = sanity_check_volume(final_vol, packed_sum)
            
            # 4. Add-on flags only (not priced by tool in v2.1)
            add_on_flags = {}
            for flag in gemma_add_ons:
                add_on_flags[f"{flag}_possible"] = True
                print(f"🏷️ Add-on flag: {flag}_possible (UI will price)")
            
            # 5. Pricing Math v2.2 (TIERED + TIGHT RANGES + INVARIANTS + SANITY)
            final_vol = round_to_half(final_vol)  # Round to nearest 0.5 (display only)
            
            # Choose tier from volume (not price)
            tier_id, tier = choose_tier_v2(final_vol)
            base_price = tier["price"]
            tier_label = tier["label"]
            
            # Calculate v2.1 uncertainty inputs
            anchor_trust = "LOW" if not detections.get("anchor_found") else "MEDIUM"
            fallback_items = [item for item in catalog_items if item.get("used_fallback", False)]
            fallback_count = len(fallback_items)
            fallback_ratio = fallback_count / max(len(catalog_items), 1)
            
            # Sum fallback range widths for uncertainty
            fallback_uncertainty = sum(
                (item.get("range", (0, 0))[1] - item.get("range", (0, 0))[0])
                for item in fallback_items
            )
            
            size_conf = confidence.get("confidence", 0.85)
            catalog_variance = 0  # TODO: Compute from size variants
            near_cliff = is_near_cliff(final_vol, tier_id)
            
            # v2.1 delta with 1-tier crossing limit
            delta = calc_volume_delta_v21(
                final_vol, anchor_trust, fallback_uncertainty, 
                size_conf, catalog_variance, near_cliff, tier_id
            )
            print(f"💰 Tier v2.1: {tier_label} → ${base_price} (for {final_vol} yd³, delta=±{delta:.2f})")
            
            # Map volume bounds to price range
            vol_low = max(0, final_vol - delta)
            vol_high = final_vol + delta
            _, tier_low = choose_tier_v2(vol_low)
            _, tier_high = choose_tier_v2(vol_high)
            raw_min = tier_low["price"]
            raw_max = tier_high["price"]
            
            # Apply tier-aware cap
            cap = get_range_cap(base_price)
            base_min = max(raw_min, base_price - cap // 2, PRICE_FLOOR)
            base_max = min(raw_max, base_price + cap // 2)
            print(f"   📊 Range capped: ${base_min}–${base_max} (cap=${cap})")
            
            # Surcharges: only heavy_surcharge (add-ons are UI-only in v2.1)
            total_surcharge = heavy_surcharge
            
            # v2.1 finalize with directional rounding and invariants
            final_estimate, final_min, final_max = finalize_prices_v21(
                base_price, base_min, base_max, total_surcharge, tier_id
            )
            print(f"   ✅ Final v2.1: ${final_min}–${final_max} (estimate=${final_estimate})")
            
            # Detect flags (not priced by tool)
            disposal_flags = detect_disposal_flags(catalog_items)
            labor_flags = detect_labor_flags_v21(catalog_items)
            
            # Get reason codes
            top_ambiguous = []  # TODO: Compute from variance report
            reason_codes = get_reason_codes_v21(anchor_trust, fallback_ratio, near_cliff, top_ambiguous)
            
            # INVARIANT CHECK
            assert final_min <= final_estimate <= final_max, \
                f"Invariant violated: {final_estimate} not in [{final_min}, {final_max}]"
            
            return {
                "status": "SUCCESS",
                "volume_yards": final_vol,
                "min_price": final_min,
                "max_price": final_max,
                "price": final_estimate,
                "tier_label": tier_label,
                "heavy_surcharge": heavy_surcharge,
                "disposal_flags": disposal_flags,
                "add_on_flags": add_on_flags,
                "labor_flags": labor_flags,
                "trust_note": TRUST_NOTE,
                "reason_codes_customer": reason_codes["reason_codes_customer"],
                "vision_enhanced": True,
                "anchor_found": detections.get("anchor_found", False),
                "anchor_scale_inches": detections.get("anchor_scale_inches"),
                "detected_items": [d.get("label") for d in detections.get("detections", [])],
                "debug": {
                    "audit_result": audit_result,
                    "catalog_volume": catalog_volume,
                    "residual_pile": residual_pile,
                    "confidence": confidence,
                    "detections_count": len(detections.get("detections", [])),
                    "depth_available": any(r.get("depth_available", False) for r in all_vision_results),
                    "heavy_level": heavy_level,
                    "gemma_categories": gemma_categories,
                    "gpt5_risk_level": audit_result.get("uncertainty_band", {}).get("risk_level", "medium"),
                    "missed_vol": missed_vol,
                    # v2.1 debug fields
                    "v21_delta": delta,
                    "v21_tier_id": tier_id,
                    "v21_range_cap": cap,
                    "v21_near_cliff": near_cliff,
                    "v21_fallback_ratio": fallback_ratio,
                    "v21_fallback_uncertainty": fallback_uncertainty,
                    "v21_anchor_trust": anchor_trust,
                    "reason_codes_internal": reason_codes["reason_codes_internal"],
                    # Phase 4: GroundingDINO metrics
                    "florence_count": detections.get("florence_count", 0),
                    "gdino_count": detections.get("gdino_count", 0),
                    "new_discoveries": len([d for d in detections.get("detections", []) if d.get("source") == "grounding_dino_new"]),
                    "priority_overrides": len([d for d in detections.get("detections", []) if d.get("source") == "grounding_dino" and d.get("original_florence_label")]),
                    "gdino_tiers_used": list(set(d.get("tier", "unknown") for d in detections.get("detections", []) if d.get("source", "").startswith("grounding")))
                }
            }
            
        except Exception as e:
            print(f"❌ VISION PIPELINE ERROR: {e}")
            import traceback
            traceback.print_exc()
            # No fallback - return error to user
            return {
                "status": "VISION_ERROR",
                "message": str(e),
                "vision_error": VISION_ERROR
            }
    
    # ==================== SINGLE ITEM ENGINE ====================
    
    def _normalize_label(self, label: str) -> str:
        """Normalize Florence labels to match catalog keys."""
        label = label.lower().strip()
        # Common synonyms
        synonyms = {
            "sofa bed": "sofa",
            "couch sofa": "couch",
            "refrigerator freezer": "refrigerator",
            "washer dryer": "washing machine",
            "clothes dryer": "dryer",
            "washing machine": "washing machine",
        }
        for phrase, replacement in synonyms.items():
            if phrase in label:
                return replacement
        return label
    
    def _select_primary_item(self, detections: list, image_width: int, image_height: int) -> dict:
        """Select the detection closest to center with largest area."""
        if not detections:
            return None
        
        center_x, center_y = image_width / 2, image_height / 2
        best_score = -1
        best_det = None
        
        for det in detections:
            bbox = det.get("bbox", [])
            if len(bbox) != 4:
                continue
            
            # Calculate area
            area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
            
            # Calculate distance to center
            det_cx = (bbox[0] + bbox[2]) / 2
            det_cy = (bbox[1] + bbox[3]) / 2
            dist = ((det_cx - center_x) ** 2 + (det_cy - center_y) ** 2) ** 0.5
            
            # Score: larger area + closer to center = higher score
            # Normalize distance (invert so closer = higher)
            max_dist = (center_x ** 2 + center_y ** 2) ** 0.5
            dist_score = 1 - (dist / max_dist) if max_dist > 0 else 0
            
            score = area * (0.5 + 0.5 * dist_score)  # Weight area more
            
            if score > best_score:
                best_score = score
                best_det = det
        
        return best_det
    
    def _measure_item_dimension(self, bbox: list, depth_map, focal_px: float, 
                                 axis: str, image_width: int) -> float:
        """Measure item height or width in inches using Depth Pro."""
        import numpy as np
        
        if depth_map is None or focal_px is None:
            return 0.0
        
        # Get center point depth (robust sampling with 10x10 patch)
        cx = int((bbox[0] + bbox[2]) / 2)
        cy = int((bbox[1] + bbox[3]) / 2)
        
        h, w = depth_map.shape[:2]
        # Clamp to bounds
        x1 = max(0, cx - 5)
        x2 = min(w, cx + 5)
        y1 = max(0, cy - 5)
        y2 = min(h, cy + 5)
        
        try:
            dist_m = float(np.median(depth_map[y1:y2, x1:x2]))
        except:
            dist_m = 2.5  # Default fallback
        
        if dist_m <= 0.1:
            dist_m = 2.5
        
        # Calculate scale
        px_per_m = focal_px / dist_m
        
        # Select axis dimension
        if axis == 'h':
            px_dim = bbox[3] - bbox[1]  # Height
        else:
            px_dim = bbox[2] - bbox[0]  # Width
        
        # Convert to real inches
        real_inches = (px_dim / px_per_m) * 39.37
        
        print(f"📏 Measured {axis.upper()}: {real_inches:.1f}\" (dist={dist_m:.2f}m, focal={focal_px:.0f})")
        return real_inches
    
    def _bin_lookup(self, real_dim: float, bins: list) -> tuple:
        """Find matching (variant_name, volume) from bins."""
        for limit, name, vol in bins:
            if real_dim <= limit:
                return name, vol
        # Fallback to last bin
        return bins[-1][1], bins[-1][2]
    
    def _measure_unknown_item(self, bbox: list, depth_map, focal_px: float, image_width: int) -> float:
        """Measure full bbox volume for unknown items."""
        import numpy as np
        
        # Get both dimensions
        width_in = self._measure_item_dimension(bbox, depth_map, focal_px, 'w', image_width)
        height_in = self._measure_item_dimension(bbox, depth_map, focal_px, 'h', image_width)
        
        # Estimate depth as 60% of width
        depth_in = width_in * 0.6
        
        # Calculate volume in cubic yards (46656 cu in per cubic yard)
        vol_yards = (width_in * height_in * depth_in) / 46656.0
        
        # Clamp to reasonable range
        vol_yards = max(0.1, min(vol_yards, 5.0))
        
        print(f"📦 Unknown item volume: {vol_yards:.2f} yd³ ({width_in:.0f}×{height_in:.0f}×{depth_in:.0f}\")")
        return vol_yards
    
    def _finalize_single_item_quote(self, volume: float, item_name: str, surcharges: list) -> dict:
        """Build final response with synthesized dimensions."""
        # Round volume to nearest 0.5
        volume = round_to_half(volume)
        
        # Get tier price (replaces flat rate)
        tier_price, tier_label = get_tier_price(volume)
        vol_price = tier_price
        
        # Add surcharges (protected from min load)
        surcharge_total = sum(s.get('amount', 0) for s in surcharges)
        final_price = vol_price + surcharge_total
        
        # Synthesize cube dimensions for frontend compatibility
        cube_side = (volume * 46656) ** (1/3) if volume > 0 else 12
        
        print(f"💰 Single Item: {tier_label} → ${final_price:.0f} ({volume} yd³)")
        
        return {
            "status": "SUCCESS",
            "min_price": int(final_price),
            "max_price": int(final_price),  # Fixed price for single items
            "price": round(final_price, 2),
            "volume_yards": volume,  # Already rounded to 0.5
            "item_detected": item_name,
            "heavy_surcharge": int(surcharge_total),
            "surcharges": surcharges,
            "vision_enhanced": True,
            "packed_dimensions": {
                "l": round(cube_side, 1),
                "w": round(cube_side, 1),
                "h": round(cube_side, 1)
            }
        }
    
    async def process_single_item(self, image_b64: str) -> dict:
        """
        Main entry point for Single Item quotes.
        Uses Smart Triage: fast catalog lookup OR measurement.
        """
        import numpy as np
        
        print("🎯 SINGLE ITEM ENGINE ACTIVATED")
        
        try:
            # Initialize vision worker
            if not VISION_ENABLED:
                raise ValueError(f"Vision not available: {VISION_ERROR}")
            
            vision_worker = VisionWorker()
            
            # 1. Run Florence-2 detection
            print("🔍 Phase 1: Florence-2 Detection...")
            florence_result = vision_worker.run_florence_detection(image_b64)
            detections = florence_result.get("detections", [])
            
            if not detections:
                print("⚠️ No items detected, using fallback")
                return self._finalize_single_item_quote(0.5, "Unknown Item", [])
            
            # Get image dimensions
            img_bytes = base64.b64decode(image_b64)
            img = Image.open(io.BytesIO(img_bytes))
            image_width, image_height = img.size
            
            # Initialize surcharges list
            active_surcharges = []
            
            # 2. Handle multi-item detection (sum Tier 1 volumes)
            if len(detections) > 1:
                print(f"📦 Multiple items detected ({len(detections)}), summing volumes")
                total_vol = 0.0
                item_names = []
                for det in detections:
                    label = self._normalize_label(det.get("label", "unknown"))
                    # Use Tier 1 catalog with conservative 0.2 fallback for unknowns
                    vol = TIER_1_CATALOG.get(label, 0.2)
                    total_vol += vol
                    item_names.append(label)
                
                return self._finalize_single_item_quote(
                    total_vol, 
                    f"Set: {', '.join(item_names[:3])}{'...' if len(item_names) > 3 else ''}", 
                    active_surcharges
                )
            
            # 3. Single item processing
            primary = self._select_primary_item(detections, image_width, image_height)
            if not primary:
                return self._finalize_single_item_quote(0.5, "Unknown Item", [])
            
            raw_label = primary.get("label", "unknown")
            label = self._normalize_label(raw_label)
            bbox = primary.get("bbox", [0, 0, 100, 100])
            
            print(f"🏷️ Primary item: '{label}' (raw: '{raw_label}')")
            
            # 4. Check for high-risk items → GPT audit
            for keyword in HIGH_RISK_KEYWORDS:
                if keyword in label.lower():
                    print(f"⚠️ High-risk item detected: {keyword}")
                    active_surcharges.append({
                        "name": f"Heavy Lift Fee ({label})",
                        "amount": 50.0
                    })
                    break
            
            # 5. PATH A: Tier 1 catalog (instant lookup)
            if label in TIER_1_CATALOG:
                print(f"⚡ Path A: Tier 1 catalog hit for '{label}'")
                return self._finalize_single_item_quote(
                    TIER_1_CATALOG[label], 
                    label.title(), 
                    active_surcharges
                )
            
            # 6. PATH B: Tier 2 or Unknown (run Depth Pro)
            print(f"📐 Path B: Running Depth Pro for measurement...")
            
            # Run Depth Pro
            depth_result = vision_worker.run_depth_pro(image_b64)
            depth_map = depth_result.get("depth_map") if depth_result.get("success") else None
            focal_px = depth_result.get("focal_px")
            
            # Fallback focal if not provided
            if not focal_px:
                focal_px = image_width * 0.7
                print(f"📷 Using fallback focal: {focal_px:.0f}px")
            
            if label in TIER_2_ROUTING:
                # Known variable item → axis-aware measurement
                routing = TIER_2_ROUTING[label]
                axis = routing["axis"]
                bins = routing["bins"]
                
                real_dim = self._measure_item_dimension(bbox, depth_map, focal_px, axis, image_width)
                variant, volume = self._bin_lookup(real_dim, bins)
                
                print(f"📊 Tier 2 result: {label} ({variant}) = {volume} yd³")
                return self._finalize_single_item_quote(
                    volume, 
                    f"{label.title()} ({variant})", 
                    active_surcharges
                )
            else:
                # Unknown item → measure full bbox
                print(f"❓ Unknown item '{label}', measuring bbox volume")
                volume = self._measure_unknown_item(bbox, depth_map, focal_px, image_width)
                return self._finalize_single_item_quote(
                    volume, 
                    f"Measured {label.title()}", 
                    active_surcharges
                )
                
        except Exception as e:
            print(f"❌ SINGLE ITEM ERROR: {e}")
            import traceback
            traceback.print_exc()
            return {
                "status": "VISION_ERROR",
                "message": str(e),
                "min_price": 95,
                "max_price": 95
            }

# --- Serverless Handler ---
engine = PricingEngine()

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        # 1. Rate Limit
        x_forwarded_for = self.headers.get('x-forwarded-for')
        if x_forwarded_for:
            user_ip = x_forwarded_for.split(',')[0].strip()
        else:
            user_ip = self.client_address[0]
            
        if not engine.check_rate_limit(user_ip):
            self.send_response(429)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Rate limit exceeded. Maximum 5 quotes per hour."}).encode('utf-8'))
            return

        # 2. Parse Body
        content_len = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_len)
        data = json.loads(body)
        images_b64 = data.get('images', [])
        heavy_level = data.get('heavyMaterialLevel', 'none')
        mode = data.get('mode', 'pile')  # Default to pile for backward compatibility

        try:
             # Prepare inputs
            base64_imgs = [img.split(",")[1] if "," in img else img for img in images_b64]
            
            # 3. Check Vision Pipeline
            if not VISION_ENABLED:
                raise ValueError(f"Vision Pipeline not available: {VISION_ERROR}")
            
            # 4. Route based on mode
            if mode == 'single':
                print("🎯 Single Item Mode Active")
                result = asyncio.run(engine.process_single_item(base64_imgs[0]))
            else:
                print("📦 Pile Mode Active (Florence-2 + Depth-Anything-V2)")
                result = asyncio.run(engine.process_quote_with_vision(base64_imgs, heavy_level))
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode('utf-8'))
            
        except Exception as e:
            print(f"Server Error: {e}")
            self.send_error(500, str(e))
