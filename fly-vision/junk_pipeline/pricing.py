"""
Pricing Engine for Junk Removal Volume Quotes

Converts volume (yd³) to price using:
1. Round volume UP to nearest 0.5 yd³  
2. Interpolate price within tiered bands
3. Apply ±15% range for min/max price
"""

import math
from typing import Tuple

# Price bands: (Vmin, Vmax, Pmin, Pmax)
PRICE_BANDS = [
    (0.0, 2.5, 135, 142.5),
    (2.5, 4.0, 142.5, 228),
    (4.0, 5.0, 228, 285),
    (5.0, 7.0, 285, 401),
    (7.0, 10.0, 401, 575),
    (10.0, 12.0, 575, 691),
    (12.0, 14.0, 691, 807),
    (14.0, 15.0, 807, 865),
    (15.0, 17.0, 865, 979),
    (17.0, 20.0, 979, 1150),
]


def round_volume_up(volume: float) -> float:
    """Round volume UP to nearest 0.5 yd³."""
    return math.ceil(volume * 2) / 2


def get_base_price(volume: float) -> float:
    """
    Get base price by linear interpolation within the appropriate band.
    
    P(V) = Pmin + ((V - Vmin) / (Vmax - Vmin)) * (Pmax - Pmin)
    """
    # Round volume first
    v = round_volume_up(volume)
    
    # Handle edge cases
    if v <= 0:
        return PRICE_BANDS[0][2]  # Return minimum price
    
    if v >= PRICE_BANDS[-1][1]:  # Above max band
        return PRICE_BANDS[-1][3]  # Return maximum price
    
    # Find the appropriate band
    for vmin, vmax, pmin, pmax in PRICE_BANDS:
        if vmin <= v < vmax:
            # Linear interpolation
            ratio = (v - vmin) / (vmax - vmin)
            return pmin + ratio * (pmax - pmin)
    
    # Fallback: use last band
    return PRICE_BANDS[-1][3]


def volume_to_price(volume: float) -> Tuple[float, float, float]:
    """
    Convert volume to price with ±15% range.
    
    Returns: (min_price, base_price, max_price) - all rounded to whole dollars
    """
    base = get_base_price(volume)
    
    min_price = round(base * 0.85)
    max_price = round(base * 1.15)
    base_price = round(base)
    
    return min_price, base_price, max_price


# Quick test
if __name__ == "__main__":
    test_volumes = [0.5, 1.0, 2.0, 3.0, 5.0, 8.0, 12.0, 15.0, 20.0]
    for v in test_volumes:
        rounded = round_volume_up(v)
        min_p, base_p, max_p = volume_to_price(v)
        print(f"Volume: {v} yd³ → Rounded: {rounded} yd³ → Price: ${min_p}-${max_p} (base: ${base_p})")
