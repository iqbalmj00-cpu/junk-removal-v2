import { NextResponse } from 'next/server';

/**
 * GET /api/crm/test
 *
 * Diagnostic endpoint to test CRM connectivity.
 * Hit this URL in your browser to verify:
 *   1. Env vars are loaded
 *   2. CRM endpoint is reachable
 *   3. Credentials are accepted
 *
 * DELETE THIS FILE after debugging is complete.
 */
export async function GET() {
    const apiKey = process.env.INGEST_API_KEY;
    const siteToken = process.env.SITE_TOKEN || process.env.DASHBOARD_SITE_TOKEN;
    const dashboardUrl = process.env.DASHBOARD_URL;
    const crmEndpoint = `${dashboardUrl}/api/ingest/website`;
    const diagnostics: Record<string, any> = {
        timestamp: new Date().toISOString(),
        env_INGEST_API_KEY: apiKey ? `SET (${apiKey.length} chars, starts: ${apiKey.substring(0, 6)}...)` : '❌ NOT SET',
        env_SITE_TOKEN: siteToken ? `SET (${siteToken.length} chars, starts: ${siteToken.substring(0, 6)}...)` : '❌ NOT SET',
        env_DASHBOARD_URL: dashboardUrl || '❌ NOT SET',
        env_checked: 'SITE_TOKEN, DASHBOARD_SITE_TOKEN, DASHBOARD_URL',
        crmEndpoint,
        testPayload: {
            name: 'CRM Test Lead',
            phone: '000-000-0000',
            email: 'test@diagnostics.dev',
            description: 'Automated diagnostic test — safe to delete',
            website_honeypot: '',
        },
    };

    if (!apiKey || !siteToken || !dashboardUrl) {
        diagnostics.result = '❌ FAILED: Missing environment variables';
        return NextResponse.json(diagnostics, { status: 500 });
    }

    // Actually try to send a test lead
    try {
        const response = await fetch(crmEndpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'x-api-key': apiKey,
                'x-site-token': siteToken,
            },
            body: JSON.stringify(diagnostics.testPayload),
        });

        const responseText = await response.text();
        let responseData: any;
        try {
            responseData = JSON.parse(responseText);
        } catch {
            responseData = responseText;
        }

        diagnostics.crmResponse = {
            status: response.status,
            statusText: response.statusText,
            headers: Object.fromEntries(response.headers.entries()),
            body: responseData,
        };

        if (response.ok) {
            diagnostics.result = '✅ SUCCESS: CRM accepted the test lead';
        } else {
            diagnostics.result = `❌ FAILED: CRM returned ${response.status}`;
        }
    } catch (error: any) {
        diagnostics.result = `❌ FAILED: Network error`;
        diagnostics.error = {
            message: error.message,
            cause: error.cause?.message || null,
        };
    }

    return NextResponse.json(diagnostics, { status: 200 });
}
