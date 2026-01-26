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
    { maxCuFt: 135, price: 285, label: '1/4 Load' },       // 2.5 - 5.0 yd³
    { maxCuFt: 270, price: 575, label: '1/2 Load' },       // 5.0 - 10.0 yd³
    { maxCuFt: 405, price: 865, label: '3/4 Load' },       // 10.0 - 15.0 yd³
    { maxCuFt: 540, price: 1150, label: 'Full Load' },     // 15.0 - 20.0 yd³
];

const PRICE_CEILING = 1150;

/**
 * v2.9: Anchor-based piecewise linear pricing.
 * 
 * Rounds volume to nearest 0.5 yd³, then linearly interpolates between anchors.
 * 
 * Anchors:
 * - 0.0-2.5 yd³: $135 flat (minimum)
 * - 2.5-5.0 yd³: $135 → $285 (+$30 per 0.5)
 * - 5.0-10.0 yd³: $285 → $575 (+$29 per 0.5)
 * - 10.0-15.0 yd³: $575 → $865 (+$29 per 0.5)
 * - 15.0-20.0 yd³: $865 → $1,150 (+$28.50 per 0.5)
 * - >20.0 yd³: Cap at $1,150, flag for manual review
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
        [0.0, 2.5, 135, 135, 'Minimum'],        // Flat minimum
        [2.5, 5.0, 135, 285, '1/4 Load'],       // +$30 per 0.5
        [5.0, 10.0, 285, 575, '1/2 Load'],      // +$29 per 0.5
        [10.0, 15.0, 575, 865, '3/4 Load'],     // +$29 per 0.5
        [15.0, 20.0, 865, 1150, 'Full Load'],   // +$28.50 per 0.5
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
