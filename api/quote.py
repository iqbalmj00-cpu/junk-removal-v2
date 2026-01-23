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
        {"max_cuft": 27,   "price": 95,  "label": "Min Load"},       # 1 yd³
        {"max_cuft": 60,   "price": 99,  "label": "1/8 Load"},       # ~2.2 yd³
        {"max_cuft": 80,   "price": 129, "label": "1/6 Load"},       # ~3.0 yd³
        {"max_cuft": 120,  "price": 149, "label": "1/4 Load"},       # ~4.4 yd³
        {"max_cuft": 180,  "price": 199, "label": "3/8 Load"},       # ~6.7 yd³
        {"max_cuft": 240,  "price": 299, "label": "Half Load"},      # ~8.9 yd³
        {"max_cuft": 300,  "price": 349, "label": "5/8 Load"},       # ~11 yd³
        {"max_cuft": 360,  "price": 399, "label": "3/4 Load"},       # ~13 yd³
        {"max_cuft": 420,  "price": 479, "label": "7/8 Load"},       # ~16 yd³
        {"max_cuft": 486,  "price": 599, "label": "Full Load"},      # 18 yd³ MAX
    ]
    
    def round_to_half(value: float) -> float:
        """Round to nearest 0.5."""
        return round(value * 2) / 2
    
    def get_tier_price(volume_yards: float) -> tuple:
        """Convert cubic yards to (price, label) using tiers."""
        cuft = volume_yards * 27
        for tier in VOLUME_TIERS:
            if cuft <= tier["max_cuft"]:
                return tier["price"], tier["label"]
        return 599, "Full Load"
    
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
        "tier1": "furniture . appliance . mattress . electronics . debris pile . boxes . bags",
        
        # Tier 2: Specific high-value items (run if Tier 1 finds <5 items)
        "tier2": "pallet . wooden pallet . CRT television . flat screen TV . shelving unit . "
                 "refrigerator . washer . dryer . couch . sofa . dresser . desk . table . "
                 "tires . construction debris . drywall . concrete . scrap metal",
        
        # Tier 3: Edge cases (run if Tier 2 still finds <3 items)
        "tier3": "hot tub . spa . exercise equipment . treadmill . elliptical . piano . "
                 "pool table . trampoline . swing set . shed components . fence panels"
    }
    
    # GroundingDINO model identifier (Replicate)
    GROUNDING_DINO_MODEL = "adirik/grounding-dino:efd10a8ddc57ea28773327e881ce95e6e2c9caf9efd10a8ddc57ea28773327e8"
    
    # Confidence threshold for GroundingDINO detections
    GROUNDING_DINO_CONFIDENCE = 0.35
    
    # Label priority: open-vocab labels take precedence over Florence generic labels
    OPEN_VOCAB_PRIORITY_LABELS = [
        "pallet", "wooden pallet", "crt television", "flat screen tv", 
        "shelving unit", "construction debris", "scrap metal", "hot tub",
        "exercise equipment", "treadmill", "piano", "pool table"
    ]
    
    # GPT-5.2 Audit System Prompt
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
        
        def merge_detections(self, florence_dets: list, gdino_dets: list) -> list:
            """Merge Florence-2 and GroundingDINO detections, prioritizing open-vocab labels."""
            merged = []
            used_gdino_indices = set()
            
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

    async def ask_gpt(self, base64_images):
        try:
            content = [{"type": "text", "text": self._get_system_prompt()}]
            for img_b64 in base64_images:
                 content.append({
                    "type": "image_url", 
                    "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}
                })

            response = await self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": content}],
                temperature=0.0,
                max_tokens=300,
                response_format={"type": "json_object"}
            )
            
            raw_content = response.choices[0].message.content
             # Cleanup markdown
            if raw_content.startswith("```json"):
                raw_content = raw_content[7:]
            if raw_content.endswith("```"):
                raw_content = raw_content[:-3]
                
            return json.loads(raw_content)
        except Exception as e:
            print(f"❌ GPT ERROR: {e}")
            return None
    
    async def classify_with_gemma(self, image_b64: str, items: list) -> list:
        """Use Google Gemini Vision to classify ambiguous items into pricing categories."""
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
1. For background objects (parked cars, trucks, buildings), set is_junk: false
2. For TVs: distinguish CRT (boxy, deep) from flat screens - different categories!
3. For piles: estimate what material it is (wood, concrete, mixed)
4. Count pallets if stacked together (put count in corrected_label: "4 pallets")

