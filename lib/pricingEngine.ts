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

const VOLUME_TIERS: VolumeTier[] = [
    { maxCuFt: 13.5, price: 135, label: 'Minimum' },       // 0.0 - 0.5 yd³
    { maxCuFt: 67.5, price: 255, label: '1/4 Load' },      // 0.5 - 2.5 yd³
    { maxCuFt: 135, price: 285, label: 'Half Load' },      // 2.5 - 5.0 yd³
    { maxCuFt: 202.5, price: 430, label: '5/8 Load' },     // 5.0 - 7.5 yd³
    { maxCuFt: 270, price: 575, label: '3/4 Load' },       // 7.5 - 10.0 yd³
    { maxCuFt: 337.5, price: 720, label: '7/8 Load' },     // 10.0 - 12.5 yd³
    { maxCuFt: 405, price: 865, label: 'Full Load' },      // 12.5 - 15.0 yd³
    { maxCuFt: 472.5, price: 1007, label: 'Oversize' },    // 15.0 - 17.5 yd³
    { maxCuFt: 540, price: 1150, label: 'Max Load' },      // 17.5 - 20.0 yd³
];

export function calculateJunkPrice(cubicFeet: number, surcharges: SurchargeItem[]): PriceBreakdown {
    // 1. Find Volume Tier
    // Default to the largest if exceeding all ranges (though 9999 covers most)
    let tier = VOLUME_TIERS.find(t => cubicFeet <= t.maxCuFt) || VOLUME_TIERS[VOLUME_TIERS.length - 1];

    if (cubicFeet === 0) {
        tier = { maxCuFt: 0, price: 0, label: 'Empty' };
    }

    // 2. Sum Surcharges
    const surchargeTotal = surcharges.reduce((sum, item) => sum + item.price, 0);

    // 3. Total
    const total = tier.price + surchargeTotal;

    return {
        basePrice: tier.price,
        tierName: tier.label,
        surcharges: surcharges,
        totalPrice: total
    };
}
