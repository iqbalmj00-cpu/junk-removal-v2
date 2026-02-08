'use client';

import { useState } from 'react';
import { Navbar } from '@/components/Navbar';
import { Footer } from '@/components/Footer';
import { Scale, MessageSquare, Shield, Mail, Phone } from 'lucide-react';

const sections = [
    { id: 'terms', label: 'Terms of Service' },
    { id: 'sms', label: 'SMS & Communications' },
    { id: 'privacy', label: 'Privacy Policy' },
    { id: 'contact', label: 'Contact Us' },
];

export default function LegalPage() {
    const [activeSection, setActiveSection] = useState('terms');

    const scrollToSection = (id: string) => {
        setActiveSection(id);
        const el = document.getElementById(id);
        if (el) {
            el.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    };

    return (
        <div className="min-h-screen bg-slate-50 flex flex-col pt-28 font-sans">
            <Navbar />

            <main className="flex-grow">
                {/* Hero Header */}
                <section className="px-4 sm:px-6 lg:px-8 pt-12 pb-16">
                    <div className="max-w-7xl mx-auto">
                        <div className="border-l-4 border-brand-orange pl-6">
                            <p className="text-brand-orange font-semibold text-sm tracking-widest uppercase mb-2">Legal Information</p>
                            <h1 className="text-4xl lg:text-5xl font-extrabold text-slate-900 mb-4">LEGAL & POLICIES</h1>
                            <p className="text-slate-500 text-lg max-w-xl leading-relaxed">
                                Transparency is key to our professional junk removal services. Please review
                                our terms of service and privacy policies below to understand how we
                                operate and protect your data.
                            </p>
                        </div>
                    </div>
                </section>

                {/* Content with Sidebar */}
                <section className="px-4 sm:px-6 lg:px-8 pb-24">
                    <div className="max-w-7xl mx-auto">
                        <div className="grid grid-cols-1 lg:grid-cols-[220px_1fr] gap-12">

                            {/* Sidebar Navigation */}
                            <nav className="lg:sticky lg:top-32 lg:self-start">
                                <ul className="space-y-1">
                                    {sections.map((section) => (
                                        <li key={section.id}>
                                            <button
                                                onClick={() => scrollToSection(section.id)}
                                                className={`block w-full text-left px-4 py-2.5 text-sm font-medium rounded-lg transition-colors ${activeSection === section.id
                                                        ? 'text-slate-900 bg-slate-100 border-l-2 border-brand-orange'
                                                        : 'text-slate-500 hover:text-slate-900 hover:bg-slate-50'
                                                    }`}
                                            >
                                                {section.label}
                                            </button>
                                        </li>
                                    ))}
                                </ul>
                            </nav>

                            {/* Main Content */}
                            <div className="space-y-10">

                                {/* Terms of Service */}
                                <div
                                    id="terms"
                                    className="bg-white rounded-2xl shadow-sm border border-slate-200 p-8 sm:p-10"
                                >
                                    <div className="flex items-center gap-4 mb-8">
                                        <div className="w-12 h-12 bg-slate-100 rounded-xl flex items-center justify-center">
                                            <Scale className="w-6 h-6 text-slate-700" />
                                        </div>
                                        <h2 className="text-2xl font-bold text-slate-900">Terms of Service</h2>
                                    </div>

                                    <div className="prose prose-slate max-w-none text-slate-600 leading-relaxed space-y-6">
                                        <p>
                                            Welcome to CleanSweep (&quot;Company&quot;, &quot;we&quot;, &quot;our&quot;, &quot;us&quot;). By accessing or using our website, services, or
                                            mobile applications, you agree to be bound by these Terms. If you disagree with any part of the terms, then
                                            you may not access the Service.
                                        </p>

                                        <div>
                                            <h3 className="text-lg font-bold text-slate-900 mb-2">1. Services Provided</h3>
                                            <p>
                                                CleanSweep provides professional junk removal, hauling, and disposal services. We reserve the right to
                                                refuse service for hazardous materials or items that pose a safety risk to our team. Quotes provided online
                                                are estimates and may be adjusted upon on-site inspection.
                                            </p>
                                        </div>

                                        <div>
                                            <h3 className="text-lg font-bold text-slate-900 mb-2">2. Scheduling & Cancellations</h3>
                                            <p>
                                                Bookings are subject to availability. Cancellations made less than 24 hours before the scheduled
                                                appointment may be subject to a cancellation fee. We strive to arrive within the scheduled window, but
                                                traffic and unforeseen circumstances may cause delays.
                                            </p>
                                        </div>

                                        <div>
                                            <h3 className="text-lg font-bold text-slate-900 mb-2">3. Payment Terms</h3>
                                            <p>
                                                Payment is due upon completion of the service unless otherwise agreed in writing. We accept major credit
                                                cards, cash, and digital payments. Late payments may incur interest charges.
                                            </p>
                                        </div>
                                    </div>
                                </div>

                                {/* Communications & SMS Policy */}
                                <div
                                    id="sms"
                                    className="bg-slate-900 rounded-2xl shadow-sm p-8 sm:p-10"
                                >
                                    <div className="flex items-center gap-4 mb-8">
                                        <div className="w-12 h-12 bg-brand-orange rounded-xl flex items-center justify-center">
                                            <MessageSquare className="w-6 h-6 text-white" />
                                        </div>
                                        <h2 className="text-2xl font-bold text-white">Communications & SMS Policy</h2>
                                    </div>

                                    <div className="text-slate-300 leading-relaxed space-y-6">
                                        <p>
                                            By providing your phone number to CleanSweep, creating an account, or requesting a quote, you
                                            expressly consent to receive non-marketing and marketing text messages (e.g., appointment
                                            confirmations, arrival notifications, service updates) from us at the mobile number provided.
                                        </p>

                                        <ul className="space-y-2 ml-1">
                                            <li className="flex items-start gap-2">
                                                <span className="text-brand-orange mt-1.5">•</span>
                                                <span>Consent is not a condition of purchase.</span>
                                            </li>
                                            <li className="flex items-start gap-2">
                                                <span className="text-brand-orange mt-1.5">•</span>
                                                <span>Msg & data rates may apply.</span>
                                            </li>
                                            <li className="flex items-start gap-2">
                                                <span className="text-brand-orange mt-1.5">•</span>
                                                <span>Message frequency varies.</span>
                                            </li>
                                            <li className="flex items-start gap-2">
                                                <span className="text-brand-orange mt-1.5">•</span>
                                                <span>Reply <strong className="text-white">STOP</strong> to unsubscribe at any time.</span>
                                            </li>
                                            <li className="flex items-start gap-2">
                                                <span className="text-brand-orange mt-1.5">•</span>
                                                <span>Reply <strong className="text-white">HELP</strong> for help.</span>
                                            </li>
                                        </ul>

                                        <p className="text-sm text-slate-400">
                                            See our{' '}
                                            <button
                                                onClick={() => scrollToSection('privacy')}
                                                className="text-brand-orange underline hover:text-orange-400 transition-colors"
                                            >
                                                Privacy Policy
                                            </button>{' '}
                                            for more information on how we handle your data.
                                        </p>
                                    </div>
                                </div>

                                {/* Privacy Policy */}
                                <div
                                    id="privacy"
                                    className="bg-white rounded-2xl shadow-sm border border-slate-200 p-8 sm:p-10"
                                >
                                    <div className="flex items-center gap-4 mb-8">
                                        <div className="w-12 h-12 bg-amber-50 rounded-xl flex items-center justify-center">
                                            <Shield className="w-6 h-6 text-amber-600" />
                                        </div>
                                        <h2 className="text-2xl font-bold text-slate-900">Privacy Policy</h2>
                                    </div>

                                    <div className="prose prose-slate max-w-none text-slate-600 leading-relaxed space-y-6">
                                        <p>
                                            Your privacy is important to us. It is CleanSweep&apos;s policy to respect your privacy regarding any information
                                            we may collect from you across our website.
                                        </p>

                                        <div>
                                            <h3 className="text-lg font-bold text-slate-900 mb-2">Information We Collect</h3>
                                            <p>
                                                We only ask for personal information when we truly need it to provide a service to you. We collect it by fair
                                                and lawful means, with your knowledge and consent. We also let you know why we&apos;re collecting it and how
                                                it will be used. Common data collected includes:
                                            </p>
                                            <ul className="mt-3 space-y-2 ml-1">
                                                <li className="flex items-start gap-2">
                                                    <span className="text-brand-orange mt-1.5">•</span>
                                                    <span>Name and contact information</span>
                                                </li>
                                                <li className="flex items-start gap-2">
                                                    <span className="text-brand-orange mt-1.5">•</span>
                                                    <span>Service location address</span>
                                                </li>
                                                <li className="flex items-start gap-2">
                                                    <span className="text-brand-orange mt-1.5">•</span>
                                                    <span>Payment details (processed securely)</span>
                                                </li>
                                            </ul>
                                        </div>

                                        <div>
                                            <h3 className="text-lg font-bold text-slate-900 mb-2">Data Retention</h3>
                                            <p>
                                                We only retain collected information for as long as necessary to provide you with your requested service.
                                                What data we store, we&apos;ll protect within commercially acceptable means to prevent loss and theft, as well
                                                as unauthorized access, disclosure, copying, use, or modification.
                                            </p>
                                        </div>

                                        <div>
                                            <h3 className="text-lg font-bold text-slate-900 mb-2">Sharing of Information</h3>
                                            <p>
                                                We do not share any personally identifying information publicly or with third-parties, except when required
                                                to by law.
                                            </p>
                                        </div>
                                    </div>
                                </div>

                                {/* Contact / Effective Date */}
                                <div
                                    id="contact"
                                    className="bg-white rounded-2xl shadow-sm border border-slate-200 p-8 sm:p-10"
                                >
                                    <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-8">
                                        <div>
                                            <h3 className="text-xl font-bold text-slate-900 mb-3">Have Legal Questions?</h3>
                                            <p className="text-slate-500 mb-6 max-w-md">
                                                If you have any questions about these Terms or our Privacy Policy,
                                                please contact our legal compliance team.
                                            </p>
                                            <div className="space-y-3">
                                                <a href="mailto:legal@sweepsite.com" className="flex items-center gap-3 text-slate-700 hover:text-brand-orange transition-colors">
                                                    <Mail className="w-4 h-4 text-brand-orange" />
                                                    <span className="text-sm font-medium">legal@sweepsite.com</span>
                                                </a>
                                                <a href="tel:+18327936566" className="flex items-center gap-3 text-slate-700 hover:text-brand-orange transition-colors">
                                                    <Phone className="w-4 h-4 text-brand-orange" />
                                                    <span className="text-sm font-medium">(832) 793-6566</span>
                                                </a>
                                            </div>
                                        </div>
                                        <div className="text-right">
                                            <p className="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1">Effective Date</p>
                                            <p className="text-xl font-bold text-slate-900">October 24, 2023</p>
                                        </div>
                                    </div>
                                </div>

                            </div>
                        </div>
                    </div>
                </section>
            </main>

            <Footer />
        </div>
    );
}
