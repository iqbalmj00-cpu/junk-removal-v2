import { google } from 'googleapis';
import { NextResponse } from 'next/server';

function getAuthAndSheets() {
    const clientEmail = process.env.GOOGLE_SERVICE_ACCOUNT_EMAIL;
    let privateKey = process.env.GOOGLE_PRIVATE_KEY || '';

    if (privateKey.startsWith('"') && privateKey.endsWith('"')) {
        privateKey = privateKey.substring(1, privateKey.length - 1);
    }
    if (privateKey.startsWith("'") && privateKey.endsWith("'")) {
        privateKey = privateKey.substring(1, privateKey.length - 1);
    }
    privateKey = privateKey.replace(/\\n/g, '\n').trim();

    const auth = new google.auth.GoogleAuth({
        credentials: { client_email: clientEmail, private_key: privateKey },
        scopes: ['https://www.googleapis.com/auth/spreadsheets'],
    });

    return google.sheets({ version: 'v4', auth });
}

/**
 * POST /api/contact
 *
 * Appends a new row to the "Contact" tab in Google Sheets.
 * Columns: A: Date  B: Name  C: Email  D: Phone  E: Message
 */
export async function POST(req: Request) {
    try {
        const body = await req.json();
        const { name, email, phone, message } = body;

        if (!name || !email || !message) {
            return NextResponse.json(
                { success: false, error: 'Name, email, and message are required' },
                { status: 400 }
            );
        }

        const sheets = getAuthAndSheets();
        const sheetId = process.env.GOOGLE_SHEET_ID;

        if (!sheetId) {
            console.error('Missing GOOGLE_SHEET_ID');
            return NextResponse.json(
                { success: false, error: 'Sheet not configured' },
                { status: 500 }
            );
        }

        const now = new Date();
        const dateStr = now.toLocaleDateString('en-US', {
            year: 'numeric', month: '2-digit', day: '2-digit',
            hour: '2-digit', minute: '2-digit', hour12: true,
        });

        await sheets.spreadsheets.values.append({
            spreadsheetId: sheetId,
            range: 'Contact!A:E',
            valueInputOption: 'USER_ENTERED',
            requestBody: {
                values: [[dateStr, name, email, phone || '', message]],
            },
        });

        console.log(`✅ Contact form submission from ${name} (${email})`);

        return NextResponse.json({ success: true, message: 'Message sent successfully' });
    } catch (error: any) {
        console.error('❌ Contact form error:', error);
        return NextResponse.json(
            { success: false, error: 'Failed to send message', details: error.message },
            { status: 500 }
        );
    }
}
