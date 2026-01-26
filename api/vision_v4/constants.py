"""
v4.0 Constants and Configuration

Contains all vocabulary, thresholds, and catalog data for the vision pipeline.
"""

# ==============================================================================
# MODEL VERSIONS
# ==============================================================================

YOLO_WORLD_VERSION = "franz-biz/yolo-world-xl:fd1305d3fc19e81540542f51c2530cf8f393e28cc6ff4976337c3e2b75c7c292"
LANG_SAM_VERSION = "tmappdev/lang-segment-anything:891411c38a6ed2d44c004b7b9e44217df7a5b07848f29ddefd2e28bc7cbf93bc"

# ==============================================================================
# YOLO VOCABULARY (Tiered for progressive detection)
# ==============================================================================

YOLO_VOCAB_TIER_1 = [
    "trash bag", "garbage bag", "cardboard box", "moving box",
    "plastic storage tote", "plastic bin", "tire", "mattress",
    "couch", "sofa", "chair", "table", "dresser",
    "tv", "monitor", "speaker", "subwoofer", "washer", "dryer",
    "refrigerator", "freezer", "foam cushion"
]

YOLO_VOCAB_TIER_2 = [
    "wood debris", "lumber", "fence panel", "pallet",
    "metal scrap", "metal pipe", "branches", "yard waste",
    "carpet", "debris pile", "exercise equipment", "treadmill"
]

YOLO_VOCAB_TIER_3 = [
    "hot tub", "spa", "motorcycle", "scooter",
    "piano", "safe", "pool table"
]

YOLO_VOCAB_ALL = YOLO_VOCAB_TIER_1 + YOLO_VOCAB_TIER_2 + YOLO_VOCAB_TIER_3

# ==============================================================================
# PILE SEGMENTATION PROMPTS
# ==============================================================================

PILE_PROMPTS = "pile of junk, mixed debris, yard waste pile, garbage pile, clutter, trash heap"

# Labels that indicate pile regions (not discrete billable items)
PILE_LABELS = {
    "yard waste", "debris pile", "debris", "trash pile", 
    "clutter", "junk pile", "mixed debris", "garbage pile"
}

# ==============================================================================
# LANE SPLIT THRESHOLDS
# ==============================================================================

PILE_AREA_THRESHOLD = 0.45      # >45% of image = pile region
NOISE_AREA_THRESHOLD = 0.002    # <0.2% = noise, drop
PILE_OVERLAP_HIGH = 0.60        # High overlap with pile mask
MIN_CONFIDENCE = 0.10           # Below this = drop in early gating

# ==============================================================================
# CATALOG VOLUMES (cubic yards by label + size)
# ==============================================================================

