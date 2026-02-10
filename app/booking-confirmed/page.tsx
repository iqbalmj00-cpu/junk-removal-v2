"use client";

import { useSearchParams, useRouter } from 'next/navigation';
import { Navbar } from '@/components/Navbar';
import { Footer } from '@/components/Footer';
import { Button } from '@/components/ui/Button';
import { CheckCircle2, Calendar, MapPin, Info, ArrowLeft } from 'lucide-react';
import Link from 'next/link';
import { Suspense, useEffect } from 'react';
import { trackEvent } from '@/lib/tracking';

function BookingConfirmedContent() {
    const searchParams = useSearchParams();
    const router = useRouter();

    const bookingId = searchParams.get('bookingId') || '#JR-PENDING';
    const date = searchParams.get('date') || '';
    const time = searchParams.get('time') || '';
    const address = searchParams.get('address') || '';

    // Track confirmation page view
    useEffect(() => {
        trackEvent('page_view', '/booking-confirmed', {
            bookingId,
            date,
            time,
        });
    }, []);

    // Create Google Calendar Link
    const googleCalendarUrl = `https://calendar.google.com/calendar/render?action=TEMPLATE&text=Junk+Removal+Appointment&dates=${date.replace(/-/g, '')}T${time.replace(/:/g, '')}00/${date.replace(/-/g, '')}T${parseInt(time.split(':')[0]) + 1}${time.split(':')[1]}00&details=Booking+ID:+${bookingId}+%0AAddress:+${encodeURIComponent(address)}&location=${encodeURIComponent(address)}`;

    return (
        <div className="min-h-screen bg-slate-50 flex flex-col font-sans pt-28">
            <Navbar />

            <main className="flex-grow flex items-center justify-center p-4 sm:p-6 lg:p-8">
                <div className="w-full max-w-3xl bg-white rounded-3xl shadow-xl overflow-hidden animate-in fade-in zoom-in-95 duration-500 border border-slate-100">

                    {/* Header */}
                    <div className="bg-white p-10 text-center border-b border-slate-100">
                        <div className="w-24 h-24 bg-green-50 rounded-full flex items-center justify-center mx-auto mb-6">
                            <CheckCircle2 className="w-12 h-12 text-green-500" />
                        </div>
                        <h1 className="text-3xl md:text-4xl font-extrabold text-slate-900 uppercase tracking-tight mb-2">
                            Your Appointment Is Scheduled!
                        </h1>
                        <p className="text-slate-500 text-lg">
                            We have sent a confirmation email to you.
                        </p>
                    </div>

                    {/* Details Grid */}
                    <div className="p-8 md:p-12">
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
                            {/* Booking ID */}
                            <div className="bg-slate-50 p-6 rounded-2xl border border-slate-200 text-center md:text-left">
                                <p className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-2">Booking ID</p>
                                <p className="text-xl font-mono font-bold text-brand-orange truncate">{bookingId}</p>
                            </div>

                            {/* Date & Time */}
                            <div className="bg-slate-50 p-6 rounded-2xl border border-slate-200 text-center md:text-left">
                                <p className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-2 flex items-center justify-center md:justify-start gap-1">
                                    <Calendar size={12} /> Date & Time
                                </p>
                                <p className="text-lg font-bold text-slate-900">{date}</p>
                                <p className="text-slate-500">{time}</p>
                            </div>

                            {/* Location */}
                            <div className="bg-slate-50 p-6 rounded-2xl border border-slate-200 text-center md:text-left">
                                <p className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-2 flex items-center justify-center md:justify-start gap-1">
                                    <MapPin size={12} /> Location
                                </p>
                                <p className="text-lg font-bold text-slate-900 truncate">{address}</p>
                            </div>
                        </div>

                        {/* Info Banner */}
                        <div className="bg-blue-50 border border-blue-100 rounded-2xl p-6 flex items-start gap-4 mb-10">
                            <Info className="text-blue-500 flex-shrink-0 mt-1" size={24} />
                            <div>
                                <h3 className="font-bold text-blue-900 text-lg mb-1">What Happens Next?</h3>
                                <p className="text-blue-700/80 leading-relaxed">
                                    Our team will review your details and call you 30 minutes before arrival. Please ensure the items are accessible.
                                </p>
                            </div>
                        </div>

                        {/* Buttons */}
                        <div className="flex flex-col sm:flex-row gap-4 justify-center">
                            <a href={googleCalendarUrl} target="_blank" rel="noopener noreferrer" className="w-full sm:w-auto">
                                <Button variant="outline" className="w-full border-2 border-slate-200 hover:border-slate-300 text-slate-700 hover:bg-slate-50 h-14 px-8 text-lg font-bold rounded-xl">
                                    <Calendar className="mr-2" size={20} /> Add to Calendar
                                </Button>
                            </a>

                            <Link href="/" className="w-full sm:w-auto">
                                <Button className="w-full bg-slate-900 hover:bg-black text-white h-14 px-8 text-lg font-bold rounded-xl shadow-lg shadow-slate-900/20">
                                    Return Home
                                </Button>
                            </Link>
                        </div>
                    </div>
                </div>
            </main>
            <Footer />
        </div>
    );
}

export default function BookingConfirmedPage() {
    return (
        <Suspense fallback={
            <div className="min-h-screen bg-slate-50 flex items-center justify-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-brand-orange"></div>
            </div>
        }>
            <BookingConfirmedContent />
        </Suspense>
    );
}
