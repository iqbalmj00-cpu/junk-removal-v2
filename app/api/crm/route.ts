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
        const siteToken = process.env.SITE_TOKEN;
        const crmEndpoint = 'https://app.scaleyourjunk.com/api/ingest/website';

        if (!apiKey || !siteToken) {
            console.error('❌ CRM credentials not configured');
            return NextResponse.json(
                { success: false, error: 'CRM credentials not configured' },
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

        const data = await response.json();

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
