'use client';

import { useState, useRef, useEffect, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Navbar } from '@/components/Navbar';
import { Footer } from '@/components/Footer';
import { Button } from '@/components/ui/Button';
import { UploadCloud, CheckCircle, ArrowRight, Loader2, Calendar, User, Phone, MapPin, Mail, Building, ArrowUp, Bell, Receipt, Info, Camera, XCircle } from 'lucide-react';
import Link from 'next/link';
import imageCompression from 'browser-image-compression';
import exifr from 'exifr';
import { trackEvent, trackQuote } from '@/lib/tracking';

// --- Pricing Engine ---
// --- Pricing Engine ---
import { calculateJunkPrice } from '@/lib/pricingEngine';
import BookingModal from "./BookingModal";
import LiabilityWaiver from "./LiabilityWaiver";

type ViewState = 'calculator' | 'analyzing' | 'receipt' | 'scheduler' | 'waiver' | 'success';

interface BookingData {
    selectedImages: File[];
    estimatedVolumeCuFt: number;
    // Property Details
    buildingType: string;
    stairsAccess: string;
    // Booking Info
    date: string; // YYYY-MM-DD
    timeSlot: string;
    fullName: string;
    email: string;
    phone: string;
    address: string;
    instructions: string;
    signature: string;
}

function BookPageContent() {
    const searchParams = useSearchParams();
    const initialView = (searchParams.get('view') as ViewState) || 'calculator';
    const [view, setView] = useState<ViewState>(initialView);
    const [bookingData, setBookingData] = useState<BookingData>({
        selectedImages: [],
        estimatedVolumeCuFt: 0,
        buildingType: 'Residential',
        stairsAccess: 'Ground Floor',
        date: '',
        timeSlot: '',
        fullName: `${searchParams.get('firstName') || ''} ${searchParams.get('lastName') || ''}`.trim(),
        email: searchParams.get('email') || '',
        phone: searchParams.get('phone') || '',
        address: '',
        instructions: '',
        signature: '',
    });
    const [loadingState, setLoadingState] = useState({ title: 'ANALYZING JUNK...', subtitle: 'Calculating volume and finding the best price.' });
    // Smart Validation State
    const [jobType, setJobType] = useState<'single' | 'pile'>('single');
    const [heavyMaterialLevel, setHeavyMaterialLevel] = useState<string>('none');

    const fileInputRef = useRef<HTMLInputElement>(null);
    const router = useRouter();

    // --- State for Backend Quote ---
    const [quoteState, setQuoteState] = useState<{ min: number; max: number; volume: number; heavySurcharge?: number } | null>(null);
    const [quoteHistory, setQuoteHistory] = useState<Array<{ min: number; max: number; volume: number }>>([]);
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [availableTimes, setAvailableTimes] = useState<string[]>([]);
    const [loadingTimes, setLoadingTimes] = useState(false);

    // Fetch available time slots for a given date
    const fetchAvailableTimes = async (date: string) => {
        if (!date) { setAvailableTimes([]); return; }
        setLoadingTimes(true);
        try {
            const res = await fetch(`/api/available-times?date=${date}`);
            const data = await res.json();
            if (data.success) {
                setAvailableTimes(data.available);
            }
        } catch (err) {
            console.error('Failed to fetch available times:', err);
            // Fallback: show all slots
            setAvailableTimes(['08:00', '09:00', '10:00', '11:00', '12:00', '13:00', '14:00', '15:00', '16:00', '17:00']);
        } finally {
            setLoadingTimes(false);
        }
    };

    // --- Price Calculation ---
    // Helper for Grand Totals
    const getGrandTotal = () => {
        const historyMin = quoteHistory.reduce((acc, item) => acc + item.min, 0);
        const historyMax = quoteHistory.reduce((acc, item) => acc + item.max, 0);
        const historyVol = quoteHistory.reduce((acc, item) => acc + item.volume, 0);

        const currentMin = quoteState ? quoteState.min : 0;
        const currentMax = quoteState ? quoteState.max : 0;
        const currentVol = quoteState ? quoteState.volume : 0;

        return {
            min: historyMin + currentMin,
            max: historyMax + currentMax,
            volume: historyVol + currentVol,
            count: quoteHistory.length + (quoteState ? 1 : 0)
        };
    };

    const grandTotal = getGrandTotal();

    const handleAddPile = () => {
        if (quoteState) {
            setQuoteHistory([...quoteHistory, quoteState]);
            setQuoteState(null);
            setBookingData(prev => ({ ...prev, selectedImages: [] }));
            setJobType('single');
            setView('calculator');
            window.scrollTo({ top: 0, behavior: 'smooth' });
        }
    };
    const getPrice = () => {
        // PRIORITIZE BACKEND QUOTE if available
        if (quoteState) {
            return {
                basePrice: quoteState.min,
                // We'll hijack tierName to show the Logic type, but the UI handles the range display
                tierName: `AI Estimate`,
                surcharges: [],
                totalPrice: quoteState.max // Used for "Book This Price" placeholder if needed
            };
        }
        // Fallback to local estimation
        return calculateJunkPrice(bookingData.estimatedVolumeCuFt, []);
    };

    const priceDetails = getPrice();
    // Use quoteState volume if available for display consistency, otherwise calc from CuFt
    const volumeYards = quoteState ? quoteState.volume.toFixed(1) : (bookingData.estimatedVolumeCuFt / 27).toFixed(1);

    // --- Handlers ---
    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files.length > 0) {
            // Append new files to existing ones
            const newFiles = Array.from(e.target.files);
            setBookingData(prev => ({
                ...prev,
                selectedImages: [...prev.selectedImages, ...newFiles]
            }));
            // Reset quote if images change? strictly speaking yes, but keeping it simple.
        }
    };

    const removeImage = (indexToRemove: number) => {
        setBookingData(prev => ({
            ...prev,
            selectedImages: prev.selectedImages.filter((_, index) => index !== indexToRemove)
        }));
    };

    // Helper to convert File to Base64
    const fileToBase64 = (file: File): Promise<string> => {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.readAsDataURL(file);
            reader.onload = () => resolve(reader.result as string);
            reader.onerror = error => reject(error);
        });
    };

    // Generate and download ICS calendar file
    const addToCalendar = () => {
        const dateStr = bookingData.date || new Date().toISOString().split('T')[0];
        const timeSlot = bookingData.timeSlot || '12pm - 4pm';
        const address = bookingData.address || '';

        // Parse time slot (e.g., "8am - 12pm", "12pm - 4pm", "4pm - 8pm")
        const startHour = timeSlot.includes('8am') ? 8 : timeSlot.includes('12pm') ? 12 : 16;
        const endHour = timeSlot.includes('12pm') ? 12 : timeSlot.includes('4pm') ? 16 : 20;

        // Format date for Google Calendar (YYYYMMDD)
        const dateFormatted = dateStr.replace(/-/g, '');
        const startTime = `${dateFormatted}T${String(startHour).padStart(2, '0')}0000`;
        const endTime = `${dateFormatted}T${String(endHour).padStart(2, '0')}0000`;

        const googleCalendarUrl = `https://calendar.google.com/calendar/render?action=TEMPLATE&text=${encodeURIComponent('Junk Removal Pickup')}&dates=${startTime}/${endTime}&details=${encodeURIComponent("CleanSweep Junk Removal team will arrive during your scheduled window. We'll call 15 minutes before arrival.")}&location=${encodeURIComponent(address)}`;

        window.open(googleCalendarUrl, '_blank');
    };


    const handleAnalyze = async () => {
        if (bookingData.selectedImages.length === 0) return;
        setLoadingState({ title: 'ANALYZING PHOTOS...', subtitle: 'Uploading images to AI engine...' });
        setView('analyzing');

        // v6.7.2: Direct upload to Modal (bypasses Vercel 4.5MB limit)
        const MODAL_ENDPOINT = 'https://iqbalmj00-cpu--junk-vision-fastapi-app.modal.run/upload';

        try {
            setLoadingState({ title: 'PREPARING IMAGES...', subtitle: 'Extracting camera data...' });

            // Build FormData with ORIGINAL files (no compression)
            const formData = new FormData();

            for (let i = 0; i < bookingData.selectedImages.length; i++) {
                const file = bookingData.selectedImages[i];

                // Extract EXIF from original bytes for optional frontend fallback
                let extractedExif: {
                    make?: string;
                    model?: string;
                    focalLength?: number;
                    focalLength35mm?: number;
                    imageWidth?: number;
                    imageHeight?: number;
                    orientation?: number;
                } = {};

                try {
                    const exif = await exifr.parse(file, {
                        pick: ['Make', 'Model', 'FocalLength', 'FocalLengthIn35mmFilm',
                            'ImageWidth', 'ImageHeight', 'ExifImageWidth', 'ExifImageHeight', 'Orientation']
                    });

                    if (exif) {
                        extractedExif = {
                            make: exif.Make,
                            model: exif.Model,
                            focalLength: exif.FocalLength,
                            focalLength35mm: exif.FocalLengthIn35mmFilm,
                            imageWidth: exif.ExifImageWidth || exif.ImageWidth,
                            imageHeight: exif.ExifImageHeight || exif.ImageHeight,
                            orientation: exif.Orientation
                        };
                        console.log(`[EXIF] Image ${i + 1}: ${extractedExif.make} ${extractedExif.model}, focal=${extractedExif.focalLength}mm`);
                    }
                } catch (exifErr) {
                    console.warn(`[EXIF] Image ${i + 1}: Browser EXIF parse failed (server will extract)`, exifErr);
                }

                // Append ORIGINAL file (untouched bytes - HEIC stays HEIC!)
                formData.append('files', file);
                formData.append('exif', JSON.stringify(extractedExif));

                console.log(`[UPLOAD] Image ${i + 1}: ${file.name} (${(file.size / 1024 / 1024).toFixed(2)} MB)`);
            }

            // Set loading timer
            setLoadingState({ title: 'ANALYZING JUNK PILE...', subtitle: 'Warming up AI engine...' });
            const loadingTimer = setTimeout(() => {
                setLoadingState({ title: 'ALMOST DONE', subtitle: 'Thank you for your patience' });
            }, 120000);

            // Pre-warm: Ping health endpoint to wake up Modal container
            const MODAL_BASE = MODAL_ENDPOINT.replace('/upload', '');
            try {
                console.log('[UPLOAD] Pre-warming Modal container...');
                await fetch(`${MODAL_BASE}/health`, { method: 'GET' });
                console.log('[UPLOAD] Container is warm');
            } catch {
                console.log('[UPLOAD] Health ping failed, container may be cold-starting. Waiting 10s...');
                await new Promise(r => setTimeout(r, 10000));
            }

            setLoadingState({ title: 'ANALYZING JUNK PILE...', subtitle: 'This may take 1-2 minutes for high-res photos' });

            // Upload with retry logic for cold start failures
            console.log(`[UPLOAD] Sending ${bookingData.selectedImages.length} files to Modal...`);
            let response: Response | null = null;
            const MAX_RETRIES = 2;

            for (let attempt = 1; attempt <= MAX_RETRIES; attempt++) {
                try {
                    const controller = new AbortController();
                    const timeoutId = setTimeout(() => controller.abort(), 5 * 60 * 1000);
                    response = await fetch(MODAL_ENDPOINT, {
                        method: 'POST',
                        body: formData,
                        signal: controller.signal,
                    });
                    clearTimeout(timeoutId);
                    break; // Success, exit retry loop
                } catch (fetchErr) {
                    console.warn(`[UPLOAD] Attempt ${attempt} failed:`, fetchErr);
                    if (attempt < MAX_RETRIES) {
                        setLoadingState({ title: 'RECONNECTING...', subtitle: 'Server was busy, retrying...' });
                        await new Promise(r => setTimeout(r, 15000)); // Wait 15s before retry
                    } else {
                        throw fetchErr; // Final attempt failed
                    }
                }
            }

            if (!response) throw new Error('All upload attempts failed');

            clearTimeout(loadingTimer);

            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.error || 'Analysis failed');
            }

            const data = await response.json();
            console.log("Modal Quote Received:", data);

            // v6.7.2: Handle Modal response format {quote: {...}}
            const quote = data.quote;

            if (quote && quote.final_volume_cy !== undefined) {
                // SUCCESS: Got a valid quote from Modal
                const volumeYards = quote.final_volume_cy || 0;
                const volumeCuFt = volumeYards * 27;

                // Check if no junk was detected (volume = 0, price = 0)
                if (volumeYards <= 0 || (quote.min_price === 0 && quote.max_price === 0)) {
                    alert("We couldn't detect any junk in your photos. Please upload new images showing your junk pile clearly.");
                    setView('calculator');
                    return;
                }

                // Sync state
                setBookingData(prev => ({
                    ...prev,
                    estimatedVolumeCuFt: volumeCuFt
                }));

                // Set Range Price from Backend
                setQuoteState({
                    min: quote.min_price || 0,
                    max: quote.max_price || 0,
                    volume: volumeYards,
                    heavySurcharge: 0  // TODO: heavy material detection
                });

                console.log(`[QUOTE] Volume: ${volumeYards.toFixed(2)} yd³, Price: $${quote.min_price}-$${quote.max_price}`);

                // Update existing lead row with quote data (Price Shown)
                const currentLeadId = searchParams.get('leadId');
                if (currentLeadId) {
                    try {
                        fetch('/api/lead', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                leadId: currentLeadId,
                                quoteMin: quote.min_price || 0,
                                quoteMax: quote.max_price || 0,
                            }),
                        }).catch(err => console.error('Lead quote update failed:', err));
                    } catch (err) {
                        console.error('Lead quote capture error:', err);
                    }
                }

                // --- CRM Step 2: Update lead to "quoted" ---
                try {
                    const syjLeadId = sessionStorage.getItem('syjLeadId');
                    if (syjLeadId) {
                        fetch('/api/crm', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                leadId: syjLeadId,
                                value: priceDetails.totalPrice,
                                description: `Volume: ${volumeYards.toFixed(1)} yd³`,
                                status: 'quoted',
                                website_honeypot: '',
                            }),
                        }).catch(err => console.error('[CRM] Quoted update failed:', err));
                        console.log('[CRM] Lead updated to quoted:', syjLeadId);
                    }
                } catch (err) {
                    console.error('[CRM] Quoted update error:', err);
                }

                // Transition Logic
                setView('receipt');

                // Track quote generated
                trackEvent('quote_generated', '/book', {
                    leadId: searchParams.get('leadId'),
                    volume: volumeYards,
                    minPrice: quote.min_price,
                    maxPrice: quote.max_price,
                    confidence: quote.confidence_score,
                    imageCount: bookingData.selectedImages.length,
                });
                trackQuote({
                    customerName: bookingData.fullName,
                    customerEmail: bookingData.email,
                    customerPhone: bookingData.phone,
                    estimatedVolume: volumeYards,
                    price: `$${quote.min_price} - $${quote.max_price}`,
                    confidence: quote.confidence_score,
                    imageCount: bookingData.selectedImages.length,
                });

                // Send quote to dashboard
                if (typeof window !== 'undefined' && (window as any).syj?.sendQuote) {
                    (window as any).syj.sendQuote({
                        junkSummary: 'N/A',
                        volumeCubicYards: volumeYards,
                        priceQuoted: quote.min_price,
                        customerName: bookingData.fullName || '',
                        customerEmail: bookingData.email || '',
                        customerPhone: bookingData.phone || '',
                    });
                }

                // Auto-Scroll to results
                setTimeout(() => {
                    window.scrollTo({ top: 0, behavior: 'smooth' });
                }, 100);

            } else if (data.error) {
                throw new Error(data.error);
            } else {
                // Unexpected response format
                console.warn("Unexpected Modal response:", data);
                throw new Error("Invalid response from analysis server");
            }

        } catch (error: any) {
            console.error("Analysis Failed:", error);
            alert("System Busy. Request sent to manual dispatch.");
            setView('calculator');
        }
    };

    const handleSchedulerSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        setView('waiver');
    };

    const handleWaiverAccept = (signatureDataUrl: string) => {
        setBookingData(prev => ({ ...prev, signature: signatureDataUrl }));
        handleBook(signatureDataUrl);
    };

    const handleBook = async (signatureDataUrl?: string) => {
        setView('analyzing');

        try {
            // --- STEP 1: Compress & Upload images to Vercel Blob ---
            let imageUrls: string[] = [];
            if (bookingData.selectedImages.length > 0) {
                setLoadingState({ title: 'UPLOADING PHOTOS...', subtitle: 'Compressing and uploading images...' });
                const compressed: File[] = [];
                for (const file of bookingData.selectedImages) {
                    try {
                        const c = await imageCompression(file, { maxSizeMB: 0.5, maxWidthOrHeight: 1920, useWebWorker: true });
                        compressed.push(c);
                    } catch { compressed.push(file); }
                }
                const uploadForm = new FormData();
                compressed.forEach(f => uploadForm.append('files', f));
                const uploadRes = await fetch('/api/upload-images', { method: 'POST', body: uploadForm });
                if (uploadRes.ok) {
                    const uploadData = await uploadRes.json();
                    imageUrls = uploadData.urls || [];
                    console.log(`[CRM] ${imageUrls.length} images uploaded`);
                }
            }

            // --- STEP 2: Submit to CRM (update lead to "booked") ---
            setLoadingState({ title: 'SUBMITTING TO CRM...', subtitle: 'Updating your booking details...' });
            const syjLeadId = sessionStorage.getItem('syjLeadId') || '';
            try {
                const crmRes = await fetch('/api/crm', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        leadId: syjLeadId || undefined,
                        name: bookingData.fullName,
                        phone: bookingData.phone,
                        email: bookingData.email,
                        address: bookingData.address,
                        description: `Volume: ${grandTotal.volume.toFixed(1)} yd³`,
                        image_urls: imageUrls,
                        requestedDate: bookingData.date,
                        status: 'booked',
                        website_honeypot: '',
                    }),
                });
                if (crmRes.ok) {
                    const crmData = await crmRes.json();
                    console.log('[CRM] Lead updated to booked:', crmData.leadId, crmData.updated ? '(updated)' : '(new)');
                }
            } catch (crmErr) {
                console.error('[CRM] Submission failed (continuing with Sheets):', crmErr);
            }

            // --- STEP 3: Dual-write to Google Sheets + Calendar ---
            setLoadingState({ title: 'FINALIZING BOOKING...', subtitle: 'Securing your appointment time...' });
            const response = await fetch('/api/book-appointment', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name: bookingData.fullName,
                    phone: bookingData.phone,
                    email: bookingData.email,
                    address: bookingData.address,
                    date: bookingData.date,
                    time: bookingData.timeSlot,
                    quoteRange: `$${grandTotal.min} - $${grandTotal.max}`,
                    junkDetails: `Volume: ${grandTotal.volume.toFixed(1)} yd³`,
                    leadId: searchParams.get('leadId') || '',
                }),
            });

            const data = await response.json();
            console.log('Booking response:', data);

            if (data.success) {
                // Track booking confirmed
                trackEvent('booking_confirmed', '/book', {
                    bookingId: data.bookingId,
                    crmLeadId: sessionStorage.getItem('syjLeadId') || '',
                    leadId: searchParams.get('leadId'),
                    date: bookingData.date,
                    time: bookingData.timeSlot,
                    quoteRange: `$${grandTotal.min} - $${grandTotal.max}`,
                });
                // Send confirmed lead to dashboard
                if (typeof window !== 'undefined' && (window as any).syj?.sendLead) {
                    (window as any).syj.sendLead({
                        name: bookingData.fullName || '',
                        email: bookingData.email || '',
                        phone: bookingData.phone || '',
                        source: 'website_form',
                        value: grandTotal.min,
                        notes: 'Booking confirmed',
                    });
                }

                // Redirect to thank-you page
                const params = new URLSearchParams({
                    bookingId: data.bookingId,
                    date: bookingData.date,
                    time: bookingData.timeSlot,
                    address: bookingData.address,
                    name: bookingData.fullName,
                });
                router.push(`/thank-you?${params.toString()}`);
            } else {
                throw new Error(data.error || 'Booking failed');
            }
        } catch (error: any) {
            console.error('Booking error:', error);
            alert('We could not process your request automatically. Please call us at (832) 793-6566.');
            setView('scheduler');
        }
    };

    // --- Render Views ---

    // VIEW 1: The Calculator
    const renderCalculator = () => (
        <div className="max-w-2xl mx-auto animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div className="text-center mb-10">
                <h1 className="text-5xl font-extrabold text-slate-900 mb-4 tracking-tight">JUNK PRICING TOOL</h1>
                <p className="text-xl text-slate-500 font-light">
                    Upload photos for an instant quote.
                </p>
            </div>

            <div className="bg-white rounded-[2rem] shadow-xl border border-slate-100 overflow-hidden">

                {/* --- MULTI-PILE SUMMARY (If history exists) --- */}
                {quoteHistory.length > 0 && (
                    <div className="bg-slate-900 text-white p-6 border-b border-slate-800">
                        <div className="flex justify-between items-center mb-2">
                            <h3 className="font-bold uppercase tracking-wider text-sm text-brand-orange">Current Job Summary</h3>
                            <span className="bg-slate-800 text-xs px-2 py-1 rounded text-slate-400">{quoteHistory.length} Pile(s) Banked</span>
                        </div>
                        <div className="flex justify-between items-end">
                            <div>
                                <p className="text-slate-400 text-sm">Running Total:</p>
                                <p className="text-2xl font-extrabold">${quoteHistory.reduce((acc, i) => acc + i.min, 0)} - ${quoteHistory.reduce((acc, i) => acc + i.max, 0)}</p>
                            </div>
                            <div className="text-right">
                                <p className="text-slate-400 text-sm">Volume:</p>
                                <p className="text-xl font-bold">{quoteHistory.reduce((acc, i) => acc + i.volume, 0).toFixed(1)} yd³</p>
                            </div>
                        </div>
                    </div>
                )}

                {/* --- START NEW ALERT BOX --- */}
                {/* --- SMART VALIDATION TOGGLE --- */}
                <div className="px-10 mt-10 mb-6">
                    <div className="bg-slate-100 p-1.5 rounded-xl flex relative mb-4">
                        <button
                            onClick={() => setJobType('single')}
                            className={`flex-1 flex items-center justify-center py-3 text-sm font-bold rounded-full transition-all duration-300 ${jobType === 'single' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}
                        >
                            Single Item
                        </button>
                        <button
                            onClick={() => setJobType('pile')}
                            className={`flex-1 flex items-center justify-center py-3 text-sm font-bold rounded-full transition-all duration-300 ${jobType === 'pile' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}
                        >
                            Pile / Cleanout
                        </button>
                    </div>
                    {/* Heavy Materials moved to booking-details page */}
                </div>
                {/* --- END NEW ALERT BOX --- */}

                {/* Upload Zone */}
                <div
                    className="p-10 border-b border-slate-100 cursor-pointer group bg-slate-50/50 hover:bg-orange-50/30 transition-colors"
                    onClick={() => fileInputRef.current?.click()}
                >
                    <div className="border-4 border-dashed border-slate-300 rounded-2xl min-h-[16rem] flex flex-col items-center justify-center group-hover:border-brand-orange transition-colors relative overflow-hidden p-6">
                        {bookingData.selectedImages.length > 0 ? (
                            <div className="w-full">
                                <div className="mt-2 grid grid-cols-2 gap-4">
                                    {bookingData.selectedImages.map((file, index) => (
                                        <div key={index} className="relative h-40 w-full overflow-hidden rounded-xl border border-gray-200">
                                            <img
                                                src={URL.createObjectURL(file)}
                                                alt={`Upload ${index + 1}`}
                                                className="h-full w-full object-cover"
                                            />
                                            <button
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    removeImage(index);
                                                }}
                                                className="absolute top-2 right-2 w-6 h-6 bg-black/60 hover:bg-red-500 rounded-full flex items-center justify-center text-white text-xs transition-colors"
                                            >
                                                ✕
                                            </button>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        ) : (
                            <div className="text-center p-6">
                                <div className="w-20 h-20 bg-white rounded-full flex items-center justify-center text-slate-400 mb-4 mx-auto shadow-sm group-hover:scale-110 transition-transform">
                                    <UploadCloud size={40} className="group-hover:text-brand-orange" />
                                </div>
                                <h3 className="text-xl font-bold text-slate-700 mb-1">Drag & drop or click</h3>
                                <p className="text-slate-400 text-sm">Upload multiple photos</p>
                            </div>
                        )}
                        <input
                            type="file"
                            ref={fileInputRef}
                            onChange={handleFileChange}
                            accept="image/*,.heic,.heif"
                            multiple
                            className="hidden"
                        />
                    </div>
                </div>

                {/* Photo Guide - Only show for Pile/Cleanout */}
                {jobType === 'pile' && (
                    <div className="px-8 py-6 bg-slate-50 border-t border-slate-100">
                        <h3 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-6">Photo Guide</h3>

                        <div className="grid grid-cols-1 xl:grid-cols-2 gap-8 xl:gap-12">
                            {/* Left: 4 Perspectives */}
                            <div>
                                <h4 className="font-bold text-slate-900 mb-4 flex items-center gap-2">
                                    <Camera className="text-brand-orange" size={20} />
                                    THE 4 PERSPECTIVES
                                </h4>
                                <p className="text-sm text-slate-600 mb-6 leading-relaxed">
                                    Step back 6-10 feet. Ensure we can see the floor and the entire pile in context.
                                </p>
                                <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-center">
                                    {/* Left Angle */}
                                    <div className="bg-white p-3 rounded-lg shadow-sm border border-slate-200 h-full flex flex-col justify-center">
                                        <div className="h-10 flex items-center justify-center mb-1">
                                            <Camera className="text-indigo-400 -rotate-12" size={28} />
                                        </div>
                                        <span className="text-xs font-bold text-slate-700 block">Left Angle</span>
                                    </div>
                                    {/* Front View - Required */}
                                    <div className="bg-white p-3 rounded-lg shadow-sm border border-slate-200 relative h-full flex flex-col justify-center">
                                        <div className="absolute -top-2 left-1/2 transform -translate-x-1/2 bg-brand-orange text-white text-[10px] px-2 py-0.5 rounded-full font-bold whitespace-nowrap shadow-sm z-10">Required</div>
                                        <div className="h-10 flex items-center justify-center mb-1">
                                            <Camera className="text-brand-orange" size={28} />
                                        </div>
                                        <span className="text-xs font-bold text-slate-700 block">Front View</span>
                                    </div>
                                    {/* Right Angle */}
                                    <div className="bg-white p-3 rounded-lg shadow-sm border border-slate-200 h-full flex flex-col justify-center">
                                        <div className="h-10 flex items-center justify-center mb-1">
                                            <Camera className="text-indigo-400 rotate-12" size={28} />
                                        </div>
                                        <span className="text-xs font-bold text-slate-700 block">Right Angle</span>
                                    </div>
                                    {/* Back View - Required */}
                                    <div className="bg-white p-3 rounded-lg shadow-sm border border-slate-200 relative h-full flex flex-col justify-center">
                                        <div className="absolute -top-2 left-1/2 transform -translate-x-1/2 bg-brand-orange text-white text-[10px] px-2 py-0.5 rounded-full font-bold whitespace-nowrap shadow-sm z-10">Required</div>
                                        <div className="h-10 flex items-center justify-center mb-1">
                                            <Camera className="text-brand-orange" size={28} />
                                        </div>
                                        <span className="text-xs font-bold text-slate-700 block">Back View</span>
                                    </div>
                                </div>
                            </div>

                            {/* Right: Do This / Avoid This */}
                            <div className="grid grid-cols-2 gap-6">
                                {/* Do This */}
                                <div>
                                    <h4 className="font-bold text-emerald-600 mb-4 flex items-center gap-2 text-sm uppercase">
                                        <span className="bg-emerald-100 p-1 rounded-full flex items-center justify-center">
                                            <CheckCircle size={14} className="text-emerald-600" />
                                        </span>
                                        Do This
                                    </h4>
                                    <ul className="space-y-3 text-sm text-slate-600">
                                        <li className="flex items-start gap-2">
                                            <CheckCircle className="text-emerald-500 mt-0.5 shrink-0" size={16} />
                                            <span>Step back</span>
                                        </li>
                                        <li className="flex items-start gap-2">
                                            <CheckCircle className="text-emerald-500 mt-0.5 shrink-0" size={16} />
                                            <span>Chest height</span>
                                        </li>
                                        <li className="flex items-start gap-2">
                                            <CheckCircle className="text-emerald-500 mt-0.5 shrink-0" size={16} />
                                            <span>Keep level</span>
                                        </li>
                                        <li className="flex items-start gap-2">
                                            <CheckCircle className="text-emerald-500 mt-0.5 shrink-0" size={16} />
                                            <span>Good lighting</span>
                                        </li>
                                        <li className="flex items-start gap-2">
                                            <CheckCircle className="text-emerald-500 mt-0.5 shrink-0" size={16} />
                                            <span>Leave space</span>
                                        </li>
                                    </ul>
                                </div>

                                {/* Avoid This */}
                                <div>
                                    <h4 className="font-bold text-rose-600 mb-4 flex items-center gap-2 text-sm uppercase">
                                        <span className="bg-rose-100 p-1 rounded-full flex items-center justify-center">
                                            <XCircle size={14} className="text-rose-600" />
                                        </span>
                                        Avoid This
                                    </h4>
                                    <ul className="space-y-3 text-sm text-slate-600">
                                        <li className="flex items-start gap-2">
                                            <XCircle className="text-rose-500 mt-0.5 shrink-0" size={16} />
                                            <span>Zooming in</span>
                                        </li>
                                        <li className="flex items-start gap-2">
                                            <XCircle className="text-rose-500 mt-0.5 shrink-0" size={16} />
                                            <span>Ultra-wide lens</span>
                                        </li>
                                        <li className="flex items-start gap-2">
                                            <XCircle className="text-rose-500 mt-0.5 shrink-0" size={16} />
                                            <span>Heavy tilt</span>
                                        </li>
                                        <li className="flex items-start gap-2">
                                            <XCircle className="text-rose-500 mt-0.5 shrink-0" size={16} />
                                            <span>Blurry photos</span>
                                        </li>
                                        <li className="flex items-start gap-2">
                                            <XCircle className="text-rose-500 mt-0.5 shrink-0" size={16} />
                                            <span>Cropping pile</span>
                                        </li>
                                    </ul>
                                </div>
                            </div>
                        </div>
                    </div>
                )}

                {/* Calculate Price Button */}
                <div className="p-10 bg-white border-t border-slate-100">
                    {(() => {
                        const minImages = jobType === 'single' ? 1 : 2;
                        const currentCount = bookingData.selectedImages.length;
                        const isReady = currentCount >= minImages;
                        const remaining = minImages - currentCount;

                        return (
                            <Button
                                onClick={handleAnalyze}
                                disabled={!isReady}
                                data-track="quote_upload"
                                className={`w-full h-16 text-xl font-bold rounded-full shadow-xl transition-all ${isReady
                                    ? 'bg-brand-orange hover:bg-orange-600 text-white shadow-orange-900/20'
                                    : 'bg-slate-200 text-slate-400 cursor-not-allowed'
                                    }`}
                            >
                                {!isReady && currentCount > 0
                                    ? `Upload ${remaining} more photo${remaining > 1 ? 's' : ''}`
                                    : 'CALCULATE PRICE'
                                }
                            </Button>
                        );
                    })()}
                </div>

            </div>
        </div>
    );

    // VIEW 2: The Receipt (Minimalist Dark)
    const renderReceipt = () => (
        <div className="max-w-lg mx-auto animate-in fade-in zoom-in duration-500">
            <Button variant="ghost" onClick={() => setView('calculator')} className="text-slate-400 hover:text-slate-900 font-bold px-0 mb-6">
                ← Back to Upload
            </Button>

            <div className="bg-slate-900 rounded-xl p-8 shadow-2xl border border-slate-800 relative overflow-hidden">
                {/* Subtle Glow Effect */}
                <div className="absolute top-0 right-0 w-32 h-32 bg-orange-500/10 blur-[50px] rounded-full pointing-events-none"></div>

                {/* Header */}
                <div className="flex items-center gap-2 mb-6 border-b border-slate-800 pb-4">
                    <Receipt size={16} className="text-slate-500" />
                    <span className="text-xs font-bold tracking-widest text-slate-500 uppercase">Price Estimate</span>
                </div>

                {/* The Range (Hero) */}
                <div className="mb-2">
                    <p className="text-sm text-slate-400 mb-1 font-medium">{quoteHistory.length > 0 ? 'Grand Total (All Piles)' : 'Estimated Range'}</p>
                    <h2 className="text-5xl font-extrabold text-orange-500 tracking-tight">
                        {quoteState ? `$${grandTotal.min} - $${grandTotal.max}` : `$${priceDetails.totalPrice}`}
                    </h2>
                    {quoteHistory.length > 0 && (
                        <p className="text-slate-500 text-sm mt-2">
                            Includes current pile (${quoteState?.min}-${quoteState?.max}) + {quoteHistory.length} previous pile(s).
                        </p>
                    )}
                </div>

                {/* Footer Disclaimer */}
                <div className="bg-slate-800/50 rounded-lg p-4 mt-8 border border-white/5">
                    <p className="text-xs text-slate-400 leading-relaxed">
                        *Final pricing is confirmed onsite before we start. If you don't like the price, we leave at no cost.
                    </p>
                </div>

                {/* Heavy Material Surcharge Alert */}
                {(quoteState?.heavySurcharge ?? 0) > 0 && (
                    <div className="bg-amber-900/30 border border-amber-700/50 rounded-lg p-4 mt-4">
                        <p className="text-amber-200 text-sm">
                            ⚠️ Heavy Material Surcharge: +${quoteState?.heavySurcharge} included in price
                        </p>
                    </div>
                )}

                {/* Action */}
                <div className="mt-6 space-y-3">
                    <Button
                        onClick={() => {
                            // Navigate to booking-details page with quote data
                            const params = new URLSearchParams({
                                min: String(grandTotal.min),
                                max: String(grandTotal.max),
                                volume: String(grandTotal.volume.toFixed(1)),
                                items: '', // Detected items would come from API response
                                firstName: searchParams.get('firstName') || '',
                                lastName: searchParams.get('lastName') || '',
                                email: searchParams.get('email') || '',
                                phone: searchParams.get('phone') || '',
                            });
                            const lid = searchParams.get('leadId');
                            if (lid) params.set('leadId', lid);
                            router.push(`/booking-details?${params.toString()}`);
                        }}
                        data-track="book_now"
                        className="w-full bg-orange-500 hover:bg-orange-600 text-white h-14 rounded-full text-lg font-bold shadow-lg shadow-orange-900/30 transition-all"
                    >
                        BOOK THIS ESTIMATE
                    </Button>
                    <Button
                        onClick={handleAddPile}
                        variant="outline"
                        className="w-full border-2 border-slate-700 text-slate-300 hover:bg-slate-800 hover:text-white h-14 rounded-full text-lg font-bold transition-all"
                    >
                        ➕ Add Another Pile
                    </Button>
                </div>
            </div>
        </div>
    );

    // VIEW 3: The Scheduler
    const renderScheduler = () => (
        <div className="max-w-2xl mx-auto animate-in fade-in slide-in-from-right-8 duration-500">
            <Button variant="ghost" onClick={() => setView('receipt')} className="text-slate-400 hover:text-slate-900 font-bold px-0 mb-6">
                ← Back to Quote
            </Button>

            <div className="bg-white rounded-[2rem] shadow-xl border border-slate-100 p-10 md:p-12">
                <div className="mb-10 text-center">
                    <h2 className="text-3xl font-bold text-slate-900 mb-2">Finalize Booking</h2>
                    <p className="text-slate-500">Secure your spot for <strong>${priceDetails.totalPrice}</strong>.</p>
                </div>

                <form onSubmit={handleSchedulerSubmit} className="space-y-6">
                    {/* Date & Time */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div>
                            <label className="text-sm font-bold text-slate-700 mb-2 block">Date</label>
                            <input
                                type="date" required
                                min={new Date().toISOString().split('T')[0]}
                                className="w-full h-14 px-4 rounded-xl border border-gray-300 bg-white text-gray-900 placeholder-gray-400 focus:border-orange-500 focus:outline-none focus:ring-1 focus:ring-orange-500 text-lg font-medium"
                                onChange={(e) => {
                                    setBookingData({ ...bookingData, date: e.target.value, timeSlot: '' });
                                    fetchAvailableTimes(e.target.value);
                                }}
                            />
                        </div>
                        <div>
                            <label className="text-sm font-bold text-slate-700 mb-2 block">Available Time</label>
                            <select
                                required
                                disabled={!bookingData.date || loadingTimes}
                                className="w-full h-14 px-4 rounded-xl border border-gray-300 bg-white text-gray-900 placeholder-gray-400 focus:border-orange-500 focus:outline-none focus:ring-1 focus:ring-orange-500 text-lg font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                                value={bookingData.timeSlot}
                                onChange={(e) => setBookingData({ ...bookingData, timeSlot: e.target.value })}
                            >
                                <option value="">{loadingTimes ? 'Loading...' : !bookingData.date ? 'Select a date first' : availableTimes.length === 0 ? 'No availability' : 'Select time...'}</option>
                                {availableTimes.map((slot) => {
                                    const hour = parseInt(slot.split(':')[0], 10);
                                    const ampm = hour >= 12 ? 'PM' : 'AM';
                                    const displayHour = hour > 12 ? hour - 12 : hour === 0 ? 12 : hour;
                                    return <option key={slot} value={slot}>{`${displayHour}:00 ${ampm}`}</option>;
                                })}
                            </select>
                        </div>
                    </div>

                    {/* Contact Info */}
                    <div className="space-y-4">
                        <input
                            type="text" placeholder="Full Name" required
                            value={bookingData.fullName}
                            className="w-full h-14 px-4 rounded-xl border border-gray-300 bg-white text-gray-900 placeholder-gray-400 focus:border-orange-500 focus:outline-none focus:ring-1 focus:ring-orange-500 text-lg font-medium"
                            onChange={(e) => setBookingData({ ...bookingData, fullName: e.target.value })}
                        />
                        <input
                            type="tel" placeholder="Phone Number" required
                            value={bookingData.phone}
                            className="w-full h-14 px-4 rounded-xl border border-gray-300 bg-white text-gray-900 placeholder-gray-400 focus:border-orange-500 focus:outline-none focus:ring-1 focus:ring-orange-500 text-lg font-medium"
                            onChange={(e) => setBookingData({ ...bookingData, phone: e.target.value })}
                        />
                        <input
                            type="text" placeholder="Pickup Address" required
                            value={bookingData.address}
                            className="w-full h-14 px-4 rounded-xl border border-gray-300 bg-white text-gray-900 placeholder-gray-400 focus:border-orange-500 focus:outline-none focus:ring-1 focus:ring-orange-500 text-lg font-medium"
                            onChange={(e) => setBookingData({ ...bookingData, address: e.target.value })}
                        />
                    </div>

                    <Button data-track="booking_finalized" className="w-full h-16 bg-brand-orange hover:bg-orange-600 text-white text-xl font-bold rounded-full mt-4 shadow-xl shadow-orange-900/20">
                        REVIEW &amp; SIGN WAIVER
                    </Button>
                </form>
            </div>
        </div>
    );

    // Loading State
    const renderAnalyzing = () => (
        <div className="text-center py-32 flex flex-col items-center animate-in fade-in zoom-in duration-300">
            <Loader2 size={80} className="text-brand-orange animate-spin mb-8" />
            <h2 className="text-4xl font-extrabold text-slate-900 mb-4 tracking-tight uppercase">{loadingState.title}</h2>
            <p className="text-xl text-slate-500 font-light">{loadingState.subtitle}</p>
        </div>
    );

    // Success State
    const renderSuccess = () => (
        <div className="max-w-2xl mx-auto py-12 px-4 animate-in fade-in slide-in-from-bottom-8 duration-500">
            <div className="text-center mb-10">
                <div className="w-24 h-24 bg-green-100 text-green-600 rounded-full flex items-center justify-center mx-auto mb-6 shadow-xl shadow-green-900/10">
                    <CheckCircle size={48} strokeWidth={3} />
                </div>
                <h1 className="text-4xl md:text-5xl font-extrabold text-slate-900 mb-4 uppercase tracking-tight">Your Appointment Is Scheduled!</h1>
                <p className="text-xl text-slate-500 font-light">We’ve sent a detailed receipt and confirmation to your email.</p>
            </div>

            {/* Details Card */}
            <div className="bg-white rounded-2xl border border-slate-200 shadow-xl overflow-hidden mb-8">
                <div className="bg-slate-50 border-b border-slate-100 p-6 flex justify-between items-center">
                    <span className="text-sm font-bold text-slate-400 uppercase tracking-widest">Booking ID</span>
                    <span className="text-lg font-bold text-slate-900">#JR-{Math.floor(Math.random() * 9000) + 1000}-X</span>
                </div>
                <div className="p-8 space-y-6">
                    <div className="flex items-start gap-4">
                        <div className="w-12 h-12 bg-orange-100 text-brand-orange rounded-xl flex items-center justify-center shrink-0">
                            <Calendar size={24} />
                        </div>
                        <div>
                            <p className="text-sm font-bold text-slate-400 uppercase mb-1">Date & Time</p>
                            <p className="text-xl font-bold text-slate-900">{bookingData.date || 'Jan 12, 2026'}</p>
                            <p className="text-slate-600">{bookingData.timeSlot || '12pm - 4pm'}</p>
                        </div>
                    </div>

                    <div className="flex items-start gap-4">
                        <div className="w-12 h-12 bg-blue-100 text-blue-600 rounded-xl flex items-center justify-center shrink-0">
                            <MapPin size={24} />
                        </div>
                        <div>
                            <p className="text-sm font-bold text-slate-400 uppercase mb-1">PickUp Location</p>
                            <p className="text-xl font-bold text-slate-900">{bookingData.address || '123 Example St, City, ST'}</p>
                        </div>
                    </div>
                </div>

                {/* "What Happens Next?" Blue Box */}
                <div className="bg-blue-50 p-8 border-t border-blue-100">
                    <div className="flex gap-4">
                        <div className="shrink-0 mt-1">
                            <div className="w-10 h-10 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center">
                                <Bell size={20} />
                            </div>
                        </div>
                        <div>
                            <h4 className="text-lg font-bold text-blue-900 mb-2">What happens next?</h4>
                            <p className="text-blue-700 leading-relaxed">
                                Sit tight! Our team has received your request. We will give you a call <strong>15 minutes before arrival</strong> to confirm entry instructions.
                            </p>
                        </div>
                    </div>
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Button onClick={addToCalendar} variant="outline" className="h-16 rounded-full border-slate-300 text-slate-700 font-bold text-lg hover:bg-slate-50 transition-colors">
                    Add to Calendar
                </Button>
                <Link href="/" className="w-full">
                    <Button className="w-full h-16 rounded-full bg-slate-900 text-white font-bold text-lg hover:bg-slate-800 shadow-xl shadow-slate-900/20 transition-all">
                        Return Home
                    </Button>
                </Link>
            </div>

            <div className="text-center mt-12 pb-8">
                <p className="text-slate-400 text-sm">Need to make changes? Call us at <a href="tel:8327936566" className="hover:text-slate-900"><span className="text-slate-600 font-bold">(832) 793-6566</span></a></p>
            </div>
        </div>
    );

    return (
        <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
            <Navbar />

            <main className="flex-grow pt-32 pb-20 px-4">
                {view === 'calculator' && renderCalculator()}
                {view === 'analyzing' && renderAnalyzing()}
                {view === 'receipt' && renderReceipt()}
                {view === 'scheduler' && renderScheduler()}
                {view === 'waiver' && (
                    <LiabilityWaiver
                        onAccept={handleWaiverAccept}
                        onBack={() => setView('scheduler')}
                    />
                )}
                {view === 'success' && renderSuccess()}

                <BookingModal
                    isOpen={isModalOpen}
                    onClose={() => setIsModalOpen(false)}
                    quoteRange={`$${grandTotal.min} - $${grandTotal.max}`}
                    junkDetails={`Total Volume: ${grandTotal.volume.toFixed(1)} cu. yards (${grandTotal.count} Piles)`}
                    initialName={`${searchParams.get('firstName') || ''} ${searchParams.get('lastName') || ''}`.trim()}
                    initialEmail={searchParams.get('email') || ''}
                    initialPhone={searchParams.get('phone') || ''}
                    leadId={searchParams.get('leadId') || ''}

                    images={bookingData.selectedImages}
                />
            </main>

            <Footer />
        </div>
    );
}

// Default export with Suspense boundary for useSearchParams
export default function BookPage() {
    return (
        <Suspense fallback={<div className="min-h-screen flex items-center justify-center"><div className="animate-spin h-8 w-8 border-4 border-orange-500 border-t-transparent rounded-full"></div></div>}>
            <BookPageContent />
        </Suspense>
    );
}
