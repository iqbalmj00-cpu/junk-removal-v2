import { NextResponse } from 'next/server';

/**
 * POST /api/track
 *
 * Server-side proxy that forwards website events to the dashboard.
 * Keeps DASHBOARD_API_KEY and DASHBOARD_SITE_TOKEN hidden from the browser.
 */
export async function POST(req: Request) {
    try {
        const dashboardUrl = process.env.DASHBOARD_URL;
        const apiKey = process.env.DASHBOARD_API_KEY;
        const siteToken = process.env.DASHBOARD_SITE_TOKEN;

        if (!dashboardUrl || !apiKey || !siteToken) {
            // Dashboard not configured — silently succeed
            return NextResponse.json({ success: true, skipped: true });
        }

        const body = await req.json();

        const response = await fetch(`${dashboardUrl}/api/ingest/website-event`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'x-api-key': apiKey,
                'x-site-token': siteToken,
            },
            body: JSON.stringify({
                eventType: body.eventType,
                page: body.page,
                metadata: body.metadata || {},
                timestamp: new Date().toISOString(),
            }),
        });

        if (!response.ok) {
            console.error(`[Track Proxy] Dashboard returned ${response.status}`);
        }

        return NextResponse.json({ success: true });

    } catch (error: any) {
        console.error('[Track Proxy] Error:', error.message);
        // Always return 200 — tracking failures should never break the app
        return NextResponse.json({ success: true, error: error.message });
    }
}
