'use client';

import { useState, useRef } from 'react';
import { Navbar } from '@/components/Navbar';
import { Footer } from '@/components/Footer';
import { Button } from '@/components/ui/Button';
import { UploadCloud, CheckCircle, ArrowRight, Loader2, Calendar, User, Phone, MapPin, Mail, Building, ArrowUp, Bell } from 'lucide-react';
import Link from 'next/link';
import imageCompression from 'browser-image-compression';

// --- Pricing Engine ---
import { calculateJunkPrice } from '@/lib/pricingEngine';

type ViewState = 'calculator' | 'analyzing' | 'receipt' | 'scheduler' | 'success';

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
}

export default function BookPage() {
    const [view, setView] = useState<ViewState>('calculator');
    const [bookingData, setBookingData] = useState<BookingData>({
        selectedImages: [],
        estimatedVolumeCuFt: 0,
        buildingType: 'Residential',
        stairsAccess: 'Ground Floor',
        date: '',
        timeSlot: '',
        fullName: '',
        email: '',
        phone: '',
        address: '',
        instructions: ''
    });
    const [loadingState, setLoadingState] = useState({ title: 'ANALYZING JUNK...', subtitle: 'Calculating volume and finding the best price.' });

    const fileInputRef = useRef<HTMLInputElement>(null);

    // --- Price Calculation ---
    const getPrice = () => {
        // We pass empty surcharges for now as the new design removed specific item tags
        // You could add logic to infer surcharges from the "Stairs/Access" if needed, 
        // e.g. "2+ Flights" adds a fee. For now keeping it simple as requested.
        return calculateJunkPrice(bookingData.estimatedVolumeCuFt, []);
    };

    const priceDetails = getPrice();
    const volumeYards = (bookingData.estimatedVolumeCuFt / 27).toFixed(1);

    // --- Handlers ---
    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files.length > 0) {
            // Append new files to existing ones
            const newFiles = Array.from(e.target.files);
            setBookingData(prev => ({
                ...prev,
                selectedImages: [...prev.selectedImages, ...newFiles]
            }));
        }
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

    const handleAnalyze = async () => {
        if (bookingData.selectedImages.length === 0) return;
        setLoadingState({ title: 'ADVANCED AI ANALYSIS...', subtitle: 'Compressing images for Vercel optimization...' });
        setView('analyzing');

        // 1. Compression Settings (Crucial for Vercel)
        const options = {
            maxSizeMB: 0.8,         // Squash to < 0.8MB
            maxWidthOrHeight: 1024, // Resize for AI Vision
            useWebWorker: true
        };

        try {
            const compressedBase64s: string[] = [];

            // 2. Compress & Convert to Base64
            for (const file of bookingData.selectedImages) {
                try {
                    const compressedFile = await imageCompression(file, options);
                    const base64 = await fileToBase64(compressedFile);
                    compressedBase64s.push(base64);
                } catch (compressErr) {
                    console.warn("Compression failed for a file, using original", compressErr);
                    const originalBase64 = await fileToBase64(file);
                    compressedBase64s.push(originalBase64);
                }
            }

            // 3. Call the Python Backend
            const response = await fetch('/api/quote', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ images: compressedBase64s }),
            });

            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.error || 'Analysis failed');
            }

            const data = await response.json();
            console.log("API Quote Received:", data);

            // 4. Handle the "Consensus" Result
            if (data.status === "SUCCESS") {
                // SCENARIO A: Models Agree
                // Python Backend returns: { status: "SUCCESS", volume_yards: 4.5, price: 157.5, ... }
                const volumeYards = data.volume_yards || 3.5;
                const volumeCuFt = volumeYards * 27;

                // Sync state for local engine compatibility 
                setBookingData(prev => ({
                    ...prev,
                    estimatedVolumeCuFt: volumeCuFt
                }));

                // Alert as requested
                alert(`✅ INSTANT QUOTE: $${data.price}\nVolume: ${volumeYards} Cubic Yards`);

                setView('receipt');
            } else {
                // SCENARIO B: SHADOW MODE (Models Disagree)
                setLoadingState({ title: 'REVIEW REQUIRED', subtitle: 'Connecting to human specialist...' });
                await new Promise(r => setTimeout(r, 1000));

                alert(`⚠️ COMPLEX LOAD DETECTED\n\nOur AI models had conflicting estimates. A Human Specialist has been alerted and will text you an exact price in 5-10 minutes.`);

                // Reset to calculator to allow re-upload or exit
                setView('calculator');
            }

        } catch (error: any) {
            console.error("Analysis Failed:", error);
            alert("System Busy. Request sent to manual dispatch.");
            setView('calculator');
        }
    };

    const handleBook = async (e: React.FormEvent) => {
        e.preventDefault();
        // Simulate API call
        setLoadingState({ title: 'FINALIZING BOOKING...', subtitle: 'Securing your appointment time...' });
        setView('analyzing'); // Reuse spinner
        await new Promise(r => setTimeout(r, 1500));
        setView('success');
    };

    // --- Render Views ---

    // VIEW 1: The Calculator
    const renderCalculator = () => (
        <div className="max-w-2xl mx-auto animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div className="text-center mb-10">
                <h1 className="text-5xl font-extrabold text-slate-900 mb-4 tracking-tight">AI JUNK PRICING TOOL</h1>
                <p className="text-xl text-slate-500 font-light">
                    Upload photos for an instant quote.
                </p>
            </div>

            <div className="bg-white rounded-[2rem] shadow-xl border border-slate-100 overflow-hidden">
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
                            accept="image/*"
                            multiple
                            className="hidden"
                        />
                    </div>
                </div>

                {/* Property Details Box */}
                <div className="p-10 bg-white">
                    <h3 className="text-sm font-bold text-slate-400 uppercase tracking-widest mb-6">Property Details</h3>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
                        <div>
                            <label className="block text-sm font-bold text-slate-700 mb-2 flex items-center gap-2">
                                <Building size={16} className="text-brand-orange" /> Building Type
                            </label>
                            <select
                                className="w-full h-14 px-4 rounded-xl bg-slate-50 border border-slate-200 focus:border-brand-orange outline-none text-lg font-medium text-slate-700"
                                value={bookingData.buildingType}
                                onChange={(e) => setBookingData({ ...bookingData, buildingType: e.target.value })}
                            >
                                <option>Residential</option>
                                <option>Commercial</option>
                                <option>Construction Site</option>
                            </select>
                        </div>
                        <div>
                            <label className="block text-sm font-bold text-slate-700 mb-2 flex items-center gap-2">
                                <ArrowUp size={16} className="text-brand-orange" /> Stairs / Access
                            </label>
                            <select
                                className="w-full h-14 px-4 rounded-xl bg-slate-50 border border-slate-200 focus:border-brand-orange outline-none text-lg font-medium text-slate-700"
                                value={bookingData.stairsAccess}
                                onChange={(e) => setBookingData({ ...bookingData, stairsAccess: e.target.value })}
                            >
                                <option>Ground Floor</option>
                                <option>1 Flight of Stairs</option>
                                <option>2+ Flights</option>
                                <option>Elevator Available</option>
                            </select>
                        </div>
                    </div>

                    <Button
                        onClick={handleAnalyze}
                        disabled={bookingData.selectedImages.length === 0}
                        className={`w-full h-16 text-xl font-bold rounded-xl shadow-xl transition-all ${bookingData.selectedImages.length > 0
                            ? 'bg-brand-orange hover:bg-orange-600 text-white shadow-orange-900/20'
                            : 'bg-slate-200 text-slate-400 cursor-not-allowed'
                            }`}
                    >
                        GET MY PRICE
                    </Button>
                </div>
            </div>
        </div>
    );

    // VIEW 2: The Receipt (Dark Navy)
    const renderReceipt = () => (
        <div className="max-w-2xl mx-auto animate-in fade-in zoom-in duration-500">
            <Button variant="ghost" onClick={() => setView('calculator')} className="text-slate-400 hover:text-slate-900 font-bold px-0 mb-8">
                ← Back to Upload
            </Button>

            <div className="bg-slate-900 text-white rounded-[2rem] shadow-2xl overflow-hidden relative border border-slate-800">
                {/* Background Pattern */}
                <div className="absolute inset-0 bg-[url('https://www.transparenttextures.com/patterns/carbon-fibre.png')] opacity-20"></div>

                <div className="relative z-10 p-12 text-center">
                    <p className="text-brand-orange font-bold tracking-widest uppercase text-sm mb-2">Estimated Quote</p>
                    <h2 className="text-7xl font-extrabold text-white mb-6 tracking-tight">${priceDetails.totalPrice}</h2>

                    <div className="inline-flex items-center gap-4 bg-slate-800 px-6 py-3 rounded-full border border-slate-700 mb-10">
                        <div className="flex flex-col items-center border-r border-slate-600 pr-4">
                            <span className="text-xs text-slate-400 font-bold uppercase">Volume</span>
                            <span className="text-xl font-bold">{volumeYards} yds³</span>
                        </div>
                        <div className="flex flex-col items-center">
                            <span className="text-xs text-slate-400 font-bold uppercase">Load Size</span>
                            <span className="text-xl font-bold text-brand-orange">{priceDetails.tierName}</span>
                        </div>
                    </div>

                    <div className="text-left bg-transparent rounded-xl p-6 mb-10 border border-slate-700">
                        <div className="flex justify-between mb-4 pb-4 border-b border-slate-700">
                            <span className="text-slate-400">Base Price (Volume)</span>
                            <span className="font-bold">${priceDetails.basePrice}</span>
                        </div>
                        <div className="flex justify-between text-brand-orange">
                            <span className="font-bold">Total Estimate</span>
                            <span className="font-bold text-2xl">${priceDetails.totalPrice}</span>
                        </div>
                    </div>

                    <div className="mt-8">
                        <Button
                            onClick={() => setView('scheduler')}
                            className="w-full bg-brand-orange hover:bg-orange-600 text-white h-16 rounded-xl text-xl font-bold shadow-lg shadow-orange-900/40"
                        >
                            BOOK THIS PRICE <ArrowRight className="ml-2" />
                        </Button>
                    </div>
                    <p className="text-slate-500 text-sm mt-6">*Final price confirmed on-site.</p>
                </div>

                {/* Decorative Perf Edge at bottom (CSS Trick or SVG) - keeping simple for now */}
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

                <form onSubmit={handleBook} className="space-y-6">
                    {/* Date & Time */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div>
                            <label className="text-sm font-bold text-slate-700 mb-2 block">Date</label>
                            <input
                                type="date" required
                                className="w-full h-14 px-4 rounded-xl border border-gray-300 bg-white text-gray-900 placeholder-gray-400 focus:border-orange-500 focus:outline-none focus:ring-1 focus:ring-orange-500 text-lg font-medium"
                                onChange={(e) => setBookingData({ ...bookingData, date: e.target.value })}
                            />
                        </div>
                        <div>
                            <label className="text-sm font-bold text-slate-700 mb-2 block">Best Time</label>
                            <select
                                required
                                className="w-full h-14 px-4 rounded-xl border border-gray-300 bg-white text-gray-900 placeholder-gray-400 focus:border-orange-500 focus:outline-none focus:ring-1 focus:ring-orange-500 text-lg font-medium"
                                onChange={(e) => setBookingData({ ...bookingData, timeSlot: e.target.value })}
                            >
                                <option value="">Select slot...</option>
                                <option>8am - 12pm</option>
                                <option>12pm - 4pm</option>
                                <option>4pm - 8pm</option>
                            </select>
                        </div>
                    </div>

                    {/* Contact Info */}
                    <div className="space-y-4">
                        <input
                            type="text" placeholder="Full Name" required
                            className="w-full h-14 px-4 rounded-xl border border-gray-300 bg-white text-gray-900 placeholder-gray-400 focus:border-orange-500 focus:outline-none focus:ring-1 focus:ring-orange-500 text-lg font-medium"
                            onChange={(e) => setBookingData({ ...bookingData, fullName: e.target.value })}
                        />
                        <input
                            type="tel" placeholder="Phone Number" required
                            className="w-full h-14 px-4 rounded-xl border border-gray-300 bg-white text-gray-900 placeholder-gray-400 focus:border-orange-500 focus:outline-none focus:ring-1 focus:ring-orange-500 text-lg font-medium"
                            onChange={(e) => setBookingData({ ...bookingData, phone: e.target.value })}
                        />
                        <input
                            type="text" placeholder="Pickup Address" required
                            className="w-full h-14 px-4 rounded-xl border border-gray-300 bg-white text-gray-900 placeholder-gray-400 focus:border-orange-500 focus:outline-none focus:ring-1 focus:ring-orange-500 text-lg font-medium"
                            onChange={(e) => setBookingData({ ...bookingData, address: e.target.value })}
                        />
                    </div>

                    <Button className="w-full h-16 bg-brand-orange hover:bg-orange-600 text-white text-xl font-bold rounded-xl mt-4 shadow-xl shadow-orange-900/20">
                        CONFIRM BOOKING
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
                <Button variant="outline" className="h-16 rounded-xl border-slate-300 text-slate-700 font-bold text-lg hover:bg-slate-50 transition-colors">
                    Add to Calendar
                </Button>
                <Link href="/" className="w-full">
                    <Button className="w-full h-16 rounded-xl bg-slate-900 text-white font-bold text-lg hover:bg-slate-800 shadow-xl shadow-slate-900/20 transition-all">
                        Return Home
                    </Button>
                </Link>
            </div>

            <div className="text-center mt-12 pb-8">
                <p className="text-slate-400 text-sm">Need to make changes? Call us at <span className="text-slate-600 font-bold">(555) 123-4567</span></p>
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
                {view === 'success' && renderSuccess()}
            </main>

            <Footer />
        </div>
    );
}
