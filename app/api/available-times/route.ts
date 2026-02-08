import { google } from 'googleapis';
import { NextResponse } from 'next/server';

// --- Helper: Get authenticated Sheets client ---
function getAuthAndSheets() {
    const clientEmail = process.env.GOOGLE_SERVICE_ACCOUNT_EMAIL;
    let privateKey = process.env.GOOGLE_PRIVATE_KEY || "";

    if (privateKey.startsWith('"') && privateKey.endsWith('"')) {
        privateKey = privateKey.substring(1, privateKey.length - 1);
    }
    if (privateKey.startsWith("'") && privateKey.endsWith("'")) {
        privateKey = privateKey.substring(1, privateKey.length - 1);
    }
    privateKey = privateKey.replace(/\\n/g, '\n');
    privateKey = privateKey.trim();

    const auth = new google.auth.GoogleAuth({
        credentials: {
            client_email: clientEmail,
            private_key: privateKey,
        },
        scopes: ['https://www.googleapis.com/auth/spreadsheets'],
    });

    return google.sheets({ version: 'v4', auth });
}

// All possible hourly slots: 8 AM to 5 PM
const ALL_SLOTS = [
    '08:00', '09:00', '10:00', '11:00', '12:00',
    '13:00', '14:00', '15:00', '16:00', '17:00',
];

/**
 * GET /api/available-times?date=2026-02-10
 *
 * Checks the SCHEDULED APPOINTMENTS sheet for bookings on the given date,
 * returns only the time slots that are still available.
 */
export async function GET(req: Request) {
    try {
        const { searchParams } = new URL(req.url);
        const date = searchParams.get('date'); // Format: "2026-02-09"

        if (!date) {
            return NextResponse.json(
                { success: false, error: 'Missing date parameter' },
                { status: 400 }
            );
        }

        const sheets = getAuthAndSheets();
        const sheetId = process.env.GOOGLE_SHEET_ID;

        if (!sheetId) {
            return NextResponse.json({ success: true, available: ALL_SLOTS });
        }

        // Read column F (Appointment Time) from SCHEDULED APPOINTMENTS
        const res = await sheets.spreadsheets.values.get({
            spreadsheetId: sheetId,
            range: "'SCHEDULED APPOINTMENTS'!F:F",
            valueRenderOption: 'FORMATTED_VALUE',
        });

        const rows = res.data.values || [];
        const bookedTimes: string[] = [];

        // Parse the requested date into components for flexible matching
        const [year, month, day] = date.split('-');
        const monthNum = parseInt(month, 10);  // "02" → 2
        const dayNum = parseInt(day, 10);      // "09" → 9

        // Build multiple date patterns to match against
        const datePatterns = [
            date,                                          // "2026-02-09"
            `${monthNum}/${dayNum}/${year}`,               // "2/9/2026"
            `${month}/${day}/${year}`,                     // "02/09/2026"
            `${monthNum}/${dayNum}/${year.slice(2)}`,      // "2/9/26"
        ];

        console.log(`[AVAILABILITY] Looking for date: ${date}, patterns: ${datePatterns.join(' | ')}`);
        console.log(`[AVAILABILITY] Total rows in sheet: ${rows.length}`);

        for (let i = 0; i < rows.length; i++) {
            const cellValue = (rows[i][0] || '').toString().trim();
            if (!cellValue) continue;

            console.log(`[AVAILABILITY] Row ${i + 1}: "${cellValue}"`);

            // Check if this cell matches any of our date patterns
            const matchesDate = datePatterns.some(pattern => cellValue.startsWith(pattern));

            if (matchesDate) {
                // Extract hour from the time portion
                const hourMatch = cellValue.match(/(\d{1,2}):(\d{2})/);
                if (hourMatch) {
                    // Find the LAST occurrence of HH:MM (the time, not part of the date)
                    const allTimeMatches = [...cellValue.matchAll(/(\d{1,2}):(\d{2})/g)];
                    const lastMatch = allTimeMatches[allTimeMatches.length - 1];
                    const hour = lastMatch[1].padStart(2, '0');
                    bookedTimes.push(`${hour}:00`);
                    console.log(`[AVAILABILITY] → BOOKED: ${hour}:00`);
                }
            }
        }

        // Filter out booked slots
        const available = ALL_SLOTS.filter(slot => !bookedTimes.includes(slot));

        console.log(`[AVAILABILITY] Date: ${date}, Booked: [${bookedTimes.join(', ')}], Available: ${available.length} slots`);

        return NextResponse.json({ success: true, available });

    } catch (error: any) {
        console.error('❌ Available times error:', error.message);
        return NextResponse.json({ success: true, available: ALL_SLOTS });
    }
}
