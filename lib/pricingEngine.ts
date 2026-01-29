export interface SurchargeItem {
    name: string;
    price: number;
}

export interface PriceBreakdown {
    basePrice: number;
    tierName: string;
    surcharges: SurchargeItem[];
    totalPrice: number;
}

export interface VolumeTier {
    maxCuFt: number;
    price: number;
    label: string;
}

// v2.9: Anchor-based piecewise linear pricing
// Legacy VOLUME_TIERS for backward compatibility
const VOLUME_TIERS: VolumeTier[] = [
    { maxCuFt: 67.5, price: 135, label: 'Minimum' },       // 0.0 - 2.5 yd³
    { maxCuFt: 108, price: 228, label: '1/4 Load' },       // 2.5 - 4.0 yd³
    { maxCuFt: 189, price: 401, label: '1/2 Load' },       // 4.0 - 7.0 yd³
    { maxCuFt: 324, price: 691, label: '3/4 Load' },       // 7.0 - 12.0 yd³
    { maxCuFt: 540, price: 1150, label: 'Full Load' },     // 12.0 - 20.0 yd³
];

const PRICE_CEILING = 1150;

/**
 * v3.0: 10-tier piecewise linear pricing.
 * 
 * Rounds volume to nearest 0.5 yd³, then linearly interpolates between anchors.
 * 
 * Tiers:
 * - 0.0-2.5 yd³:   $135.00 → $142.50
 * - 2.5-4.0 yd³:   $142.50 → $228.00
 * - 4.0-5.0 yd³:   $228.00 → $285.00
 * - 5.0-7.0 yd³:   $285.00 → $401.00
 * - 7.0-10.0 yd³:  $401.00 → $575.00
 * - 10.0-12.0 yd³: $575.00 → $691.00
 * - 12.0-14.0 yd³: $691.00 → $807.00
 * - 14.0-15.0 yd³: $807.00 → $865.00
 * - 15.0-17.0 yd³: $865.00 → $979.00
 * - 17.0-20.0 yd³: $979.00 → $1,150.00
 * - >20.0 yd³:     Cap at $1,150, flag for manual review
 */
function calcPriceLinear(volumeYards: number): { price: number; label: string; needsReview: boolean } {
    // Round to nearest 0.5
    const roundedVol = Math.round(volumeYards * 2) / 2;

    // Cap at 20.0 yd³
    if (roundedVol > 20.0) {
        return { price: PRICE_CEILING, label: 'Full Load (Review)', needsReview: true };
    }

    // Define anchor segments: [min_vol, max_vol, min_price, max_price, label]
    const segments: [number, number, number, number, string][] = [
        [0.0, 2.5, 135, 142.50, 'Minimum'],
        [2.5, 4.0, 142.50, 228, '1/4 Load'],
        [4.0, 5.0, 228, 285, '1/4+ Load'],
        [5.0, 7.0, 285, 401, '1/3 Load'],
        [7.0, 10.0, 401, 575, '1/2 Load'],
        [10.0, 12.0, 575, 691, '1/2+ Load'],
        [12.0, 14.0, 691, 807, '3/4 Load'],
        [14.0, 15.0, 807, 865, '3/4+ Load'],
        [15.0, 17.0, 865, 979, 'Near Full'],
        [17.0, 20.0, 979, 1150, 'Full Load'],
    ];

    for (const [minVol, maxVol, minPrice, maxPrice, label] of segments) {
        if (roundedVol <= maxVol) {
            if (roundedVol <= minVol) {
                return { price: minPrice, label, needsReview: false };
            }
            // Linear interpolation
            const ratio = (roundedVol - minVol) / (maxVol - minVol);
            const price = minPrice + ratio * (maxPrice - minPrice);
            return { price: Math.round(price), label, needsReview: false };
        }
    }

    // Fallback (shouldn't reach here)
    return { price: PRICE_CEILING, label: 'Full Load', needsReview: false };
}

export function calculateJunkPrice(cubicFeet: number, surcharges: SurchargeItem[]): PriceBreakdown {
    // Convert cuft to yards
    const volumeYards = cubicFeet / 27;

    // Use linear pricing
    const { price: basePrice, label: tierName } = calcPriceLinear(volumeYards);

    if (cubicFeet === 0) {
        return {
            basePrice: 0,
            tierName: 'Empty',
            surcharges: surcharges,
            totalPrice: 0
        };
    }

    // Sum Surcharges
    const surchargeTotal = surcharges.reduce((sum, item) => sum + item.price, 0);

    // Total
    const total = basePrice + surchargeTotal;

    return {
        basePrice: basePrice,
        tierName: tierName,
        surcharges: surcharges,
        totalPrice: total
    };
}
