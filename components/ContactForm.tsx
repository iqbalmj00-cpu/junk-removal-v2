'use client';

import { useState } from 'react';
import { Send, CheckCircle, AlertCircle } from 'lucide-react';

interface FormState {
    name: string;
    email: string;
    phone: string;
    message: string;
}

export function ContactForm() {
    const [form, setForm] = useState<FormState>({ name: '', email: '', phone: '', message: '' });
    const [status, setStatus] = useState<'idle' | 'sending' | 'sent' | 'error'>('idle');

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setStatus('sending');

        try {
            const res = await fetch('/api/contact', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(form),
            });

            if (!res.ok) throw new Error('Failed to send');
            setStatus('sent');
            setForm({ name: '', email: '', phone: '', message: '' });
        } catch {
            setStatus('error');
        }
    };

    if (status === 'sent') {
        return (
            <div className="bg-green-50 border border-green-200 rounded-2xl p-10 text-center">
                <CheckCircle className="w-12 h-12 text-green-500 mx-auto mb-4" />
                <h3 className="text-2xl font-bold text-slate-900 mb-2">Message Sent!</h3>
                <p className="text-slate-600">We&apos;ll get back to you as soon as possible.</p>
                <button
                    onClick={() => setStatus('idle')}
                    className="mt-6 text-brand-orange font-bold hover:underline"
                >
                    Send another message
                </button>
            </div>
        );
    }

    return (
        <form onSubmit={handleSubmit} className="space-y-6">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                <div>
                    <label htmlFor="contact-name" className="block text-sm font-bold text-slate-700 mb-2">
                        Full Name *
                    </label>
                    <input
                        id="contact-name"
                        type="text"
                        required
                        value={form.name}
                        onChange={(e) => setForm({ ...form, name: e.target.value })}
                        className="w-full px-4 py-3 rounded-lg border border-slate-300 focus:ring-2 focus:ring-brand-orange focus:border-brand-orange transition-colors text-slate-900"
                        placeholder="John Doe"
                    />
                </div>
                <div>
                    <label htmlFor="contact-email" className="block text-sm font-bold text-slate-700 mb-2">
                        Email Address *
                    </label>
                    <input
                        id="contact-email"
                        type="email"
                        required
                        value={form.email}
                        onChange={(e) => setForm({ ...form, email: e.target.value })}
                        className="w-full px-4 py-3 rounded-lg border border-slate-300 focus:ring-2 focus:ring-brand-orange focus:border-brand-orange transition-colors text-slate-900"
                        placeholder="john@example.com"
                    />
                </div>
            </div>
            <div>
                <label htmlFor="contact-phone" className="block text-sm font-bold text-slate-700 mb-2">
                    Phone Number
                </label>
                <input
                    id="contact-phone"
                    type="tel"
                    value={form.phone}
                    onChange={(e) => setForm({ ...form, phone: e.target.value })}
                    className="w-full px-4 py-3 rounded-lg border border-slate-300 focus:ring-2 focus:ring-brand-orange focus:border-brand-orange transition-colors text-slate-900"
                    placeholder="(832) 555-0100"
                />
            </div>
            <div>
                <label htmlFor="contact-message" className="block text-sm font-bold text-slate-700 mb-2">
                    Message *
                </label>
                <textarea
                    id="contact-message"
                    required
                    rows={5}
                    value={form.message}
                    onChange={(e) => setForm({ ...form, message: e.target.value })}
                    className="w-full px-4 py-3 rounded-lg border border-slate-300 focus:ring-2 focus:ring-brand-orange focus:border-brand-orange transition-colors text-slate-900 resize-none"
                    placeholder="Tell us about your junk removal needs..."
                />
            </div>

            {status === 'error' && (
                <div className="flex items-center gap-2 text-red-600 bg-red-50 px-4 py-3 rounded-lg border border-red-200">
                    <AlertCircle className="w-5 h-5 flex-shrink-0" />
                    <span className="text-sm font-medium">Something went wrong. Please try again or call us directly.</span>
                </div>
            )}

            <button
                type="submit"
                disabled={status === 'sending'}
                className="w-full bg-brand-orange hover:bg-orange-600 text-white font-bold py-4 px-8 rounded-full text-lg transition-all shadow-lg shadow-orange-900/20 flex items-center justify-center gap-2 disabled:opacity-60 disabled:cursor-not-allowed"
            >
                {status === 'sending' ? (
                    <>
                        <svg className="animate-spin w-5 h-5" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                        </svg>
                        Sending...
                    </>
                ) : (
                    <>
                        <Send className="w-5 h-5" />
                        Send Message
                    </>
                )}
            </button>
        </form>
    );
}
