import { Metadata } from 'next';
import Link from 'next/link';
import { CheckCircle, Calendar, MapPin, Phone, Home, ArrowRight } from 'lucide-react';
import { Navbar } from '@/components/Navbar';
import { Footer } from '@/components/Footer';

export const metadata: Metadata = {
    title: 'Booking Confirmed | Clean Sweep Junk Removal',
    description: 'Your junk removal appointment has been confirmed. We will contact you before arrival.',
    robots: { index: false, follow: false },
};

export default function ThankYouPage({
    searchParams,
}: {
    searchParams: Promise<{ [key: string]: string | string[] | undefined }>;
}) {
    return <ThankYouContent searchParamsPromise={searchParams} />;
}

async function ThankYouContent({
    searchParamsPromise,
}: {
    searchParamsPromise: Promise<{ [key: string]: string | string[] | undefined }>;
}) {
    const params = await searchParamsPromise;
    const bookingId = (params.bookingId as string) || '';
    const date = (params.date as string) || '';
    const time = (params.time as string) || '';
    const address = (params.address as string) || '';
    const name = (params.name as string) || '';

    // Format time for display
    let timeDisplay = time;
    if (time && time.includes(':')) {
        const hour = parseInt(time.split(':')[0], 10);
        const ampm = hour >= 12 ? 'PM' : 'AM';
        const displayHour = hour > 12 ? hour - 12 : hour === 0 ? 12 : hour;
        timeDisplay = `${displayHour}:00 ${ampm}`;
    }

    return (
        <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
            <Navbar />

            <main className="flex-grow pt-32 pb-20 px-4">
                <div className="max-w-xl mx-auto">

                    {/* Success Icon */}
                    <div className="text-center mb-10">
                        <div className="w-24 h-24 bg-green-100 text-green-600 rounded-full flex items-center justify-center mx-auto mb-6 shadow-xl shadow-green-900/10 animate-in zoom-in duration-500">
                            <CheckCircle className="w-12 h-12" strokeWidth={2.5} />
                        </div>
                        <h1 className="text-4xl md:text-5xl font-extrabold text-slate-900 mb-4 tracking-tight">
                            Booking Confirmed!
                        </h1>
                        {name && (
                            <p className="text-xl text-slate-500 font-light">
                                Thank you, <strong className="text-slate-700">{name}</strong>. We&apos;ve received your request.
                            </p>
                        )}
                    </div>

                    {/* Booking Details Card */}
                    <div className="bg-white rounded-2xl shadow-xl border border-slate-100 overflow-hidden mb-8">
                        {bookingId && (
                            <div className="bg-slate-50 border-b border-slate-100 px-8 py-4 flex justify-between items-center">
                                <span className="text-sm font-bold text-slate-400 uppercase tracking-widest">Booking ID</span>
                                <span className="text-lg font-bold text-slate-900 font-mono">{bookingId}</span>
                            </div>
                        )}

                        <div className="p-8 space-y-6">
                            {date && (
                                <div className="flex items-start gap-4">
                                    <div className="w-12 h-12 bg-orange-100 text-brand-orange rounded-xl flex items-center justify-center shrink-0">
                                        <Calendar className="w-6 h-6" />
                                    </div>
                                    <div>
                                        <p className="text-sm font-bold text-slate-400 uppercase mb-1">Date & Time</p>
                                        <p className="text-xl font-bold text-slate-900">{date}</p>
                                        {timeDisplay && <p className="text-slate-600">{timeDisplay}</p>}
                                    </div>
                                </div>
                            )}

                            {address && (
                                <div className="flex items-start gap-4">
                                    <div className="w-12 h-12 bg-blue-100 text-blue-600 rounded-xl flex items-center justify-center shrink-0">
                                        <MapPin className="w-6 h-6" />
                                    </div>
                                    <div>
                                        <p className="text-sm font-bold text-slate-400 uppercase mb-1">Pickup Location</p>
                                        <p className="text-xl font-bold text-slate-900">{address}</p>
                                    </div>
                                </div>
                            )}
                        </div>

                        {/* What Happens Next */}
                        <div className="bg-blue-50 p-8 border-t border-blue-100">
                            <h3 className="text-lg font-bold text-blue-900 mb-3">What happens next?</h3>
                            <ul className="space-y-3 text-blue-700">
                                <li className="flex items-start gap-3">
                                    <CheckCircle className="w-5 h-5 text-blue-500 mt-0.5 shrink-0" />
                                    <span>Our team is reviewing your request and preparing a crew.</span>
                                </li>
                                <li className="flex items-start gap-3">
                                    <Phone className="w-5 h-5 text-blue-500 mt-0.5 shrink-0" />
                                    <span>We&apos;ll call you <strong>15 minutes before arrival</strong> to confirm entry.</span>
                                </li>
                                <li className="flex items-start gap-3">
                                    <CheckCircle className="w-5 h-5 text-blue-500 mt-0.5 shrink-0" />
                                    <span>Final pricing is confirmed on-site before we start. No surprises.</span>
                                </li>
                            </ul>
                        </div>
                    </div>

                    {/* Action Buttons */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-8">
                        <a
                            href="tel:8327936566"
                            className="flex items-center justify-center gap-2 h-14 rounded-full border-2 border-slate-200 text-slate-700 font-bold text-lg hover:bg-slate-100 transition-colors"
                        >
                            <Phone className="w-5 h-5" />
                            Call Us
                        </a>
                        <Link
                            href="/"
                            className="flex items-center justify-center gap-2 h-14 rounded-full bg-slate-900 text-white font-bold text-lg hover:bg-slate-800 shadow-xl shadow-slate-900/20 transition-all"
                        >
                            <Home className="w-5 h-5" />
                            Return Home
                        </Link>
                    </div>

                    {/* Need changes */}
                    <div className="text-center">
                        <p className="text-slate-400 text-sm">
                            Need to reschedule?{' '}
                            <a href="tel:8327936566" className="text-brand-orange font-semibold hover:text-orange-600 transition-colors">
                                Call (832) 793-6566
                            </a>
                        </p>
                    </div>
                </div>
            </main>

            <Footer />
        </div>
    );
}
