import { NextResponse } from 'next/server';

/**
 * POST /api/track
 *
 * Server-side proxy that forwards tracking data to the dashboard.
 * Keeps DASHBOARD_API_KEY and DASHBOARD_SITE_TOKEN hidden from the browser.
 *
 * Body: { type: 'event' | 'lead' | 'quote', ...payload }
 */
export async function POST(req: Request) {
    try {
        const dashboardUrl = process.env.DASHBOARD_URL;
        const apiKey = process.env.INGEST_API_KEY;
        const siteToken = process.env.SITE_TOKEN;

        if (!dashboardUrl || !apiKey || !siteToken) {
            return NextResponse.json({ success: true, skipped: true });
        }

        const body = await req.json();
        const { type = 'event', ...payload } = body;

        const endpoints: Record<string, string> = {
            event: '/api/ingest/website-event',
            lead: '/api/ingest/lead',
            quote: '/api/ingest/quote',
        };

        const endpoint = endpoints[type] || endpoints.event;

        const response = await fetch(`${dashboardUrl}${endpoint}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'x-api-key': apiKey,
                'x-site-token': siteToken,
            },
            body: JSON.stringify({
                ...payload,
                timestamp: new Date().toISOString(),
            }),
        });

        if (!response.ok) {
            console.error(`[Track Proxy] Dashboard ${endpoint} returned ${response.status}`);
        }

        return NextResponse.json({ success: true });

    } catch (error: any) {
        console.error('[Track Proxy] Error:', error.message);
        return NextResponse.json({ success: true, error: error.message });
    }
}