CATALOG_VOLUMES = {
    # Bags & Boxes
    ("bags", "small"): 0.10,
    ("bags", "medium"): 0.15,
    ("bags", "large"): 0.25,
    ("boxes", "small"): 0.08,
    ("boxes", "medium"): 0.15,
    ("boxes", "large"): 0.25,
    
    # Furniture
    ("couch", "medium"): 1.5,
    ("couch", "large"): 2.5,
    ("couch", "xlarge"): 3.0,
    ("sofa", "medium"): 1.5,
    ("sofa", "large"): 2.5,
    ("mattress", "small"): 0.5,
    ("mattress", "medium"): 1.0,
    ("mattress", "large"): 1.5,
    ("dresser", "small"): 0.5,
    ("dresser", "medium"): 1.0,
    ("dresser", "large"): 1.5,
    ("table", "small"): 0.4,
    ("table", "medium"): 0.8,
    ("table", "large"): 1.2,
    ("chair", "small"): 0.3,
    ("chair", "medium"): 0.5,
    ("chair", "large"): 0.7,
    ("foam cushion", "small"): 0.2,
    ("foam cushion", "medium"): 0.4,
    
    # Appliances
    ("refrigerator", "medium"): 1.5,
    ("refrigerator", "large"): 2.0,
    ("refrigerator", "xlarge"): 2.5,
    ("freezer", "medium"): 1.2,
    ("freezer", "large"): 1.8,
    ("washer", "medium"): 1.0,
    ("washer", "large"): 1.2,
    ("dryer", "medium"): 1.0,
    ("dryer", "large"): 1.2,
    
    # Electronics
    ("tv", "small"): 0.15,
    ("tv", "medium"): 0.3,
    ("tv", "large"): 0.5,
    ("monitor", "small"): 0.1,
    ("monitor", "medium"): 0.2,
    ("speaker", "small"): 0.1,
    ("speaker", "medium"): 0.3,
    ("speaker", "large"): 0.5,
    ("subwoofer", "small"): 0.15,
    ("subwoofer", "medium"): 0.3,
    ("subwoofer", "large"): 0.5,
    
    # Yard & Construction
    ("tire", "small"): 0.15,
    ("tire", "medium"): 0.25,
    ("tire", "large"): 0.4,
    ("wood debris", "small"): 0.2,
    ("wood debris", "medium"): 0.5,
    ("wood debris", "large"): 1.0,
    ("lumber", "small"): 0.2,
    ("lumber", "medium"): 0.5,
    ("lumber", "large"): 1.0,
    ("fence panel", "medium"): 0.4,
    ("fence panel", "large"): 0.6,
    ("pallet", "medium"): 0.3,
    ("branches", "small"): 0.2,
    ("branches", "medium"): 0.5,
    ("branches", "large"): 1.0,
    ("carpet", "medium"): 0.5,
    ("carpet", "large"): 1.0,
    ("metal scrap", "small"): 0.1,
    ("metal scrap", "medium"): 0.3,
    ("metal pipe", "medium"): 0.2,
    ("exercise equipment", "medium"): 0.8,
    ("exercise equipment", "large"): 1.5,
    ("treadmill", "large"): 1.5,
    
    # Big-ticket
    ("hot tub", "large"): 4.0,
    ("hot tub", "xlarge"): 5.0,
    ("spa", "large"): 4.0,
    ("motorcycle", "medium"): 1.5,
    ("scooter", "small"): 0.5,
    ("piano", "large"): 3.0,
    ("piano", "xlarge"): 4.0,
    ("safe", "medium"): 0.5,
    ("safe", "large"): 1.0,
    ("pool table", "xlarge"): 4.0,
}

# Default volume when not in catalog
DEFAULT_VOLUME = 0.3

# ==============================================================================
# CANONICAL LABEL MAPPING
# ==============================================================================

CANONICAL_LABELS = {
    # Bags
    "trash bag": "bags",
    "garbage bag": "bags",
    "bag of trash": "bags",
    "plastic bag": "bags",
    
    # Boxes
    "cardboard box": "boxes",
    "moving box": "boxes",
    "plastic storage tote": "boxes",
    "plastic bin": "boxes",
    "storage bin": "boxes",
    "tote": "boxes",
    
    # Furniture
    "sofa": "couch",
    "loveseat": "couch",
    "sectional": "couch",
    "recliner": "chair",
    "ottoman": "chair",
    "desk": "table",
    "nightstand": "dresser",
    "bureau": "dresser",
    "chest": "dresser",
    
    # Appliances
    "fridge": "refrigerator",
    "washing machine": "washer",
    "drying machine": "dryer",
    "dishwasher": "washer",
    
    # Electronics
    "television": "tv",
    "computer monitor": "monitor",
    "loudspeaker": "speaker",
    "woofer": "subwoofer",
}

# ==============================================================================
# ADD-ON FLAGS
# ==============================================================================

HEAVY_ITEMS = {"refrigerator", "freezer", "washer", "dryer", "piano", "safe", "hot tub", "pool table"}
EWASTE_ITEMS = {"tv", "monitor", "computer", "printer", "electronics"}
TWO_PERSON_ITEMS = {"couch", "sofa", "mattress", "refrigerator", "washer", "dryer", "piano", "hot tub", "pool table"}
HAZMAT_ITEMS = {"tire", "paint", "chemicals", "batteries"}

# ==============================================================================
# PRICING TIERS
# ==============================================================================

PRICING_TIERS = [
    {"name": "Minimum", "max_vol": 2.5, "base_price": 135},
    {"name": "Quarter Load", "max_vol": 4.0, "base_price": 195},
    {"name": "Half Load", "max_vol": 8.0, "base_price": 350},
    {"name": "Three-Quarter Load", "max_vol": 12.0, "base_price": 475},
    {"name": "Full Load", "max_vol": 16.0, "base_price": 595},
]
