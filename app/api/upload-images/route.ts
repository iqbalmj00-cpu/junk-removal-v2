import { put } from '@vercel/blob';
import { NextResponse } from 'next/server';

/**
 * POST /api/upload-images
 *
 * Accepts FormData with image files (already compressed client-side).
 * Uploads each to Vercel Blob and returns an array of public URLs.
 */
export async function POST(req: Request) {
    try {
        const formData = await req.formData();
        const files = formData.getAll('files') as File[];

        if (!files || files.length === 0) {
            return NextResponse.json(
                { success: false, error: 'No files provided' },
                { status: 400 }
            );
        }

        const urls: string[] = [];

        for (const file of files) {
            // Generate a unique filename with timestamp
            const timestamp = Date.now();
            const safeName = file.name.replace(/[^a-zA-Z0-9.-]/g, '_');
            const blobPath = `bookings/${timestamp}-${safeName}`;

            const blob = await put(blobPath, file, {
                access: 'public',
                contentType: file.type || 'image/jpeg',
            });

            urls.push(blob.url);
        }

        return NextResponse.json({ success: true, urls });
    } catch (error: any) {
        console.error('❌ Image upload error:', error);
        return NextResponse.json(
            { success: false, error: 'Failed to upload images', details: error.message },
            { status: 500 }
        );
    }
}
