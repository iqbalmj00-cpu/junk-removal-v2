'use client';

import dynamic from 'next/dynamic';

const CoverageMap = dynamic(() => import('@/components/CoverageMap'), {
    ssr: false,
    loading: () => (
        <div className="w-full h-full min-h-[400px] bg-slate-200 animate-pulse flex items-center justify-center">
            <span className="text-slate-400 font-medium">Loading map...</span>
        </div>
    ),
});

export default function CoverageMapWrapper() {
    return <CoverageMap />;
}
