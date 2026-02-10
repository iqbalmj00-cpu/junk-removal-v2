"use client";

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { X, Calendar, Clock, MapPin, Phone, Mail, User, Loader2, CheckCircle2 } from 'lucide-react';
import { trackEvent } from '@/lib/tracking';

interface BookingModalProps {
    isOpen: boolean;
    onClose: () => void;
    quoteRange: string;
    junkDetails: string;
    initialName?: string;
    initialEmail?: string;
    initialPhone?: string;
    leadId?: string;
}

export default function BookingModal({ isOpen, onClose, quoteRange, junkDetails, initialName, initialEmail, initialPhone, leadId }: BookingModalProps) {
    const router = useRouter();
    const [formData, setFormData] = useState({
        name: initialName || '',
        phone: initialPhone || '',
        email: initialEmail || '',
        address: '',
        buildingType: 'Residential',
        stairsAccess: 'Ground Floor',
        date: '',
        time: ''
    });
    const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle');
    const [errorMessage, setErrorMessage] = useState('');
    const [bookingId, setBookingId] = useState<string>('');
    const [availableTimes, setAvailableTimes] = useState<string[]>([]);
    const [loadingTimes, setLoadingTimes] = useState(false);

    if (!isOpen) return null;

    const fetchAvailableTimes = async (date: string) => {
        if (!date) { setAvailableTimes([]); return; }
        setLoadingTimes(true);
        try {
            const res = await fetch(`/api/available-times?date=${date}`);
            const data = await res.json();
            if (data.success) setAvailableTimes(data.available);
        } catch (err) {
            setAvailableTimes(['08:00', '09:00', '10:00', '11:00', '12:00', '13:00', '14:00', '15:00', '16:00', '17:00']);
        } finally {
            setLoadingTimes(false);
        }
    };

    const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
        const { name, value } = e.target;
        setFormData(prev => ({ ...prev, [name]: value }));
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setStatus('loading');
        setErrorMessage('');

        try {
            console.log("Submitting booking...");
            const response = await fetch('/api/book-appointment', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    ...formData,
                    quoteRange,
                    junkDetails,
                    leadId,
                }),
            });

            const data = await response.json();
            console.log("Booking response:", data);

            if (data.success) {
                console.log("Redirecting to confirmation page");
                setStatus('success');

                // Track booking confirmed
                trackEvent('booking_confirmed', '/book/modal', {
                    bookingId: data.bookingId,
                    leadId,
                    date: formData.date,
                    time: formData.time,
                    quoteRange,
                });

                const params = new URLSearchParams({
                    bookingId: data.bookingId,
                    date: formData.date,
                    time: formData.time,
                    address: formData.address
                });

                router.push(`/booking-confirmed?${params.toString()}`);
                // Optional: onClose(); 
            } else {
                throw new Error(data.error || 'Failed to submit booking');
            }
        } catch (error: any) {
            console.error("Booking error:", error);
            setStatus('error');
            setErrorMessage(error.message || 'Something went wrong. Please try again.');
        }
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
            <div className="relative w-full max-w-lg bg-slate-900 border border-slate-700 rounded-xl shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">

                {/* Header */}
                <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-900/50">
                    <h2 className="text-xl font-bold text-white">
                        {status === 'loading' ? 'Processing...' : 'Complete Your Booking'}
                    </h2>
                    <button
                        onClick={onClose}
                        className="p-2 text-slate-400 hover:text-white transition-colors rounded-full hover:bg-slate-800"
                    >
                        <X className="w-5 h-5" />
                    </button>
                </div>

                {/* Content */}
                <div className="p-6">
                    <form onSubmit={handleSubmit} className="space-y-4">

                        {/* Quote Summary */}
                        <div className="p-4 bg-slate-800/50 rounded-lg border border-slate-700 mb-6">
                            <p className="text-sm text-slate-400">Estimated Quote</p>
                            <p className="text-lg font-bold text-brand-orange">{quoteRange}</p>
                            <p className="text-xs text-slate-500 mt-1 truncate">{junkDetails}</p>
                        </div>

                        {errorMessage && (
                            <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-500 text-sm">
                                {errorMessage}
                            </div>
                        )}

                        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                            <div className="col-span-1 sm:col-span-2 space-y-1">
                                <label className="text-sm font-medium text-slate-300">Full Name</label>
                                <div className="relative">
                                    <User className="absolute left-3 top-3 w-4 h-4 text-slate-500" />
                                    <input
                                        type="text"
                                        name="name"
                                        required
                                        value={formData.name}
                                        onChange={handleChange}
                                        className="w-full pl-10 pr-4 py-2.5 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-brand-orange/50 focus:border-brand-orange transition-all"
                                        placeholder="John Doe"
                                    />
                                </div>
                            </div>

                            <div className="space-y-1">
                                <label className="text-sm font-medium text-slate-300">Phone</label>
                                <div className="relative">
                                    <Phone className="absolute left-3 top-3 w-4 h-4 text-slate-500" />
                                    <input
                                        type="tel"
                                        name="phone"
                                        required
                                        value={formData.phone}
                                        onChange={handleChange}
                                        className="w-full pl-10 pr-4 py-2.5 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-brand-orange/50 focus:border-brand-orange transition-all"
                                        placeholder="(555) 123-4567"
                                    />
                                </div>
                            </div>

                            <div className="space-y-1">
                                <label className="text-sm font-medium text-slate-300">Email</label>
                                <div className="relative">
                                    <Mail className="absolute left-3 top-3 w-4 h-4 text-slate-500" />
                                    <input
                                        type="email"
                                        name="email"
                                        required
                                        value={formData.email}
                                        onChange={handleChange}
                                        className="w-full pl-10 pr-4 py-2.5 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-brand-orange/50 focus:border-brand-orange transition-all"
                                        placeholder="john@example.com"
                                    />
                                </div>
                            </div>

                            <div className="col-span-1 sm:col-span-2 space-y-1">
                                <label className="text-sm font-medium text-slate-300">Pickup Address</label>
                                <div className="relative">
                                    <MapPin className="absolute left-3 top-3 w-4 h-4 text-slate-500" />
                                    <input
                                        type="text"
                                        name="address"
                                        required
                                        value={formData.address}
                                        onChange={handleChange}
                                        className="w-full pl-10 pr-4 py-2.5 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-brand-orange/50 focus:border-brand-orange transition-all"
                                        placeholder="123 Clean St, City, Zip"
                                    />
                                </div>
                            </div>

                            <div className="space-y-1">
                                <label className="text-sm font-medium text-slate-300">Preferred Date</label>
                                <div className="relative">
                                    <Calendar className="absolute left-3 top-3 w-4 h-4 text-slate-500" />
                                    <input
                                        type="date"
                                        name="date"
                                        required
                                        min={new Date().toISOString().split('T')[0]}
                                        value={formData.date}
                                        onChange={(e) => {
                                            handleChange(e);
                                            setFormData(prev => ({ ...prev, time: '' }));
                                            fetchAvailableTimes(e.target.value);
                                        }}
                                        className="w-full pl-10 pr-4 py-2.5 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-brand-orange/50 focus:border-brand-orange transition-all [color-scheme:dark]"
                                    />
                                </div>
                            </div>

                            <div className="space-y-1">
                                <label className="text-sm font-medium text-slate-300">Available Time</label>
                                <div className="relative">
                                    <Clock className="absolute left-3 top-3 w-4 h-4 text-slate-500" />
                                    <select
                                        name="time"
                                        required
                                        disabled={!formData.date || loadingTimes}
                                        value={formData.time}
                                        onChange={handleChange}
                                        className="w-full pl-10 pr-4 py-2.5 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-brand-orange/50 focus:border-brand-orange transition-all appearance-none disabled:opacity-50 disabled:cursor-not-allowed"
                                    >
                                        <option value="" disabled>{loadingTimes ? 'Loading...' : !formData.date ? 'Select a date first' : availableTimes.length === 0 ? 'No availability' : 'Select Time'}</option>
                                        {availableTimes.map((slot) => {
                                            const hour = parseInt(slot.split(':')[0], 10);
                                            const ampm = hour >= 12 ? 'PM' : 'AM';
                                            const displayHour = hour > 12 ? hour - 12 : hour === 0 ? 12 : hour;
                                            return <option key={slot} value={slot}>{`${displayHour}:00 ${ampm}`}</option>;
                                        })}
                                    </select>
                                </div>
                            </div>
                        </div>

                        <div className="pt-4">
                            <button
                                type="submit"
                                disabled={status === 'loading'}
                                className="w-full py-3.5 bg-brand-orange text-white font-bold rounded-lg hover:bg-orange-600 focus:ring-4 focus:ring-brand-orange/30 disabled:opacity-70 disabled:cursor-not-allowed transition-all shadow-lg shadow-brand-orange/20 flex items-center justify-center"
                            >
                                {status === 'loading' ? (
                                    <>
                                        <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                                        Processing...
                                    </>
                                ) : (
                                    "Confirm Booking"
                                )}
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    );
}
