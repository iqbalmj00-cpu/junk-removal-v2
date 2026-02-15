import { NextResponse } from 'next/server';

/**
 * POST /api/crm
 *
 * Server-side proxy for the ScaleYourJunk CRM.
 * Hides API credentials from the client bundle.
 *
 * Expects JSON body: { name, phone, email?, address, description?, image_urls[], website_honeypot }
 */
export async function POST(req: Request) {
    try {
        const body = await req.json();

        // --- Honeypot check (server-side defense) ---
        if (body.website_honeypot && body.website_honeypot.length > 0) {
            console.warn('🤖 Honeypot triggered — rejecting spam submission');
            // Return 200 to not tip off bots, but don't forward
            return NextResponse.json({ success: true, leadId: 'blocked', deduplicated: false });
        }

        // --- Credentials ---
        const apiKey = process.env.INGEST_API_KEY;
        const siteToken = process.env.SITE_TOKEN || process.env.DASHBOARD_SITE_TOKEN;
        const dashboardUrl = process.env.DASHBOARD_URL;
        const crmEndpoint = `${dashboardUrl}/api/ingest/website`;

        console.log('[CRM] === Incoming Request ===');
        console.log('[CRM] Env INGEST_API_KEY:', apiKey ? `SET (${apiKey.length} chars)` : '❌ NOT SET');
        console.log('[CRM] Env SITE_TOKEN:', siteToken ? `SET (${siteToken.length} chars)` : '❌ NOT SET');
        console.log('[CRM] Env DASHBOARD_URL:', dashboardUrl || '❌ NOT SET');

        if (!apiKey || !siteToken || !dashboardUrl) {
            console.error('❌ CRM credentials not configured');
            return NextResponse.json(
                { success: false, error: 'CRM credentials not configured (missing INGEST_API_KEY, SITE_TOKEN, or DASHBOARD_URL)' },
                { status: 500 }
            );
        }

        // --- Build CRM payload (exact schema required) ---
        const payload: Record<string, any> = {
            name: body.name || '',
            phone: body.phone || '',
            email: body.email || '',
            address: body.address || '',
            description: body.description || '',
            source: 'WEBSITE',
            image_urls: body.image_urls || [],
            website_honeypot: '',  // Always empty (we already checked above)
        };
        if (body.requestedDate) payload.requestedDate = body.requestedDate;
        if (body.leadId) payload.leadId = body.leadId;

        console.log('[CRM] Payload:', JSON.stringify(payload));

        // --- Forward to CRM ---
        const response = await fetch(crmEndpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'x-api-key': apiKey,
                'x-site-token': siteToken,
            },
            body: JSON.stringify(payload),
        });

        const responseText = await response.text();
        console.log(`[CRM] Response status: ${response.status}`);
        console.log(`[CRM] Response body: ${responseText}`);

        let data: any;
        try { data = JSON.parse(responseText); } catch { data = { raw: responseText }; }

        if (!response.ok) {
            console.error(`❌ CRM rejected request (${response.status}):`, data);
            return NextResponse.json(
                { success: false, error: data.error || 'CRM submission failed' },
                { status: response.status }
            );
        }

        console.log(`✅ CRM lead created: ${data.leadId || 'unknown'}`);
        return NextResponse.json({
            success: true,
            leadId: data.leadId,
            deduplicated: data.deduplicated || false,
        });
    } catch (error: any) {
        console.error('❌ CRM proxy error:', error);
        return NextResponse.json(
            { success: false, error: 'Failed to submit to CRM', details: error.message },
            { status: 500 }
        );
    }
}
