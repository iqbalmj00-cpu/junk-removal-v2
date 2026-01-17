import { GoogleGenerativeAI } from "@google/generative-ai";
import { NextResponse } from "next/server";
import { calculateJunkPrice } from "@/lib/pricingEngine"; // Assuming this is available, otherwise we use standard pricing map

// 1. TIMEOUT CONFIGURATION
export const runtime = "nodejs";
export const maxDuration = 120;

export async function POST(req: Request) {
    try {
        const { images } = await req.json();
        console.log(`Starting Dual-Model Analysis on ${images.length} images...`);

        if (!process.env.GEMINI_API_KEY) {
            return NextResponse.json({ valid: false, reason: "Server Error: Missing API Key" }, { status: 500 });
        }

        // 2. Clean Images
        const processedImages = images.map((img: string) => ({
            inlineData: {
                data: img.includes(',') ? img.split(',')[1] : img,
                mimeType: "image/jpeg",
            },
        }));

        const genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY);

        // 3. The "Surveyor" System Prompt
        const systemPrompt = `
You are a Spatial Surveyor for a Junk Removal tool.
Your ONLY job is to estimate the bounding box dimensions of the junk pile in the image.
DO NOT calculate volume. DO NOT do any math.

### STEP 1: CALIBRATION
- Identify a visual anchor (e.g., Door frame = 80", Wheelie Bin = 42") to establish scale.
- If no anchor is found, use standard ground texture sizes.

### STEP 2: MEASUREMENT
Imagine a rectangular box that creates a *tight fit* around the junk pile.
Estimate the following in DECIMAL FEET:
1. Length (Longest side on ground)
2. Width (Depth from front to back)
3. Height (Average vertical height)

### STEP 3: DENSITY FACTOR (Crucial)
Estimate the "Solidity" of the pile (0.0 to 1.0).
- 1.0 = Solid block (e.g., Concrete, loaded pallet).
- 0.8 = Efficiently stacked boxes.
- 0.5 = Loose/Messy pile (Furniture, bicycles, lots of air gaps).

### OUTPUT FORMAT (JSON ONLY):
{
  "anchor_used": "String",
  "dimensions_ft": {
      "length": Float,
      "width": Float,
      "height": Float
  },
  "density_factor": Float
}
`;

        // 4. Parallel Execution (Model A & Model B)
        console.log("Launching Parallel Models...");
        const modelA = genAI.getGenerativeModel({ model: "gemini-1.5-pro" });
        const modelB = genAI.getGenerativeModel({ model: "gemini-1.5-flash" });

        const [resultA, resultB] = await Promise.all([
            modelA.generateContent([systemPrompt, ...processedImages]).catch(e => ({ error: e })),
            modelB.generateContent([systemPrompt, ...processedImages]).catch(e => ({ error: e }))
        ]);

        // Helper to parse JSON
        const parseResponse = (result: any) => {
            if (result.error) return null;
            try {
                const text = result.response.text();
                const cleanJson = text.replace(/```json|```/g, "").trim();
                return JSON.parse(cleanJson);
            } catch (e) {
                console.error("JSON Parse Error:", e);
                return null;
            }
        };

        const jsonA = parseResponse(resultA);
        const jsonB = parseResponse(resultB);

        // Fallback Logic: If both fail, trigger Manual Review immediately.
        if (!jsonA && !jsonB) {
            return NextResponse.json({ status: "FAIL", reason: "AI Blindness" });
        }

        // If one fails, use the other (soft consensus)
        if (!jsonA && jsonB) return processSingleResult(jsonB);
        if (jsonA && !jsonB) return processSingleResult(jsonA);

        // 5. Consensus Calculation
        return calculateConsensus(jsonA, jsonB);

    } catch (error) {
        console.error("Critical Failure:", error);
        return NextResponse.json({ status: "FAIL", reason: "Critical Error" });
    }
}

// --- Logic Engine ---

function calculateConsensus(modelA: any, modelB: any) {
    // 1. Calculate Volume A
    const dimA = modelA.dimensions_ft;
    const volA_ft = dimA.length * dimA.width * dimA.height;
    const volA_yards = (volA_ft * modelA.density_factor) / 27.0;

    // 2. Calculate Volume B
    const dimB = modelB.dimensions_ft;
    const volB_ft = dimB.length * dimB.width * dimB.height;
    const volB_yards = (volB_ft * modelB.density_factor) / 27.0;

    console.log(`Model A Volume: ${volA_yards.toFixed(2)} yds`);
    console.log(`Model B Volume: ${volB_yards.toFixed(2)} yds`);

    // 3. Consensus Check (15% Variance)
    const diff = Math.abs(volA_yards - volB_yards);
    const average_vol = (volA_yards + volB_yards) / 2;
    const percent_diff = average_vol > 0 ? (diff / average_vol) : 0;

    if (percent_diff > 0.15) {
        console.warn(`Consensus Failed: ${percent_diff.toFixed(2)} variance`);
        return NextResponse.json({
            status: "FAIL",
            reason: "High Variance",
            details: { vol_a: volA_yards, vol_b: volB_yards }
        });
    }

    // 4. PASS: Return Average
    const finalVolume = Math.ceil(average_vol * 10) / 10; // Round to 1 decimal place
    const finalPrice = determinePrice(finalVolume);

    return NextResponse.json({
        valid: true, // Legacy flag for frontend
        status: "PASS",
        volume: `${finalVolume.toFixed(1)} yds³`,
        price: finalPrice,
        load_size: getLoadSize(finalVolume),
        reasoning: `Consensus Reached. Model A (${volA_yards.toFixed(1)} yds) and Model B (${volB_yards.toFixed(1)} yds) agree.`
    });
}

function processSingleResult(modelJson: any) {
    console.warn("Single Model Fallback Triggered");
    const dim = modelJson.dimensions_ft;
    const vol_ft = dim.length * dim.width * dim.height;
    const vol_yards = (vol_ft * modelJson.density_factor) / 27.0;

    const finalVolume = Math.ceil(vol_yards * 10) / 10;
    const finalPrice = determinePrice(finalVolume);

    return NextResponse.json({
        valid: true,
        status: "PASS",
        volume: `${finalVolume.toFixed(1)} yds³`,
        price: finalPrice,
        load_size: getLoadSize(finalVolume),
        reasoning: "Single Model Estimate (Consensus Bypassed)"
    });
}

function getLoadSize(yards: number): string {
    if (yards <= 2) return "Min Load";
    if (yards <= 4) return "1/4 Truck";
    if (yards <= 8) return "1/2 Truck";
    if (yards < 12) return "3/4 Truck";
    return "Full Truck";
}

function determinePrice(yards: number): string {
    if (yards <= 2) return "$129 - $159";
    if (yards <= 3) return "$169 - $199";
    if (yards <= 4) return "$229 - $269";
    if (yards <= 8) return "$349 - $449";
    return "$599+";
}
