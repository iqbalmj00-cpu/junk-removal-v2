import { NextResponse } from 'next/server';

/**
 * POST /api/track/quote
 *
 * Server-side proxy that forwards quote data to the dashboard.
 */
export async function POST(req: Request) {
    try {
        const dashboardUrl = process.env.DASHBOARD_URL;
        const apiKey = process.env.DASHBOARD_API_KEY;
        const siteToken = process.env.DASHBOARD_SITE_TOKEN;

        if (!dashboardUrl || !apiKey || !siteToken) {
            return NextResponse.json({ success: true, skipped: true });
        }

        const body = await req.json();

        const response = await fetch(`${dashboardUrl}/api/ingest/quote`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'x-api-key': apiKey,
                'x-site-token': siteToken,
            },
            body: JSON.stringify({
                customerName: body.customerName,
                customerEmail: body.customerEmail,
                customerPhone: body.customerPhone,
                estimatedVolume: body.estimatedVolume,
                price: body.price,
                confidence: body.confidence,
                itemList: body.itemList || [],
                imageCount: body.imageCount || 0,
                timestamp: new Date().toISOString(),
            }),
        });

        if (!response.ok) {
            console.error(`[Quote Proxy] Dashboard returned ${response.status}`);
        }

        return NextResponse.json({ success: true });

    } catch (error: any) {
        console.error('[Quote Proxy] Error:', error.message);
        return NextResponse.json({ success: true, error: error.message });
    }
}
