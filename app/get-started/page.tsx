'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Navbar } from '@/components/Navbar';
import { Footer } from '@/components/Footer';
import { Mail, Smartphone, ArrowRight } from 'lucide-react';
import Link from 'next/link';
import { trackEvent } from '@/lib/tracking';

export default function GetStartedPage() {
    const router = useRouter();
    const [firstName, setFirstName] = useState('');
    const [lastName, setLastName] = useState('');
    const [email, setEmail] = useState('');
    const [phone, setPhone] = useState('');
    const [errors, setErrors] = useState<Record<string, string>>({});

    const validate = () => {
        const newErrors: Record<string, string> = {};
        if (!firstName.trim()) newErrors.firstName = 'First name is required';
        if (!lastName.trim()) newErrors.lastName = 'Last name is required';
        if (!email.trim()) {
            newErrors.email = 'Email is required';
        } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
            newErrors.email = 'Please enter a valid email';
        }
        if (!phone.trim()) {
            newErrors.phone = 'Phone number is required';
        } else if (phone.replace(/\D/g, '').length < 10) {
            newErrors.phone = 'Please enter a valid phone number';
        }
        setErrors(newErrors);
        return Object.keys(newErrors).length === 0;
    };

    const [submitting, setSubmitting] = useState(false);

    const handleContinue = async () => {
        if (!validate()) return;
        setSubmitting(true);

        const leadData = {
            firstName: firstName.trim(),
            lastName: lastName.trim(),
            email: email.trim(),
            phone: phone.trim(),
        };

        // Save lead to Google Sheets and capture leadId
        let leadId = '';
        try {
            const res = await fetch('/api/lead', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(leadData),
            });
            const data = await res.json();
            if (data.success && data.leadId) {
                leadId = data.leadId;
                // Track lead creation
                trackEvent('form_submit', '/get-started', {
                    leadId,
                    name: `${leadData.firstName} ${leadData.lastName}`,
                    email: leadData.email,
                    phone: leadData.phone,
                });
                // Send lead to dashboard
                if (typeof window !== 'undefined' && (window as any).syj?.sendLead) {
                    (window as any).syj.sendLead({
                        name: `${leadData.firstName} ${leadData.lastName}`,
                        email: leadData.email,
                        phone: leadData.phone,
                        source: 'website_form',
                    });
                }
            }
        } catch (err) {
            console.error('Lead capture failed:', err);
        }

        // Also send to CRM — capture leadId for progressive updates
        let crmLeadId = '';
        try {
            const crmRes = await fetch('/api/crm', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name: `${leadData.firstName} ${leadData.lastName}`,
                    phone: leadData.phone,
                    email: leadData.email,
                    website_honeypot: '',
                }),
            });
            if (crmRes.ok) {
                const crmData = await crmRes.json();
                crmLeadId = crmData.leadId || '';
                console.log('[CRM] Initial lead created:', crmLeadId);
            }
        } catch (err) {
            console.error('[CRM] Lead submission error:', err);
        }

        const params = new URLSearchParams(leadData);
        if (leadId) {
            params.set('leadId', leadId);
        }
        if (crmLeadId) {
            params.set('crmLeadId', crmLeadId);
        }
        router.push(`/book?${params.toString()}`);
    };

    const formatPhone = (value: string) => {
        const digits = value.replace(/\D/g, '');
        if (digits.length <= 3) return digits;
        if (digits.length <= 6) return `(${digits.slice(0, 3)}) ${digits.slice(3)}`;
        return `(${digits.slice(0, 3)}) ${digits.slice(3, 6)}-${digits.slice(6, 10)}`;
    };

    return (
        <div className="min-h-screen bg-slate-50 flex flex-col pt-28 font-sans">
            <Navbar />

            <main className="flex-grow flex flex-col items-center justify-center px-4 sm:px-6 py-16">
                {/* Header */}
                <div className="text-center mb-10">
                    <h1 className="text-4xl lg:text-5xl font-extrabold text-slate-900 mb-4 tracking-tight">
                        LET&apos;S GET STARTED
                    </h1>
                    <p className="text-slate-500 text-lg">
                        Enter your details below to begin your free quote.
                    </p>
                </div>

                {/* Form Card */}
                <div className="w-full max-w-2xl bg-white rounded-2xl shadow-lg border border-slate-100 p-8 sm:p-10">
                    {/* Name Row */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 mb-6">
                        <div>
                            <label className="block text-sm font-bold text-slate-800 mb-2">First Name</label>
                            <input
                                type="text"
                                placeholder="Jane"
                                value={firstName}
                                onChange={(e) => setFirstName(e.target.value)}
                                className={`w-full px-4 py-3.5 rounded-xl border ${errors.firstName ? 'border-red-400' : 'border-slate-200'} bg-slate-50 text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-brand-orange/30 focus:border-brand-orange transition-all`}
                            />
                            {errors.firstName && <p className="text-red-500 text-xs mt-1">{errors.firstName}</p>}
                        </div>
                        <div>
                            <label className="block text-sm font-bold text-slate-800 mb-2">Last Name</label>
                            <input
                                type="text"
                                placeholder="Doe"
                                value={lastName}
                                onChange={(e) => setLastName(e.target.value)}
                                className={`w-full px-4 py-3.5 rounded-xl border ${errors.lastName ? 'border-red-400' : 'border-slate-200'} bg-slate-50 text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-brand-orange/30 focus:border-brand-orange transition-all`}
                            />
                            {errors.lastName && <p className="text-red-500 text-xs mt-1">{errors.lastName}</p>}
                        </div>
                    </div>

                    {/* Email */}
                    <div className="mb-6">
                        <label className="block text-sm font-bold text-slate-800 mb-2">Email Address</label>
                        <div className="relative">
                            <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                            <input
                                type="email"
                                placeholder="jane@example.com"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                className={`w-full pl-12 pr-4 py-3.5 rounded-xl border ${errors.email ? 'border-red-400' : 'border-slate-200'} bg-slate-50 text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-brand-orange/30 focus:border-brand-orange transition-all`}
                            />
                        </div>
                        {errors.email && <p className="text-red-500 text-xs mt-1">{errors.email}</p>}
                    </div>

                    {/* Phone */}
                    <div className="mb-8">
                        <label className="block text-sm font-bold text-slate-800 mb-2">Phone Number</label>
                        <div className="relative">
                            <Smartphone className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                            <input
                                type="tel"
                                placeholder="(555) 123-4567"
                                value={phone}
                                onChange={(e) => setPhone(formatPhone(e.target.value))}
                                className={`w-full pl-12 pr-4 py-3.5 rounded-xl border ${errors.phone ? 'border-red-400' : 'border-slate-200'} bg-slate-50 text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-brand-orange/30 focus:border-brand-orange transition-all`}
                            />
                        </div>
                        {errors.phone && <p className="text-red-500 text-xs mt-1">{errors.phone}</p>}
                    </div>

                    {/* Submit Button */}
                    <button
                        onClick={handleContinue}
                        disabled={submitting}
                        data-track="book_now"
                        className="w-full py-4 rounded-full bg-brand-orange text-white font-bold text-lg tracking-wide hover:bg-orange-600 active:scale-[0.98] transition-all shadow-lg shadow-orange-500/25 flex items-center justify-center gap-3 disabled:opacity-60 disabled:cursor-not-allowed"
                    >
                        {submitting ? 'SAVING...' : 'CONTINUE TO PHOTO UPLOAD'}
                        {!submitting && <ArrowRight className="w-5 h-5" />}
                    </button>
                </div>

                {/* Legal Disclaimer */}
                <p className="text-center text-sm text-slate-400 mt-8">
                    By clicking continue, you agree to our{' '}
                    <Link href="/legal#terms" className="text-brand-orange hover:underline">Terms of Service</Link>
                    {' '}and{' '}
                    <Link href="/legal#privacy" className="text-brand-orange hover:underline">Privacy Policy</Link>.
                </p>
            </main>

            <Footer />
        </div>
    );
}
