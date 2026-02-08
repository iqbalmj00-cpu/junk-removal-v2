import { google } from 'googleapis';
import { NextResponse } from 'next/server';

export async function POST(req: Request) {
    try {
        const body = await req.json();
        const { firstName, lastName, email, phone, quoteMin, quoteMax, volume } = body;

        // Validate required fields
        if (!firstName || !lastName || !email || !phone) {
            return NextResponse.json(
                { success: false, error: 'Missing required fields' },
                { status: 400 }
            );
        }

        // --- ROBUST KEY CLEANER ---
        let privateKey = process.env.GOOGLE_PRIVATE_KEY || "";
        if (privateKey.startsWith('"') && privateKey.endsWith('"')) {
            privateKey = privateKey.substring(1, privateKey.length - 1);
        }
        if (privateKey.startsWith("'") && privateKey.endsWith("'")) {
            privateKey = privateKey.substring(1, privateKey.length - 1);
        }
        privateKey = privateKey.replace(/\\n/g, '\n');
        privateKey = privateKey.trim();

        // Authenticate with Google
        const auth = new google.auth.GoogleAuth({
            credentials: {
                client_email: process.env.GOOGLE_SERVICE_ACCOUNT_EMAIL,
                private_key: privateKey,
            },
            scopes: ['https://www.googleapis.com/auth/spreadsheets'],
        });

        const sheets = google.sheets({ version: 'v4', auth });
        const sheetId = process.env.GOOGLE_SHEET_ID;

        if (!sheetId) {
            console.error('Missing GOOGLE_SHEET_ID');
            return NextResponse.json(
                { success: false, error: 'Sheet not configured' },
                { status: 500 }
            );
        }

        // Generate Lead ID: #LD-XXXX-X
        const randomDigits = Math.floor(1000 + Math.random() * 9000);
        const randomLetter = String.fromCharCode(65 + Math.floor(Math.random() * 26));
        const leadId = `#LD-${randomDigits}-${randomLetter}`;

        // Determine status based on whether quote data is present
        const status = quoteMin ? 'Quoted' : 'New Lead';

        // Format quote range if present
        const quoteRange = quoteMin && quoteMax ? `$${quoteMin} - $${quoteMax}` : '';

        // Append to "Leads" sheet tab
        await sheets.spreadsheets.values.append({
            spreadsheetId: sheetId,
            range: 'Leads!A:I',
            valueInputOption: 'USER_ENTERED',
            requestBody: {
                values: [
                    [
                        leadId,
                        new Date().toISOString(),
                        `${firstName} ${lastName}`,
                        phone,
                        email,
                        status,
                        quoteRange,
                        volume ? `${volume} yd³` : '',
                        '', // Notes column (reserved)
                    ],
                ],
            },
        });

        console.log(`✅ Lead ${leadId} saved: ${firstName} ${lastName} (${status})`);

        return NextResponse.json({
            success: true,
            leadId,
            message: 'Lead captured successfully',
        });

    } catch (error: any) {
        console.error('❌ Lead capture error:', error);
        return NextResponse.json(
            { success: false, error: 'Failed to save lead', details: error.message },
            { status: 500 }
        );
    }
}
