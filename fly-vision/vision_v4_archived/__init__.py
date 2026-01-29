"""
v4.0 Vision Pipeline
YOLO-World + Lang-SAM + GPT Architecture

Modules:
- orchestrator: Main pipeline flow
- pile_segmenter: Lang-SAM pile boundary detection
- yolo_detector: YOLO-World open-vocab detection
- gating: Bbox validation and early filtering
- item_segmenter: Lang-SAM per-item segmentation
- lane_splitter: Pile vs discrete item classification
- classifier: GPT batch classification
- fusion: Cross-image deduplication
- remainder: Remainder mask computation
- volume_engine: Two-lane volume calculation
- audit: GPT final audit
- response_builder: API response formatting
"""

from .orchestrator import process_quote_v4
from .constants import (
    YOLO_VOCAB_TIER_1,
    YOLO_VOCAB_TIER_2,
    YOLO_VOCAB_TIER_3,
    YOLO_VOCAB_ALL,
    PILE_PROMPTS,
    CATALOG_VOLUMES,
)

__version__ = "4.0.0"
__all__ = ["process_quote_v4"]
