import { google } from 'googleapis';
import { NextResponse } from 'next/server';

// --- Helper: Get authenticated Sheets client ---
function getAuthAndSheets() {
    const clientEmail = process.env.GOOGLE_SERVICE_ACCOUNT_EMAIL;
    let privateKey = process.env.GOOGLE_PRIVATE_KEY || "";

    // Debug: log what we received (redacted)
    console.log('[AUTH DEBUG] client_email:', clientEmail);
    console.log('[AUTH DEBUG] private_key length:', privateKey.length);
    console.log('[AUTH DEBUG] private_key starts with:', privateKey.substring(0, 40));
    console.log('[AUTH DEBUG] private_key ends with:', privateKey.substring(privateKey.length - 40));

    // Strip surrounding quotes if present
    if (privateKey.startsWith('"') && privateKey.endsWith('"')) {
        privateKey = privateKey.substring(1, privateKey.length - 1);
        console.log('[AUTH DEBUG] Stripped double quotes');
    }
    if (privateKey.startsWith("'") && privateKey.endsWith("'")) {
        privateKey = privateKey.substring(1, privateKey.length - 1);
        console.log('[AUTH DEBUG] Stripped single quotes');
    }

    // Replace literal \n with actual newlines
    privateKey = privateKey.replace(/\\n/g, '\n');
    privateKey = privateKey.trim();

    console.log('[AUTH DEBUG] Final key starts with:', privateKey.substring(0, 30));
    console.log('[AUTH DEBUG] Final key contains BEGIN:', privateKey.includes('BEGIN PRIVATE KEY'));
    console.log('[AUTH DEBUG] Final key contains END:', privateKey.includes('END PRIVATE KEY'));

    const auth = new google.auth.GoogleAuth({
        credentials: {
            client_email: clientEmail,
            private_key: privateKey,
        },
        scopes: ['https://www.googleapis.com/auth/spreadsheets'],
    });

    return google.sheets({ version: 'v4', auth });
}

// --- Helper: Find row number by Customer ID (column A) ---
async function findRowByLeadId(sheets: any, sheetId: string, leadId: string): Promise<number | null> {
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
 * POST /api/lead
 *
 * Leads tab columns (must match existing sheet):
 *   A: Customer ID    B: Customer Name   C: Phone Number   D: Email Address
 *   E: Service Type   F: Date Booked     G: Time Slot      H: Pickup Address
 *   I: Price Shown    J: Payment Status
 *
 * Mode 1 - CREATE (no leadId in body):
 *   Fills A-D, leaves E-J empty.
 *
 * Mode 2 - UPDATE (leadId in body):
 *   Finds the row by Customer ID, updates specified columns.
 *   Currently used for updating Price Shown (column I) after AI quote.
 */
export async function POST(req: Request) {
    try {
        const body = await req.json();
        const sheets = getAuthAndSheets();
        const sheetId = process.env.GOOGLE_SHEET_ID;

        if (!sheetId) {
            console.error('Missing GOOGLE_SHEET_ID');
            return NextResponse.json(
                { success: false, error: 'Sheet not configured' },
                { status: 500 }
            );
        }

        // ===== MODE 2: UPDATE existing lead row =====
        if (body.leadId) {
            const { leadId, quoteMin, quoteMax } = body;

            const rowNumber = await findRowByLeadId(sheets, sheetId, leadId);
            if (!rowNumber) {
                console.error(`❌ Lead ${leadId} not found for update`);
                return NextResponse.json(
                    { success: false, error: 'Lead not found' },
                    { status: 404 }
                );
            }

            // Update column I (Price Shown)
            if (quoteMin && quoteMax) {
                const priceShown = `$${quoteMin} - $${quoteMax}`;
                await sheets.spreadsheets.values.update({
                    spreadsheetId: sheetId,
                    range: `Leads!I${rowNumber}`,
                    valueInputOption: 'USER_ENTERED',
                    requestBody: {
                        values: [[priceShown]],
                    },
                });
                console.log(`✅ Lead ${leadId} updated: Price Shown = ${priceShown}`);
            }

            return NextResponse.json({
                success: true,
                leadId,
                message: 'Lead updated successfully',
            });
        }

        // ===== MODE 1: CREATE new lead row =====
        const { firstName, lastName, email, phone } = body;

        if (!firstName || !lastName || !email || !phone) {
            return NextResponse.json(
                { success: false, error: 'Missing required fields' },
                { status: 400 }
            );
        }

        // Generate Customer ID: #LD-XXXX-X
        const randomDigits = Math.floor(1000 + Math.random() * 9000);
        const randomLetter = String.fromCharCode(65 + Math.floor(Math.random() * 26));
        const leadId = `#LD-${randomDigits}-${randomLetter}`;

        // Append new row: A-D filled, E-J empty
        await sheets.spreadsheets.values.append({
            spreadsheetId: sheetId,
            range: 'Leads!A:J',
            valueInputOption: 'USER_ENTERED',
            requestBody: {
                values: [
                    [
                        leadId,                           // A: Customer ID
                        `${firstName} ${lastName}`,       // B: Customer Name
                        phone,                            // C: Phone Number
                        email,                            // D: Email Address
                        '',                               // E: Service Type
                        '',                               // F: Date Booked
                        '',                               // G: Time Slot
                        '',                               // H: Pickup Address
                        '',                               // I: Price Shown
                        '',                               // J: Payment Status
                    ],
                ],
            },
        });

        console.log(`✅ Lead ${leadId} created: ${firstName} ${lastName}`);

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
