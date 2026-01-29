"""
Pricing Engine for Junk Removal Volume Quotes

Simple lookup table: round volume UP to nearest 0.5, then get price from table.
"""

import math
from typing import Tuple

# Direct price lookup table: volume (yd³) -> price ($)
PRICE_TABLE = {
    2.0: 140,
    2.5: 140,
    3.0: 170,
    3.5: 200,
    4.0: 225,
    4.5: 255,
    5.0: 285,
    5.5: 310,
    6.0: 340,
    6.5: 370,
    7.0: 400,
    7.5: 430,
    8.0: 455,
    8.5: 485,
    9.0: 515,
    9.5: 545,
    10.0: 575,
    10.5: 600,
    11.0: 630,
    11.5: 660,
    12.0: 690,
    12.5: 720,
    13.0: 745,
    13.5: 775,
    14.0: 805,
    14.5: 835,
    15.0: 865,
    15.5: 890,
    16.0: 920,
    16.5: 950,
    17.0: 975,
    17.5: 1005,
    18.0: 1035,
    18.5: 1060,
    19.0: 1090,
    19.5: 1120,
    20.0: 1150,
}


def round_volume_up(volume: float) -> float:
    """Round volume UP to nearest 0.5 yd³."""
    return math.ceil(volume * 2) / 2


def get_price(volume: float) -> int:
    """
    Get price for a given volume.
    Rounds UP to nearest 0.5, then looks up in table.
    """
    rounded = round_volume_up(volume)
    
    # Handle edge cases
    if rounded < 2.0:
        return PRICE_TABLE[2.0]  # Minimum price
    
    if rounded > 20.0:
        return PRICE_TABLE[20.0]  # Maximum price
    
    # Direct lookup
    if rounded in PRICE_TABLE:
        return PRICE_TABLE[rounded]
    
    # Fallback: find nearest key
    keys = sorted(PRICE_TABLE.keys())
    for k in keys:
        if k >= rounded:
            return PRICE_TABLE[k]
    
    return PRICE_TABLE[20.0]


def volume_to_price(volume: float) -> Tuple[int, int, int]:
    """
    Convert volume to price with ±15% range.
    
    Returns: (min_price, base_price, max_price)
    """
    base = get_price(volume)
    
    min_price = round(base * 0.85)
    max_price = round(base * 1.15)
    
    return min_price, base, max_price


# Quick test
if __name__ == "__main__":
    test_volumes = [1.0, 2.3, 3.0, 4.2, 5.0, 7.5, 10.0, 15.0, 20.0, 25.0]
    for v in test_volumes:
        rounded = round_volume_up(v)
        min_p, base_p, max_p = volume_to_price(v)
        print(f"Volume: {v} yd³ → Rounded: {rounded} yd³ → Price: ${min_p}-${max_p} (base: ${base_p})")
