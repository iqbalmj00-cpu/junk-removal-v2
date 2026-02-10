/**
 * Client-side tracking helpers.
 * All calls are fire-and-forget — errors are caught and logged, never block UI.
 */

export async function trackEvent(
    eventType: string,
    page: string,
    metadata: Record<string, any> = {}
) {
    try {
        await fetch('/api/track', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ eventType, page, metadata }),
        });
    } catch (err) {
        console.error('[Track] Event failed:', err);
    }
}

export async function trackQuote(quoteData: {
    customerName?: string;
    customerEmail?: string;
    customerPhone?: string;
    estimatedVolume: number;
    price: string;
    confidence?: number;
    itemList?: string[];
    imageCount: number;
}) {
    try {
        await fetch('/api/track/quote', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(quoteData),
        });
    } catch (err) {
        console.error('[Track] Quote failed:', err);
    }
}
