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
    "carpet", "debris pile", "exercise equipment", "treadmill",
    # P0.1: Bulky items for dead-zone fix
    "bookshelf", "shelf", "shelving unit", "rug", "rolled carpet",
    "crate", "wooden crate", "bed frame", "furniture frame"
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
    # Bags & Boxes (boosted - bags add up quickly)
    ("bags", "small"): 0.15,
    ("bags", "medium"): 0.25,
    ("bags", "large"): 0.40,
    ("boxes", "small"): 0.12,
    ("boxes", "medium"): 0.20,
    ("boxes", "large"): 0.35,
    
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
    
    # P0.2: Expanded bulky items (closing dead-zone)
    ("bookshelf", "small"): 0.6,
    ("bookshelf", "medium"): 1.0,
    ("bookshelf", "large"): 1.5,
    ("shelf", "small"): 0.4,
    ("shelf", "medium"): 0.8,
    ("shelf", "large"): 1.2,
    ("shelving", "medium"): 0.8,
    ("shelving", "large"): 1.2,
    ("rug", "small"): 0.3,
    ("rug", "medium"): 0.5,
    ("rug", "large"): 0.8,
    ("crate", "small"): 0.2,
    ("crate", "medium"): 0.3,
    ("crate", "large"): 0.5,
    ("bin", "small"): 0.2,
    ("bin", "medium"): 0.4,
    ("bin", "large"): 0.6,
    ("storage bin", "medium"): 0.4,
    ("storage bin", "large"): 0.6,
    ("bed frame", "medium"): 0.8,
    ("bed frame", "large"): 1.0,
    ("furniture frame", "medium"): 0.6,
    ("furniture frame", "large"): 1.0,
}

# Default volume when not in catalog (boosted from 0.3)
DEFAULT_VOLUME = 0.4

# ==============================================================================
# BULKY DISCRETE LANE (P1: Safety net for dead-zone)
# ==============================================================================

# Classes that are "bulky discrete" - large structured objects
BULKY_DISCRETE_CLASSES = {
    "mattress", "bookshelf", "shelf", "shelving", "carpet", "rug",
    "large bin", "storage bin", "crate", "bin", "bed frame", 
    "furniture frame", "couch", "sofa", "dresser", "table"
}

# Conservative volume priors when catalog lookup returns 0
BULKY_DISCRETE_VOLUMES = {
    "mattress": 1.2,
    "bookshelf": 1.0,
    "shelf": 0.8,
    "shelving": 0.8,
    "carpet": 0.6,
    "rug": 0.5,
    "large bin": 0.4,
    "storage bin": 0.4,
    "bin": 0.4,
    "crate": 0.3,
    "bed frame": 1.0,
    "furniture frame": 0.8,
    "couch": 1.5,
    "sofa": 1.5,
    "dresser": 1.0,
    "table": 0.8,
}

# Pile-relative geometry thresholds (not frame-relative!)
BULKY_MASK_PILE_RATIO = 0.06   # mask_area / pile_area >= 6%
BULKY_BBOX_PILE_RATIO = 0.08   # bbox_area / pile_area >= 8%

# Gate thresholds for applying bulky lane
BULKY_GATE_REMAINDER_MIN = 0.10
BULKY_GATE_FALLBACK_RATE_MIN = 0.40

# ==============================================================================
# OWNERSHIP PIPELINE THRESHOLDS (Gap 1-4)
# ==============================================================================

# Area thresholds for subtraction
AREA_LARGE = 0.06               # Unowned blob detection threshold
AREA_COUNTABLE_SUBTRACT = 0.03  # Gap 2: Countable subtraction threshold (smaller)
SUBTRACTION_MAX_RATIO = 0.85    # Clamp: can't subtract > 85% of pile

# Policy A: fallback for unowned blobs
HEIGHT_FACTOR_MIN = 0.5         # Conservative height multiplier for blob volume

# Vision quality gates (Step 3/5)
VISION_QUALITY_FALLBACK_MAX = 0.40  # If fallback_rate > 40%, tighten countables
VISION_QUALITY_SPREAD_MAX = 1.5     # If mask_spread > 1.5, use trimmed aggregation

# ==============================================================================
# COUNTABLE CLASSES (never considered as bulky candidates)
# ==============================================================================

COUNTABLE_CLASSES = {
    "bags", "boxes", "trash bag", "garbage bag", "trashbag",
    "plastic storage tote", "moving box", "cardboard box", 
    "tote", "plastic bin", "storage bin"
}

# ==============================================================================
# BEST-VIEW ESTIMATOR THRESHOLDS
# ==============================================================================

BEST_VIEW_SPREAD_MIN = 1.35      # Only use best-view if max/median >= 1.35
BEST_VIEW_MAX_PILE_CAP = 0.55    # Max pile ratio must be <= 55% (anti-mask-outlier)
BEST_VIEW_MIN_ITEMS_COV = 0.03   # Best frame must have >= 3% item coverage

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
    
    # Bulky items (P0.1 vocab expansion)
    "shelving unit": "shelf",
    "rolled carpet": "carpet",
    "wooden crate": "crate",
    "large bin": "bin",
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
