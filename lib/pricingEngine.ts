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
    { maxCuFt: 60, price: 99, label: 'Min Load' },
    { maxCuFt: 80, price: 129, label: '1/6 Load' },
    { maxCuFt: 120, price: 149, label: '1/4 Load' },
    { maxCuFt: 180, price: 199, label: '3/8 Load' },
    { maxCuFt: 240, price: 299, label: 'Half Load' },
    { maxCuFt: 300, price: 329, label: '5/8 Load' },
    { maxCuFt: 360, price: 379, label: '3/4 Load' },
    { maxCuFt: 420, price: 435, label: '7/8 Load' },
    { maxCuFt: 480, price: 549, label: 'Full Load' }, // Approx 480 cu ft for 12ft truck
    { maxCuFt: 9999, price: 599, label: 'Overload' },
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
