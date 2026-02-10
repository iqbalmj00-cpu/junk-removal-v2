'use client';

import { usePathname, useSearchParams } from 'next/navigation';
import { useEffect, Suspense } from 'react';

declare global {
    interface Window {
        gtag?: (...args: any[]) => void;
    }
}

function GAPageTracker() {
    const pathname = usePathname();
    const searchParams = useSearchParams();

    useEffect(() => {
        if (typeof window.gtag === 'function') {
            const url = pathname + (searchParams?.toString() ? `?${searchParams.toString()}` : '');
            window.gtag('config', 'G-56CMER4LL2', {
                page_path: url,
            });
        }
    }, [pathname, searchParams]);

    return null;
}

export default function GoogleAnalytics() {
    return (
        <Suspense fallback={null}>
            <GAPageTracker />
        </Suspense>
    );
}