Return JSON array ONLY. No explanation."""

            print(f"🔮 Calling Google Gemini Vision for {len(items)} items...")
            
            # Use Google Gemini Vision API
            response = self.google_client.models.generate_content(
                model="gemini-2.0-flash",
                contents=[
                    types.Content(
                        role="user",
                        parts=[
                            types.Part.from_bytes(
                                data=base64.b64decode(image_b64),
                                mime_type="image/jpeg"
                            ),
                            types.Part.from_text(text=prompt)
                        ]
                    )
                ],
                config=types.GenerateContentConfig(
                    max_output_tokens=1000
                )
            )
            
            # Debug: print raw response
            result_text = response.text if response.text else ""
            print(f"🔮 Gemini raw response length: {len(result_text)} chars")
            
            if not result_text:
                # Try getting text from candidates
                if hasattr(response, 'candidates') and response.candidates:
                    for candidate in response.candidates:
                        if hasattr(candidate, 'content') and candidate.content:
                            for part in candidate.content.parts:
                                if hasattr(part, 'text') and part.text:
                                    result_text = part.text
                                    break
            
            if not result_text:
                raise ValueError("Empty response from Gemini")
            
            # Clean up any markdown formatting
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0]
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0]
            
            result = json.loads(result_text.strip())
            print(f"🔮 Gemini classifications: {result}")
            return result
            
        except Exception as e:
            print(f"⚠️ Gemini classification failed: {e}, using static mapping")
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
        print("🚀 STARTING DUAL-MODEL CONSENSUS (Async)...")
        
        # Heavy Surcharge from user selection
        heavy_surcharge = HEAVY_SURCHARGES.get(heavy_level, 0)
        print(f"📦 Heavy Material Level: {heavy_level} -> +${heavy_surcharge}")
        
        # 1. Prepare Gemini Inputs
        gemini_inputs = []
        for img_bytes in images:
             gemini_inputs.append(types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg"))

        # 2. Parallel Execution (Survivor Protocol)
        results = await asyncio.gather(
            self.ask_gemini(gemini_inputs),
            self.ask_gpt(base64_images),
            return_exceptions=True
        )
        
        res_gemini = results[0] if not isinstance(results[0], Exception) else None
        res_gpt = results[1] if not isinstance(results[1], Exception) else None

        if isinstance(results[0], Exception): print(f"❌ Gemini Exception: {results[0]}")
        if isinstance(results[1], Exception): print(f"❌ GPT Exception: {results[1]}")

        # 3. Fail-Over Check
        if not res_gemini and not res_gpt:
            return {"status": "SHADOW_MODE", "message": "Both Models Failed", "reason": "System Outage"}
        
        # Use survivor if one failed
        if not res_gemini:
            res_gemini = res_gpt
            print("⚠️ Gemini failed, mirroring GPT data.")
        if not res_gpt:
            res_gpt = res_gemini
            print("⚠️ GPT failed, mirroring Gemini data.")

        # 4. Confidence Gate
        conf_gemini = res_gemini.get('confidence_score', 0)
        conf_gpt = res_gpt.get('confidence_score', 0)
        
        if conf_gemini < 0.5 and conf_gpt < 0.5:
             return {"status": "SHADOW_MODE", "message": "Image Unclear", "debug": f"Conf: G{conf_gemini}|O{conf_gpt}"}

        # 5. Variance Check
        vol_gemini = self.calculate_volume(res_gemini)
        vol_gpt = self.calculate_volume(res_gpt)
        
        # Filter out invalid volumes (0.0 usually means parsing error or empty response)
        if vol_gemini <= 0: vol_gemini = vol_gpt
        if vol_gpt <= 0: vol_gpt = vol_gemini

        diff = abs(vol_gemini - vol_gpt)
        avg_vol = (vol_gemini + vol_gpt) / 2
        variance = (diff / avg_vol) if avg_vol > 0 else 0
        
        print(f"🧮 MATH: Gemini({vol_gemini:.2f}) | GPT({vol_gpt:.2f}) | Diff({diff:.2f}) | Var({variance:.1%})")

        final_vol = 0.0
        
        # Small Load Exception
        if diff < 1.5:
            final_vol = avg_vol
            print("✅ SMALL LOAD EXCEPTION: Using Average")
        elif variance < 0.20:
             # High Agreement
             final_vol = avg_vol
             print("✅ HIGH AGREEMENT: Using Average")
        elif variance <= 0.40:
             # Moderate Disagreement -> Be Conservative (Min)
             final_vol = min(vol_gemini, vol_gpt)
             print("⚠️ MODERATE DISAGREEMENT: Using Minimum")
        else:
             # High Variance
             return {
                 "status": "SHADOW_MODE", 
                 "message": "High Variance Detected", 
                 "debug": f"Variance {variance:.1%}. Gemini: {vol_gemini} vs GPT: {vol_gpt}"
             }

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
                "gpt_vol": vol_gpt,
                "variance": f"{variance:.1%}",
                "gemini_raw": res_gemini,
                "gpt_raw": res_gpt,
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
            
            all_detections = detections.get("detections", [])
            ambiguous_items = [d for d in all_detections 
                               if d.get("label", "").lower() in AMBIGUOUS_LABELS 
                               or d.get("label", "").lower() not in ITEM_TO_CATEGORY]
            
            if ambiguous_items and visual_bridge:
                print(f"🔮 {len(ambiguous_items)} ambiguous items found, calling Gemini Vision...")
                classifications = await self.classify_with_gemma(visual_bridge, ambiguous_items)
                
                # Store Gemini classifications for volume calculation
                gemma_sizes = {}  # label -> size bucket
                for cls in classifications:
                    label = cls.get("item", "").lower()
                    
                    # Skip if Gemini says this isn't junk (background object)
                    if cls.get("is_junk") == False:
                        print(f"🚫 Gemini identified {label} as background object, skipping")
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
            
            # 2b. GPT-5.2 Audit (replaces Gemini)
            # Build initial classifications list for audit
            catalog_items = catalog_volume.get("items", [])
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
            
            # 4. Add-on surcharges from Gemma classification
            add_on_surcharge = 0
            for flag in gemma_add_ons:
                if flag in ADD_ON_FEES:
                    add_on_surcharge += ADD_ON_FEES[flag]
                    print(f"➕ Add-on fee: {flag} = +${ADD_ON_FEES[flag]}")
            
            # 5. Pricing Math (TIERED PRICING)
            final_vol = round_to_half(final_vol)  # Round to nearest 0.5
            
            # Get tier price (replaces flat rate)
            tier_price, tier_label = get_tier_price(final_vol)
            vol_price = tier_price
            print(f"💰 Tier: {tier_label} → ${tier_price} (for {final_vol} yd³)")
            
            # Apply uncertainty band from GPT-5.2 (if available) or fallback
            gpt_uncertainty = audit_result.get("uncertainty_band", {})
            risk_level = gpt_uncertainty.get("risk_level", "medium")
            band_map = {"low": 0.10, "medium": 0.20, "high": 0.35}
            band = band_map.get(risk_level, uncertainty_result.get("uncertainty", confidence.get("band", 0.20)))
            
            min_vol_price = max(95, round(vol_price * (1 - band)))  # Floor at Min Load ($95)
            max_vol_price = round(vol_price * (1 + band))
            
            # Add fixed surcharges AFTER (protected from discounting)
            total_surcharge = heavy_surcharge + add_on_surcharge
            min_price = min_vol_price + total_surcharge
            max_price = max_vol_price + total_surcharge
            
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
                "price": round(vol_price + total_surcharge, 2),
                "heavy_surcharge": total_surcharge,  # Combined heavy + add-ons
                "add_on_surcharge": add_on_surcharge,
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
                    "gemma_add_ons": gemma_add_ons,
                    "gpt5_risk_level": risk_level,
                    "missed_vol": missed_vol,
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
