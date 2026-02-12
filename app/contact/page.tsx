import { Metadata } from 'next';
import { Navbar } from '@/components/Navbar';
import { Footer } from '@/components/Footer';
import { ContactForm } from '@/components/ContactForm';
import { Mail, Phone, MapPin, Clock, CheckCircle } from 'lucide-react';

export const metadata: Metadata = {
    title: 'Contact Us | Clean Sweep Junk Removal Houston',
    description: 'Get in touch with Clean Sweep. Call (832) 793-6566 or fill out our contact form. Same-day junk removal in the Greater Houston area.',
};

export default function ContactPage() {
    return (
        <div className="min-h-screen bg-gray-50 flex flex-col font-sans">
            <Navbar />

            <main className="flex-grow pt-40 pb-32 px-4 sm:px-6 lg:px-8">
                <div className="max-w-7xl mx-auto">

                    {/* SECTION 1: HEADER (Top Left) */}
                    <div className="mb-20">
                        <div className="border-l-4 border-brand-orange pl-8 min-h-[140px] flex flex-col justify-center">
                            <h2 className="text-brand-orange font-bold text-sm uppercase tracking-widest mb-3">CONTACT US</h2>
                            <h1 className="text-6xl font-extrabold text-slate-900 mb-6 tracking-tight">GET IN TOUCH</h1>
                            <p className="text-2xl text-slate-500 max-w-3xl font-light leading-relaxed">
                                Ready to clear the clutter? Professional junk removal services at your disposal. We're here to answer any questions.
                            </p>
                        </div>
                    </div>

                    {/* SECTION 2: MAIN CONTENT GRID */}
                    <div className="grid grid-cols-1 lg:grid-cols-12 gap-16">

                        {/* LEFT COLUMN: The Form (7 cols) */}
                        <div className="lg:col-span-7">
                            <div className="bg-white p-10 md:p-12 rounded-2xl shadow-sm border border-slate-100">
                                <div className="flex items-center gap-4 mb-10">
                                    <div className="w-14 h-14 bg-orange-50 rounded-full flex items-center justify-center text-brand-orange">
                                        <Mail size={28} />
                                    </div>
                                    <h3 className="text-2xl font-bold text-slate-900">Send a Message</h3>
                                </div>

                                <ContactForm />
                            </div>
                        </div>

                        {/* RIGHT COLUMN: Info Stack & Map (5 cols) */}
                        <div className="lg:col-span-5 space-y-8">

                            {/* Card 1: Phone */}
                            <div className="bg-white p-8 rounded-2xl shadow-sm border border-slate-100 border-l-8 border-l-brand-orange hover:shadow-lg transition-all group">
                                <div className="flex items-start gap-6">
                                    <div className="w-14 h-14 bg-slate-100 rounded-full flex items-center justify-center text-slate-600 shrink-0 group-hover:bg-brand-orange group-hover:text-white transition-colors">
                                        <Phone size={28} />
                                    </div>
                                    <div>
                                        <h4 className="text-sm font-bold text-slate-400 uppercase tracking-widest mb-1">CALL US</h4>
                                        <a href="tel:8327936566" className="block hover:opacity-80 transition-opacity">
                                            <p className="text-2xl font-bold text-slate-900 group-hover:text-brand-orange transition-colors">(832) 793-6566</p>
                                        </a>
                                        <p className="text-sm text-brand-orange font-bold mt-2 flex items-center bg-orange-50 inline-block px-2 py-1 rounded">
                                            <CheckCircle size={14} className="mr-1.5" /> Available 24/7
                                        </p>
                                    </div>
                                </div>
                            </div>

                            {/* Card 2: Email */}
                            <div className="bg-white p-8 rounded-2xl shadow-sm border border-slate-100 border-l-8 border-l-brand-orange hover:shadow-lg transition-all group">
                                <div className="flex items-start gap-6">
                                    <div className="w-14 h-14 bg-slate-100 rounded-full flex items-center justify-center text-slate-600 shrink-0 group-hover:bg-brand-orange group-hover:text-white transition-colors">
                                        <Mail size={28} />
                                    </div>
                                    <div>
                                        <h4 className="text-sm font-bold text-slate-400 uppercase tracking-widest mb-1">EMAIL US</h4>
                                        <p className="text-xl font-bold text-slate-900 break-all group-hover:text-brand-orange transition-colors">clean@sweepsite.com</p>
                                    </div>
                                </div>
                            </div>

                            {/* Card 3: Hours */}
                            <div className="bg-white p-8 rounded-2xl shadow-sm border border-slate-100 border-l-8 border-l-brand-orange hover:shadow-lg transition-all group">
                                <div className="flex items-start gap-6">
                                    <div className="w-14 h-14 bg-slate-100 rounded-full flex items-center justify-center text-slate-600 shrink-0 group-hover:bg-brand-orange group-hover:text-white transition-colors">
                                        <Clock size={28} />
                                    </div>
                                    <div>
                                        <h4 className="text-sm font-bold text-slate-400 uppercase tracking-widest mb-1">OPERATING HOURS</h4>
                                        <p className="text-slate-900 font-bold text-lg">Mon - Sat: 8:00 AM - 8:00 PM</p>
                                        <p className="text-slate-500 font-medium mt-1">Sunday: By Appointment</p>
                                    </div>
                                </div>
                            </div>

                            {/* Map Graphic */}
                            <div className="h-80 rounded-2xl bg-slate-700 relative overflow-hidden flex items-center justify-center group cursor-pointer border-4 border-white shadow-2xl">
                                {/* Map Placeholder Pattern */}
                                <div className="absolute inset-0 opacity-20 bg-[url('https://www.transparenttextures.com/patterns/diagmonds-light.png')]"></div>

                                <div className="relative z-10 flex flex-col items-center">
                                    <div className="w-16 h-16 bg-white rounded-full flex items-center justify-center text-brand-orange shadow-2xl mb-4 group-hover:scale-110 transition-transform">
                                        <MapPin size={32} fill="currentColor" />
                                    </div>
                                    <div className="bg-white/90 backdrop-blur-md px-6 py-2 rounded-full shadow-lg">
                                        <p className="text-sm font-bold text-slate-900 tracking-wide">SERVICE AREA: METRO & SUBURBS</p>
                                    </div>
                                </div>
                            </div>

                        </div>

                    </div>
                </div>
            </main>
            <Footer />
        </div>
    );
}
