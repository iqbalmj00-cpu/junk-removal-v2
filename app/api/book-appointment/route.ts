import { google } from 'googleapis';
import { NextResponse } from 'next/server';

// --- Helper: Parse "8am", "12pm", "4pm" to 24-hour number ---
function parseTimeToHour(timeStr: string): number {
    const isPM = timeStr.toLowerCase().includes('pm');
    const hour = parseInt(timeStr.replace(/[^0-9]/g, ''), 10);
    if (isPM && hour !== 12) return hour + 12;
    if (!isPM && hour === 12) return 0;
    return hour;
}

// --- Helper: Get authenticated Google clients ---
function getGoogleClients() {
    const clientEmail = process.env.GOOGLE_SERVICE_ACCOUNT_EMAIL;
    let privateKey = process.env.GOOGLE_PRIVATE_KEY || "";

    console.log('[BOOKING AUTH] client_email:', clientEmail);
    console.log('[BOOKING AUTH] private_key length:', privateKey.length);

    // Strip surrounding quotes if present
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
        scopes: [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/calendar',
        ],
    });

    return {
        sheets: google.sheets({ version: 'v4', auth }),
        calendar: google.calendar({ version: 'v3', auth }),
    };
}

// --- Helper: Find row number by Customer ID (column A) in Leads tab ---
async function findLeadRow(sheets: any, sheetId: string, leadId: string): Promise<number | null> {
    const res = await sheets.spreadsheets.values.get({
        spreadsheetId: sheetId,
        range: 'Leads!A:A',
    });

    const rows = res.data.values || [];
    for (let i = 0; i < rows.length; i++) {
        if (rows[i][0] === leadId) {
            return i + 1; // 1-indexed row number
        }
    }
    return null;
}

/**
 * POST /api/book-appointment
 *
 * 1. Appends to "SCHEDULED APPOINTMENTS" tab:
 *    A: Booking ID  B: Customer Name  C: Phone Number  D: Address
 *    E: Zip Code    F: Appointment Time  G: Service Type  H: Status  I: Contact Preference
 *
 * 2. Updates the "Leads" tab row (by leadId):
 *    E: Service Type  F: Date Booked  G: Time Slot  H: Pickup Address  J: Payment Status
 *
 * 3. Creates Google Calendar event
 */
export async function POST(req: Request) {
    try {
        const body = await req.json();
        const { name, phone, email, address, date, time, quoteRange, junkDetails, leadId } = body;

        // --- ID GENERATION ---
        const randomDigits = Math.floor(1000 + Math.random() * 9000);
        const randomLetter = String.fromCharCode(65 + Math.floor(Math.random() * 26));
        const bookingId = `#JR-${randomDigits}-${randomLetter}`;

        const { sheets, calendar } = getGoogleClients();
        const sheetId = process.env.GOOGLE_SHEET_ID;

        // --- 1. Append to SCHEDULED APPOINTMENTS tab ---
        if (sheetId) {
            // Extract zip code from address (last 5 digits if present)
            const zipMatch = address?.match(/\b(\d{5})\b/);
            const zipCode = zipMatch ? zipMatch[1] : '';

            // Format appointment time from date + time
            const appointmentTime = date && time ? `${date} ${time}` : '';

            await sheets.spreadsheets.values.append({
                spreadsheetId: sheetId,
                range: "'SCHEDULED APPOINTMENTS'!A:I",
                valueInputOption: 'USER_ENTERED',
                requestBody: {
                    values: [
                        [
                            bookingId,              // A: Booking ID
                            name,                   // B: Customer Name
                            phone,                  // C: Phone Number
                            address,                // D: Address
                            zipCode,                // E: Zip Code
                            appointmentTime,        // F: Appointment Time
                            'Junk Removal',         // G: Service Type
                            'Scheduled',            // H: Status
                            email ? 'Email' : 'Phone', // I: Contact Preference
                        ],
                    ],
                },
            });
            console.log(`✅ Booking ${bookingId} added to SCHEDULED APPOINTMENTS`);

            // --- 2. Update Leads row (if leadId provided) ---
            if (leadId) {
                const rowNumber = await findLeadRow(sheets, sheetId, leadId);
                if (rowNumber) {
                    // Update columns E, F, G, H (Service Type, Date Booked, Time Slot, Pickup Address)
                    await sheets.spreadsheets.values.update({
                        spreadsheetId: sheetId,
                        range: `Leads!E${rowNumber}:H${rowNumber}`,
                        valueInputOption: 'USER_ENTERED',
                        requestBody: {
                            values: [['Junk Removal', date, time, address]],
                        },
                    });

                    // Update column J (Payment Status)
                    await sheets.spreadsheets.values.update({
                        spreadsheetId: sheetId,
                        range: `Leads!J${rowNumber}`,
                        valueInputOption: 'USER_ENTERED',
                        requestBody: {
                            values: [['Pending']],
                        },
                    });

                    console.log(`✅ Lead ${leadId} updated to Booked`);
                } else {
                    console.warn(`⚠️ Lead ${leadId} not found in Leads tab, skipping update`);
                }
            }
        }

        // --- 3. Create Google Calendar Event ---
        const calendarId = process.env.GOOGLE_CALENDAR_ID;
        if (calendarId && date && time) {
            try {
                // Parse time slot strings like "8am - 12pm", "12pm - 4pm", "4pm - 8pm"
                // or raw hour strings like "08:00", "10:00", "12:00", "14:00", "16:00"
                let startHour = 8;
                let endHour = 10;

                if (time.includes(' - ')) {
                    const parts = time.split(' - ');
                    startHour = parseTimeToHour(parts[0].trim());
                    endHour = parseTimeToHour(parts[1].trim());
                } else if (time.includes(':')) {
                    startHour = parseInt(time.split(':')[0], 10);
                    endHour = startHour + 1;
                }

                const startTime = `${date}T${String(startHour).padStart(2, '0')}:00:00`;
                const endTime = `${date}T${String(endHour).padStart(2, '0')}:00:00`;

                await calendar.events.insert({
                    calendarId: calendarId,
                    requestBody: {
                        summary: `[${bookingId}] Junk Removal: ${name}`,
                        description: `Phone: ${phone}\nEmail: ${email}\nAddress: ${address}\nQuote: ${quoteRange}\nDetails: ${junkDetails}\nID: ${bookingId}`,
                        start: { dateTime: startTime, timeZone: 'America/Chicago' },
                        end: { dateTime: endTime, timeZone: 'America/Chicago' },
                    },
                });
                console.log(`✅ Calendar event created for ${bookingId} at ${startTime} CST`);
            } catch (calError: any) {
                console.error(`⚠️ Calendar event failed (booking still saved): ${calError.message}`);
            }
        }

        return NextResponse.json({ success: true, bookingId, message: 'Booking processed successfully' });
    } catch (error: any) {
        console.error('❌ Booking API Error:', error);
        return NextResponse.json(
            { success: false, error: 'Failed to process booking', details: error.message },
            { status: 500 }
        );
    }
}
