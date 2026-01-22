import { google } from 'googleapis';
import { NextResponse } from 'next/server';

export async function POST(req: Request) {
    try {
        const body = await req.json();
        const { name, phone, email, address, buildingType, stairsAccess, date, time, quoteRange, junkDetails } = body;

        // --- ID GENERATION ---
        // Format: #JR-XXXX-X (e.g., #JR-9281-K)
        const randomDigits = Math.floor(1000 + Math.random() * 9000);
        const randomLetter = String.fromCharCode(65 + Math.floor(Math.random() * 26)); // A-Z
        const bookingId = `#JR-${randomDigits}-${randomLetter}`;

        // --- ROBUST KEY CLEANER (start) ---
        // Fixes common Vercel/Env formatting issues:
        // 1. Literal "\n" strings
        // 2. Wrapping double quotes
        // 3. Wrapping single quotes
        let privateKey = process.env.GOOGLE_PRIVATE_KEY || "";

        // 1. Remove wrapping double quotes (common Vercel copy-paste error)
        if (privateKey.startsWith('"') && privateKey.endsWith('"')) {
            privateKey = privateKey.substring(1, privateKey.length - 1);
        }

        // 2. Remove wrapping single quotes
        if (privateKey.startsWith("'") && privateKey.endsWith("'")) {
            privateKey = privateKey.substring(1, privateKey.length - 1);
        }

        // 3. Convert literal "\n" to real newlines
        privateKey = privateKey.replace(/\\n/g, '\n');

        // 4. Trim whitespace
        privateKey = privateKey.trim();
        // --- ROBUST KEY CLEANER (end) ---

        // 1. Authenticate with Google
        const auth = new google.auth.GoogleAuth({
            credentials: {
                client_email: process.env.GOOGLE_SERVICE_ACCOUNT_EMAIL,
                private_key: privateKey,
            },
            scopes: [
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/calendar',
            ],
        });

        const sheets = google.sheets({ version: 'v4', auth });
        const calendar = google.calendar({ version: 'v3', auth });

        // 2. Append to Google Sheets
        const sheetId = process.env.GOOGLE_SHEET_ID;
        if (sheetId) {
            const response = await sheets.spreadsheets.values.append({
                spreadsheetId: sheetId,
                range: 'Sheet1!A:L', // Expanded range to include new columns
                valueInputOption: 'USER_ENTERED',
                requestBody: {
                    values: [
                        [
                            bookingId,
                            new Date().toISOString(),
                            name,
                            phone,
                            email,
                            address,
                            date,
                            time,
                            quoteRange,
                            junkDetails,
                            buildingType,
                            stairsAccess
                        ],
                    ],
                },
            });
            console.log('Sheet append response:', response.data);
        }

        // 3. Create Google Calendar Event
        const calendarId = process.env.GOOGLE_CALENDAR_ID;
        if (calendarId) {
            // Parse date and time to create start/end ISO strings
            // Assuming 'date' is YYYY-MM-DD and 'time' is HH:mm
            const startDateTime = new Date(`${date}T${time}:00`);

            // Default duration: 1 hour
            const endDateTime = new Date(startDateTime);
            endDateTime.setHours(startDateTime.getHours() + 1);

            await calendar.events.insert({
                calendarId: calendarId,
                requestBody: {
                    summary: `[${bookingId}] Junk Removal: ${name}`,
                    description: `Phone: ${phone}\nAddress: ${address}\nQuote: ${quoteRange}\nDetails: ${junkDetails}\nAccess: ${buildingType} - ${stairsAccess}\nID: ${bookingId}`,
                    start: { dateTime: startDateTime.toISOString() },
                    end: { dateTime: endDateTime.toISOString() },
                },
            });
        }

        return NextResponse.json({ success: true, bookingId: bookingId, message: 'Booking processed successfully' });
    } catch (error: any) {
        console.error('Booking API Error:', error);
        return NextResponse.json(
            { success: false, error: 'Failed to process booking', details: error.message },
            { status: 500 }
        );
    }
}
