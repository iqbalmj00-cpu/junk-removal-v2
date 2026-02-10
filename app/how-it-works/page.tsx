'use client';

import { Navbar } from '@/components/Navbar';
import { Footer } from '@/components/Footer';
import { Button } from '@/components/ui/Button';
import { ArrowRight, Truck, Calendar, CheckCircle, Box, Users, Recycle, Receipt, Camera, Star } from 'lucide-react';
import Link from 'next/link';

export default function HowItWorksPage() {
    return (
        <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
            <Navbar />

            <main className="flex-grow pt-28">

                {/* 1. HERO SECTION */}
                <section className="bg-slate-900 pt-20 pb-32 px-4 sm:px-6 lg:px-8 text-center relative overflow-hidden">
                    {/* Background Noise */}
                    <div className="absolute inset-0 opacity-10 bg-[url('https://www.transparenttextures.com/patterns/carbon-fibre.png')]"></div>

                    <div className="relative z-10 max-w-5xl mx-auto">
                        <span className="inline-block py-1 px-3 rounded-full bg-slate-800 border border-slate-700 text-brand-orange text-xs font-bold tracking-widest uppercase mb-6">
                            Simple & Fair
                        </span>
                        <h1 className="text-5xl md:text-7xl font-extrabold text-white mb-8 leading-tight tracking-tight uppercase">
                            Transparent, <br />
                            <span className="text-transparent bg-clip-text bg-gradient-to-r from-orange-400 to-orange-600">Volume-Based Pricing</span>
                        </h1>
                        <p className="text-xl text-slate-400 max-w-2xl mx-auto mb-12 font-light leading-relaxed">
                            No hourly rates. No hidden fees. You simply pay for the amount of space your items take up in our truck.
                        </p>

                        <div className="flex flex-col sm:flex-row gap-6 justify-center">
                            <Link href="#pricing">
                                <Button className="bg-brand-orange hover:bg-orange-600 text-white px-10 py-5 rounded-full text-lg font-bold shadow-xl shadow-orange-900/30 transition-transform hover:scale-105">
                                    VIEW PRICING
                                </Button>
                            </Link>
                            <Link href="/get-started">
                                <Button data-track="book_now" variant="outline" className="text-white border-2 border-slate-600 hover:bg-white hover:text-slate-900 hover:border-white px-10 py-5 rounded-full text-lg font-bold transition-all">
                                    GET STARTED <ArrowRight className="ml-2" size={20} />
                                </Button>
                            </Link>
                        </div>
                    </div>
                </section>

                {/* 2. THE FAIR PRICE FORMULA (Corrected: Vol + Labor + Disposal = Price) */}
                <section className="py-24 px-4 sm:px-6 lg:px-8 bg-white border-b border-slate-200">
                    <div className="max-w-7xl mx-auto">
                        <div className="text-center mb-16">
                            <h2 className="text-3xl font-extrabold text-slate-900">The Fair Price Formula</h2>
                            <p className="text-slate-500 mt-2">We separate the costs so you know exactly what you're paying for.</p>
                        </div>

                        {/* Equation Grid: Responsive (Stack on mobile, Row on Desktop) */}
                        <div className="flex flex-col lg:flex-row items-center justify-center gap-6 text-center">

                            {/* 1. Volume */}
                            <div className="flex-1 w-full lg:w-auto bg-slate-50 p-8 rounded-2xl border border-slate-200 h-full flex flex-col justify-center">
                                <Box size={40} className="text-slate-400 mx-auto mb-4" />
                                <h3 className="text-xl font-bold text-slate-900 mb-2">Volume</h3>
                                <p className="text-sm text-slate-500">Space in the truck</p>
                            </div>

                            <div className="text-slate-300 font-bold text-4xl shrink-0">+</div>

                            {/* 2. Labor */}
                            <div className="flex-1 w-full lg:w-auto bg-slate-50 p-8 rounded-2xl border border-slate-200 h-full flex flex-col justify-center">
                                <Users size={40} className="text-slate-400 mx-auto mb-4" />
                                <h3 className="text-xl font-bold text-slate-900 mb-2">Labor</h3>
                                <p className="text-sm text-slate-500">Loading & Lifting</p>
                            </div>

                            <div className="text-slate-300 font-bold text-4xl shrink-0">+</div>

                            {/* 3. Disposal */}
                            <div className="flex-1 w-full lg:w-auto bg-slate-50 p-8 rounded-2xl border border-slate-200 h-full flex flex-col justify-center">
                                <Recycle size={40} className="text-slate-400 mx-auto mb-4" />
                                <h3 className="text-xl font-bold text-slate-900 mb-2">Disposal</h3>
                                <p className="text-sm text-slate-500">Eco-friendly sorting</p>
                            </div>

                            <div className="text-slate-300 font-bold text-4xl shrink-0">=</div>

                            {/* 4. The Result */}
                            <div className="flex-1 w-full lg:w-auto bg-slate-900 p-8 rounded-2xl border border-slate-800 shadow-xl relative overflow-hidden h-full flex flex-col justify-center">
                                <div className="absolute top-0 right-0 w-20 h-20 bg-orange-500/20 blur-[40px] rounded-full"></div>
                                <Receipt size={40} className="text-brand-orange mx-auto mb-4 relative z-10" />
                                <h3 className="text-xl font-bold text-white mb-2 relative z-10">One Price</h3>
                                <p className="text-sm text-slate-400 relative z-10">Guaranteed upfront</p>
                            </div>

                        </div>
                    </div>
                </section>

                {/* 3. VISUAL TRUCK ESTIMATOR */}
                <section id="pricing" className="py-32 px-4 sm:px-6 lg:px-8 bg-slate-50">
                    <div className="max-w-7xl mx-auto">
                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">

                            {/* LEFT: TRUCK GRAPHIC */}
                            <div className="bg-white p-10 rounded-3xl shadow-xl border border-slate-200">
                                <div className="flex justify-between items-center mb-8">
                                    <h3 className="text-2xl font-bold text-slate-900 flex items-center gap-3">
                                        <Truck className="text-brand-orange" /> Standard Truck Bed
                                    </h3>
                                    <span className="bg-orange-100 text-brand-orange px-4 py-1 rounded-full text-xs font-bold uppercase">15 Cubic Yards</span>
                                </div>

                                {/* CSS GRID TRUCK */}
                                <div className="aspect-[4/3] bg-slate-100 rounded-xl border-4 border-slate-300 relative overflow-hidden">
                                    {/* Truck Cab Hint */}
                                    <div className="absolute right-0 top-0 bottom-0 w-1/12 bg-slate-200 border-l border-slate-300"></div>

                                    {/* The Grid */}
                                    <div className="absolute inset-0 right-[8.33%] grid grid-cols-4 grid-rows-2 gap-1 p-2">
                                        {[...Array(8)].map((_, i) => (
                                            <div key={i} className={`rounded-md ${i < 4 ? 'bg-orange-500/80 border border-orange-600' : 'bg-slate-200 border border-slate-300/50'}`}>
                                                {i === 0 && <span className="text-white/90 text-xs font-bold p-2 block">1/8 Load</span>}
                                                {i === 3 && <span className="text-white/90 text-xs font-bold p-2 block">1/2 Load</span>}
                                            </div>
                                        ))}
                                    </div>

                                    <div className="absolute bottom-4 left-4 bg-white/90 backdrop-blur px-4 py-2 rounded-lg text-xs font-bold text-slate-600 shadow-sm">
                                        Equivalent to ~6 Pickup Trucks
                                    </div>
                                </div>
                            </div>

                            {/* RIGHT: PRICE LIST */}
                            <div>
                                <h2 className="text-4xl font-extrabold text-slate-900 mb-8 leading-tight">Compare Load Sizes</h2>
                                <div className="space-y-4">
                                    {/* Row 1 */}
                                    <div className="flex items-center justify-between p-6 bg-white rounded-2xl border border-slate-100 shadow-sm transition-all hover:border-brand-orange/30">
                                        <div className="flex items-center gap-4">
                                            <div className="w-12 h-12 bg-slate-100 rounded-full flex items-center justify-center font-bold text-slate-500">XS</div>
                                            <div>
                                                <h4 className="font-bold text-slate-900">Minimum Load</h4>
                                                <p className="text-sm text-slate-500">Single item (Mattress, Sofa)</p>
                                            </div>
                                        </div>
                                        <div className="text-right">
                                            <span className="block text-2xl font-bold text-slate-900">$99 - $149</span>
                                        </div>
                                    </div>

                                    {/* Row 2 - Highlighted */}
                                    <div className="flex items-center justify-between p-6 bg-slate-900 rounded-2xl border border-slate-800 shadow-xl transform scale-105 relative z-10">
                                        <div className="absolute top-0 right-0 bg-brand-orange text-white text-[10px] font-bold px-3 py-1 rounded-bl-xl uppercase">Most Popular</div>
                                        <div className="flex items-center gap-4">
                                            <div className="w-12 h-12 bg-brand-orange text-white rounded-full flex items-center justify-center font-bold">1/2</div>
                                            <div>
                                                <h4 className="font-bold text-white">Half Truck Load</h4>
                                                <p className="text-sm text-slate-400">1 Bedroom Apt Cleanout</p>
                                            </div>
                                        </div>
                                        <div className="text-right">
                                            <span className="block text-2xl font-bold text-white">$350 - $450</span>
                                        </div>
                                    </div>

                                    {/* Row 3 */}
                                    <div className="flex items-center justify-between p-6 bg-white rounded-2xl border border-slate-100 shadow-sm transition-all hover:border-brand-orange/30">
                                        <div className="flex items-center gap-4">
                                            <div className="w-12 h-12 bg-slate-100 rounded-full flex items-center justify-center font-bold text-slate-500">Full</div>
                                            <div>
                                                <h4 className="font-bold text-slate-900">Full Truck Load</h4>
                                                <p className="text-sm text-slate-500">Garage / Estate Cleanout</p>
                                            </div>
                                        </div>
                                        <div className="text-right">
                                            <span className="block text-2xl font-bold text-slate-900">$650 - $799</span>
                                        </div>
                                    </div>
                                </div>
                                <div className="mt-8 flex items-center gap-2 text-slate-500 text-sm bg-blue-50 p-4 rounded-xl border border-blue-100">
                                    <Star size={16} className="text-brand-orange fill-brand-orange" />
                                    <span><strong>Pro Tip:</strong> We compact the load to save you money.</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </section>

                {/* 4. HOW TO BOOK STEPS */}
                <section className="py-24 px-4 sm:px-6 lg:px-8 bg-white overflow-hidden">
                    <div className="max-w-7xl mx-auto text-center">
                        <div className="inline-block mb-16">
                            <h2 className="text-3xl font-extrabold text-slate-900 mb-2">Easiest Booking in the Industry</h2>
                            <div className="h-1 w-24 bg-brand-orange mx-auto rounded-full"></div>
                        </div>

                        <div className="relative grid grid-cols-1 md:grid-cols-3 gap-12">
                            {/* Connecting Line (Desktop) */}
                            <div className="hidden md:block absolute top-12 left-[16%] right-[16%] h-0.5 bg-slate-200 -z-0"></div>

                            {/* Step 1 */}
                            <div className="relative z-10 flex flex-col items-center group">
                                <div className="w-24 h-24 bg-white border-4 border-slate-100 rounded-full flex items-center justify-center text-brand-orange shadow-lg mb-6 group-hover:scale-110 transition-transform">
                                    <Camera size={40} />
                                </div>
                                <h3 className="text-xl font-bold text-slate-900 mb-3">1. Snap A Photo</h3>
                                <p className="text-slate-500 max-w-xs leading-relaxed">Upload a picture of your junk pile using our AI tool.</p>
                            </div>

                            {/* Step 2 */}
                            <div className="relative z-10 flex flex-col items-center group">
                                <div className="w-24 h-24 bg-white border-4 border-slate-100 rounded-full flex items-center justify-center text-brand-orange shadow-lg mb-6 group-hover:scale-110 transition-transform">
                                    <Calendar size={40} />
                                </div>
                                <h3 className="text-xl font-bold text-slate-900 mb-3">2. Pick A Time</h3>
                                <p className="text-slate-500 max-w-xs leading-relaxed">Choose a 2-hour window that works for your schedule.</p>
                            </div>

                            {/* Step 3 */}
                            <div className="relative z-10 flex flex-col items-center group">
                                <div className="w-24 h-24 bg-white border-4 border-slate-100 rounded-full flex items-center justify-center text-brand-orange shadow-lg mb-6 group-hover:scale-110 transition-transform">
                                    <CheckCircle size={40} />
                                </div>
                                <h3 className="text-xl font-bold text-slate-900 mb-3">3. We Haul It</h3>
                                <p className="text-slate-500 max-w-xs leading-relaxed">Our team arrives, loads it up, and sweeps the area clean.</p>
                            </div>
                        </div>
                    </div>
                </section>

                {/* 5. FINAL CTA BANNER */}
                <section className="py-20 px-4 bg-slate-50">
                    <div className="max-w-5xl mx-auto bg-slate-900 rounded-[2.5rem] p-12 md:p-16 text-center relative overflow-hidden shadow-2xl">
                        {/* Glow */}
                        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full h-full bg-gradient-to-b from-slate-800 to-slate-900 z-0"></div>

                        <div className="relative z-10">
                            <h2 className="text-4xl md:text-5xl font-extrabold text-white mb-8 tracking-tight">
                                Ready to get rid of it?
                            </h2>

                            <div className="flex flex-col items-center gap-6">
                                <Link href="/get-started">
                                    <Button data-track="book_now" className="bg-brand-orange hover:bg-orange-600 text-white px-12 py-8 rounded-2xl text-2xl font-bold shadow-2xl shadow-orange-900/50 flex items-center gap-4 transition-transform hover:scale-105">
                                        <Camera size={32} /> UPLOAD FOR QUOTE
                                    </Button>
                                </Link>
                                <p className="text-slate-400 font-medium">
                                    Get a guaranteed price in seconds. No credit card required.
                                </p>
                            </div>
                        </div>
                    </div>
                </section>

            </main>
            <Footer />
        </div>
    );
}
