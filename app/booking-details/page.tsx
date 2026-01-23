'use client';

import { useState, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { Navbar } from '@/components/Navbar';
import { Footer } from '@/components/Footer';
import { Button } from '@/components/ui/Button';
import { Truck, ChevronDown, Lock, AlertTriangle, Loader2 } from 'lucide-react';
import Link from 'next/link';

// Loading fallback for Suspense
function BookingDetailsLoading() {
    return (
        <div className="min-h-screen bg-gray-50 flex flex-col font-sans">
            <Navbar />
            <main className="flex-grow pt-32 pb-20 px-4">
                <div className="max-w-xl mx-auto flex items-center justify-center">
                    <Loader2 className="w-8 h-8 animate-spin text-orange-500" />
                </div>
            </main>
            <Footer />
        </div>
    );
}

// Inner component that uses useSearchParams
function BookingDetailsContent() {
    const searchParams = useSearchParams();
    const router = useRouter();


    // Parse data from URL params
    const minPrice = searchParams.get('min') || '0';
    const maxPrice = searchParams.get('max') || '0';
    const volume = searchParams.get('volume') || '0';
    const detectedItemsRaw = searchParams.get('items') || '';
    const detectedItems = detectedItemsRaw ? detectedItemsRaw.split(',').map(i => i.toLowerCase()) : [];

    // Check if bags were detected
    const hasBags = detectedItems.some(item =>
        item.includes('bag') || item.includes('plastic bag') || item.includes('garbage') || item.includes('trash bag')
    );

    // Form state
    const [bagContents, setBagContents] = useState('');
    const [heavyMaterials, setHeavyMaterials] = useState('none');
    const [accessDetails, setAccessDetails] = useState('');
    const [hazardCheck, setHazardCheck] = useState<'safe' | 'hazard' | null>(null);

    const isFormValid = accessDetails !== '' && hazardCheck !== null &&
        (hasBags ? bagContents !== '' : true);

    const handleContinue = () => {
        // Build URL params for scheduling page
        const params = new URLSearchParams({
            min: minPrice,
            max: maxPrice,
            volume: volume,
            heavyMaterials,
            accessDetails,
            hazardCheck: hazardCheck || 'safe',
            ...(hasBags && { bagContents })
        });

        router.push(`/scheduling?${params.toString()}`);
    };

    return (
        <div className="min-h-screen bg-gray-50 flex flex-col font-sans">
            <Navbar />

            <main className="flex-grow pt-32 pb-20 px-4">
                <div className="max-w-xl mx-auto">
                    {/* Card */}
                    <div className="bg-white rounded-2xl shadow-xl border border-gray-100 overflow-hidden">

                        {/* Header */}
                        <div className="p-8 pb-6">
                            <div className="flex items-start justify-between">
                                <div>
                                    <h1 className="text-3xl font-bold text-gray-900 mb-2">Booking Details</h1>
                                    <p className="text-gray-500">Help us prepare the right truck and crew for your job.</p>
                                </div>
                                <div className="w-12 h-12 bg-blue-100 rounded-xl flex items-center justify-center">
                                    <Truck className="w-6 h-6 text-blue-600" />
                                </div>
                            </div>
                        </div>

                        {/* Form Content */}
                        <div className="px-8 pb-8 space-y-6">

                            {/* Question 1: What's in the bags? (CONDITIONAL) */}
                            {hasBags && (
                                <div className="space-y-2">
                                    <label className="text-sm font-bold text-gray-800 uppercase tracking-wide">
                                        What's in the bags?
                                    </label>
                                    <div className="relative">
                                        <select
                                            value={bagContents}
                                            onChange={(e) => setBagContents(e.target.value)}
                                            className="w-full h-14 px-4 pr-10 rounded-xl border border-gray-200 bg-white text-gray-700 appearance-none focus:border-orange-500 focus:outline-none focus:ring-1 focus:ring-orange-500 text-base"
                                        >
                                            <option value="">Select contents...</option>
                                            <option value="household">Household trash</option>
                                            <option value="yard">Yard waste (leaves, grass)</option>
                                            <option value="construction">Construction debris</option>
                                            <option value="mixed">Mixed / Unknown</option>
                                        </select>
                                        <ChevronDown className="absolute right-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400 pointer-events-none" />
                                    </div>
                                </div>
                            )}

                            {/* Question 2: Heavy Materials (Moved from booking page) */}
                            <div className="space-y-2">
                                <label className="text-sm font-bold text-gray-800 uppercase tracking-wide">
                                    Heavy Materials
                                </label>
                                <div className="relative">
                                    <select
                                        value={heavyMaterials}
                                        onChange={(e) => setHeavyMaterials(e.target.value)}
                                        className="w-full h-14 px-4 pr-10 rounded-xl border border-gray-200 bg-white text-gray-700 appearance-none focus:border-orange-500 focus:outline-none focus:ring-1 focus:ring-orange-500 text-base"
                                    >
                                        <option value="none">No heavy materials (furniture, bags, boxes)</option>
                                        <option value="some">Some (~25%) - A few bricks or small debris</option>
                                        <option value="mixed">Mixed (~50%) - Half construction debris</option>
                                        <option value="mostly">Mostly Heavy (~75%) - Majority concrete/dirt</option>
                                        <option value="all">All Heavy (100%) - Full debris load</option>
                                    </select>
                                    <ChevronDown className="absolute right-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400 pointer-events-none" />
                                </div>
                                <p className="text-xs text-gray-400">
                                    Heavy: concrete, bricks, dirt, roofing, stone, gravel
                                </p>
                            </div>

                            {/* Question 3: Access Details */}
                            <div className="space-y-2">
                                <label className="text-sm font-bold text-gray-800 uppercase tracking-wide">
                                    Access Details
                                </label>
                                <div className="relative">
                                    <select
                                        value={accessDetails}
                                        onChange={(e) => setAccessDetails(e.target.value)}
                                        className="w-full h-14 px-4 pr-10 rounded-xl border border-gray-200 bg-white text-gray-700 appearance-none focus:border-orange-500 focus:outline-none focus:ring-1 focus:ring-orange-500 text-base"
                                    >
                                        <option value="">Select access details...</option>
                                        <option value="curbside">Street level / Curbside</option>
                                        <option value="stairs_1">Stairs (1 flight)</option>
                                        <option value="stairs_2">Stairs (2+ flights)</option>
                                        <option value="elevator">Elevator access</option>
                                        <option value="long_carry">Long carry (50+ feet)</option>
                                    </select>
                                    <ChevronDown className="absolute right-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400 pointer-events-none" />
                                </div>
                            </div>

                            {/* Question 4: Hazard Check */}
                            <div className="space-y-3">
                                <label className="text-sm font-bold text-gray-800 uppercase tracking-wide">
                                    Hazard Check
                                </label>
                                <div className="bg-gray-50 rounded-xl p-5 border border-gray-100">
                                    <p className="text-gray-700 mb-4">
                                        Does your junk contain any{' '}
                                        <span className="relative inline-block group">
                                            <span className="text-blue-600 underline hover:text-blue-800 cursor-help">
                                                hazardous materials?
                                            </span>
                                            {/* Hover Tooltip */}
                                            <span className="absolute left-1/2 -translate-x-1/2 bottom-full mb-2 w-64 p-3 bg-gray-900 text-white text-sm rounded-lg shadow-xl opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-50 pointer-events-none">
                                                <span className="font-semibold block mb-2 text-orange-400">Hazardous Materials Include:</span>
                                                <ul className="space-y-1 text-gray-200">
                                                    <li>• Paint & solvents</li>
                                                    <li>• Batteries (car/lithium)</li>
                                                    <li>• Chemicals & pesticides</li>
                                                    <li>• Propane tanks</li>
                                                    <li>• Motor oil & fluids</li>
                                                    <li>• Fluorescent bulbs</li>
                                                    <li>• Medical waste</li>
                                                </ul>
                                                {/* Arrow */}
                                                <span className="absolute left-1/2 -translate-x-1/2 top-full w-0 h-0 border-l-8 border-r-8 border-t-8 border-l-transparent border-r-transparent border-t-gray-900"></span>
                                            </span>
                                        </span>
                                    </p>
                                    <div className="grid grid-cols-2 gap-3">
                                        <button
                                            type="button"
                                            onClick={() => setHazardCheck('safe')}
                                            className={`h-12 rounded-xl border-2 font-medium transition-all ${hazardCheck === 'safe'
                                                ? 'border-green-500 bg-green-50 text-green-700'
                                                : 'border-gray-200 bg-white text-gray-600 hover:border-gray-300'
                                                }`}
                                        >
                                            No, it's safe
                                        </button>
                                        <button
                                            type="button"
                                            onClick={() => setHazardCheck('hazard')}
                                            className={`h-12 rounded-xl border-2 font-medium transition-all ${hazardCheck === 'hazard'
                                                ? 'border-orange-500 bg-orange-50 text-orange-700'
                                                : 'border-gray-200 bg-white text-gray-600 hover:border-gray-300'
                                                }`}
                                        >
                                            Yes, it does
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Hazard Warning (if they select Yes) */}
                        {hazardCheck === 'hazard' && (
                            <div className="mx-8 mb-6 bg-amber-50 border border-amber-200 rounded-xl p-4">
                                <div className="flex items-start gap-3">
                                    <AlertTriangle className="w-5 h-5 text-amber-600 mt-0.5 shrink-0" />
                                    <div>
                                        <p className="text-amber-800 font-medium mb-1">Hazardous Materials Detected</p>
                                        <p className="text-amber-700 text-sm">
                                            Items like paint, chemicals, or batteries require special handling.
                                            Our crew will assess on-site and provide a final quote.
                                        </p>
                                    </div>
                                </div>
                            </div>
                        )}

                        {/* Continue Button */}
                        <div className="px-8 pb-8">
                            <Button
                                onClick={handleContinue}
                                disabled={!isFormValid}
                                className={`w-full h-14 text-lg font-bold rounded-xl shadow-lg transition-all flex items-center justify-center gap-2 ${isFormValid
                                    ? 'bg-orange-500 hover:bg-orange-600 text-white shadow-orange-200'
                                    : 'bg-gray-200 text-gray-400 cursor-not-allowed'
                                    }`}
                            >
                                CONTINUE TO SCHEDULING
                                <span className="text-xl">→</span>
                            </Button>
                        </div>

                        {/* Security Footer */}
                        <div className="border-t border-gray-100 py-4 px-8 bg-gray-50/50">
                            <div className="flex items-center justify-center gap-2 text-gray-400 text-sm">
                                <Lock className="w-4 h-4" />
                                <span>Your details are secure and encrypted.</span>
                            </div>
                        </div>
                    </div>

                    {/* Back Link */}
                    <div className="text-center mt-6">
                        <button
                            onClick={() => router.back()}
                            className="text-gray-500 hover:text-gray-700 text-sm font-medium"
                        >
                            ← Back to estimate
                        </button>
                    </div>
                </div>
            </main>

            <Footer />
        </div>
    );
}

// Default export with Suspense boundary
export default function BookingDetailsPage() {
    return (
        <Suspense fallback={<BookingDetailsLoading />}>
            <BookingDetailsContent />
        </Suspense>
    );
}
