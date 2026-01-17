export interface Dimensions {
    length: number;
    width: number;
    height: number;
}

export interface SurveyorOutput {
    anchor_used: string;
    dimensions_ft: Dimensions;
    density_factor: number;
}

export interface ConsensusResult {
    status: 'PASS' | 'FAIL';
    final_volume_yards?: number;
    reason?: string;
    vol_a?: number;
    vol_b?: number;
}

export function calculateConsensusVolume(
    modelA: SurveyorOutput,
    modelB: SurveyorOutput
): ConsensusResult {
    // 1. Calculate Volume A
    const dimA = modelA.dimensions_ft;
    const volACubicFt = dimA.length * dimA.width * dimA.height;
    const volAYards = (volACubicFt * modelA.density_factor) / 27.0;

    // 2. Calculate Volume B
    const dimB = modelB.dimensions_ft;
    const volBCubicFt = dimB.length * dimB.width * dimB.height;
    const volBYards = (volBCubicFt * modelB.density_factor) / 27.0;

    // 3. The Consensus Check
    const diff = Math.abs(volAYards - volBYards);
    const averageVol = (volAYards + volBYards) / 2;

    // Avoid division by zero
    const percentDiff = averageVol > 0 ? diff / averageVol : 0;

    if (percentDiff > 0.15) {
        // FAIL: The models disagree significantly (high variance)
        return {
            status: 'FAIL',
            reason: 'High Variance',
            vol_a: Number(volAYards.toFixed(2)),
            vol_b: Number(volBYards.toFixed(2)),
        };
    } else {
        // PASS: The models agree. Return the AVERAGE.
        return {
            status: 'PASS',
            final_volume_yards: Number(averageVol.toFixed(2)),
        };
    }
}
