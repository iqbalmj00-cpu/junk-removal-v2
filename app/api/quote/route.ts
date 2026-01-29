import { NextRequest, NextResponse } from 'next/server';

// Modal endpoint (GPU-accelerated)
const MODAL_ENDPOINT = process.env.MODAL_VISION_URL || 'https://iqbalmj00-cpu--junk-vision-process.modal.run';

// Timeout for pipeline (5 minutes for first cold start with model downloads)
const TIMEOUT_MS = 300_000;

export async function POST(request: NextRequest) {
    const startTime = Date.now();

    try {
        const body = await request.json();
        const images = body.images || [];

        // Validate
        if (!images.length) {
            return NextResponse.json(
                { status: 'ERROR', error: 'No images provided' },
                { status: 400 }
            );
        }

        if (images.length > 10) {
            return NextResponse.json(
                { status: 'ERROR', error: 'Max 10 images allowed' },
                { status: 400 }
            );
        }

        console.log(`📥 Proxying ${images.length} images to Modal...`);

        // Format for Modal endpoint
        const payload = {
            images: images.map((img: string, i: number) => ({
                id: `img_${i}`,
                b64: img,
                mime: 'image/jpeg'
            })),
        };

        // Call Modal with timeout
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), TIMEOUT_MS);

        try {
            const response = await fetch(MODAL_ENDPOINT, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(payload),
                signal: controller.signal,
            });

            clearTimeout(timeoutId);

            if (!response.ok) {
                const errorText = await response.text();
                console.error(`❌ Modal returned ${response.status}: ${errorText}`);

                // Retry once on 5xx
                if (response.status >= 500) {
                    console.log('🔄 Retrying once...');
                    const retryResponse = await fetch(MODAL_ENDPOINT, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify(payload),
                    });

                    if (retryResponse.ok) {
                        const result = await retryResponse.json();
                        const elapsed = Date.now() - startTime;
                        console.log(`✅ Retry succeeded in ${elapsed}ms`);

                        // Transform to frontend-expected format
                        const quote = result.quote || result;
                        return NextResponse.json({
                            status: 'SUCCESS',
                            volume_yards: quote.final_volume_cy || quote.final_volume || quote.volume || 0,
                            min_price: quote.min_price || 0,
                            max_price: quote.max_price || 0,
                            price: quote.final_volume_cy || quote.final_volume || 0,
                            confidence: quote.confidence_score || 0.5,
                            items: quote.line_items || quote.items || [],
                            flags: quote.flags || [],
                            audit: quote.audit || {}
                        });
                    }
                }

                return NextResponse.json(
                    { status: 'ERROR', error: 'Vision service unavailable', details: errorText },
                    { status: response.status }
                );
            }

            const result = await response.json();
            const elapsed = Date.now() - startTime;
            console.log(`✅ Quote complete in ${elapsed}ms`);

            // Transform Modal response to frontend-expected format
            const quote = result.quote || result;

            return NextResponse.json({
                status: 'SUCCESS',
                volume_yards: quote.final_volume_cy || quote.final_volume || quote.volume || 0,
                min_price: quote.min_price || 0,
                max_price: quote.max_price || 0,
                price: quote.final_volume_cy || quote.final_volume || 0,
                confidence: quote.confidence_score || 0.5,
                items: quote.line_items || quote.items || [],
                flags: quote.flags || [],
                audit: quote.audit || {}
            });

        } catch (fetchError: any) {
            clearTimeout(timeoutId);

            if (fetchError.name === 'AbortError') {
                console.error('⏱️ Request timed out');
                return NextResponse.json(
                    { status: 'TIMEOUT', error: 'Request timed out' },
                    { status: 504 }
                );
            }
            throw fetchError;
        }

    } catch (error: any) {
        console.error('❌ Proxy error:', error);
        return NextResponse.json(
            { status: 'ERROR', error: 'Internal server error', message: error.message },
            { status: 500 }
        );
    }
}

export const config = {
    api: {
        bodyParser: {
            sizeLimit: '50mb',
        },
    },
};
