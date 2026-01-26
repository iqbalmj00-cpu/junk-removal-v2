import { NextRequest, NextResponse } from 'next/server';

// Fly.io endpoint
const FLY_ENDPOINT = process.env.FLY_VISION_URL || 'https://jamals-junk-vision.fly.dev';
const INTERNAL_TOKEN = process.env.INTERNAL_TOKEN || 'dev-token-change-me';

// Timeout for pipeline (3 minutes)
const TIMEOUT_MS = 180_000;

export async function POST(request: NextRequest) {
    const startTime = Date.now();

    try {
        const body = await request.json();
        const images = body.images || [];

        // Validate
        if (!images.length) {
            return NextResponse.json(
                { error: 'No images provided' },
                { status: 400 }
            );
        }

        if (images.length > 10) {
            return NextResponse.json(
                { error: 'Max 10 images allowed' },
                { status: 400 }
            );
        }

        console.log(`📥 Proxying ${images.length} images to Fly.io...`);

        // Format for Fly endpoint
        const flyPayload = {
            images: images.map((img: string, i: number) => ({
                id: `img_${i}`,
                b64: img,
                mime: 'image/jpeg'
            })),
            context: {
                mode: body.mode || 'pile',
                debug: body.debug || false
            }
        };

        // Call Fly.io with timeout
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), TIMEOUT_MS);

        try {
            const response = await fetch(`${FLY_ENDPOINT}/process`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Internal-Token': INTERNAL_TOKEN,
                },
                body: JSON.stringify(flyPayload),
                signal: controller.signal,
            });

            clearTimeout(timeoutId);

            if (!response.ok) {
                const errorText = await response.text();
                console.error(`❌ Fly returned ${response.status}: ${errorText}`);

                // Retry once on 5xx
                if (response.status >= 500) {
                    console.log('🔄 Retrying once...');
                    const retryResponse = await fetch(`${FLY_ENDPOINT}/process`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-Internal-Token': INTERNAL_TOKEN,
                        },
                        body: JSON.stringify(flyPayload),
                    });

                    if (retryResponse.ok) {
                        const result = await retryResponse.json();
                        const elapsed = Date.now() - startTime;
                        console.log(`✅ Retry succeeded in ${elapsed}ms`);
                        return NextResponse.json(result.quote || result);
                    }
                }

                return NextResponse.json(
                    { error: 'Vision service unavailable', details: errorText },
                    { status: response.status }
                );
            }

            const result = await response.json();
            const elapsed = Date.now() - startTime;
            console.log(`✅ Quote complete in ${elapsed}ms`);

            // Return just the quote (not debug unless requested)
            return NextResponse.json(result.quote || result);

        } catch (fetchError: any) {
            clearTimeout(timeoutId);

            if (fetchError.name === 'AbortError') {
                console.error('⏱️ Request timed out');
                return NextResponse.json(
                    { error: 'Request timed out' },
                    { status: 504 }
                );
            }
            throw fetchError;
        }

    } catch (error: any) {
        console.error('❌ Proxy error:', error);
        return NextResponse.json(
            { error: 'Internal server error', message: error.message },
            { status: 500 }
        );
    }
}

export const config = {
    api: {
        bodyParser: {
            sizeLimit: '50mb', // Allow large base64 payloads
        },
    },
};
