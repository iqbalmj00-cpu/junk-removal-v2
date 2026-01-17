import { Navbar } from '@/components/Navbar';
import { Footer } from '@/components/Footer';
import { Button } from '@/components/ui/Button';
import Link from 'next/link';
import { Box, User, Recycle, CheckCircle, Camera, ArrowRight, X, Info, Truck, Scale } from 'lucide-react';

export default function HowItWorksPage() {
    return (
        <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
            <Navbar />

            <main className="flex-grow pt-28">

                {/* 1. HERO SECTION (Dark Mode) - pt-32 for clearance */}
                <section className="bg-slate-900 py-32 px-4 sm:px-6 lg:px-8 text-center relative overflow-hidden">
                    {/* Decorative background element */}
                    <div className="absolute top-0 left-0 w-full h-full bg-[url('https://www.transparenttextures.com/patterns/dark-matter.png')] opacity-20 pointer-events-none"></div>

                    <div className="max-w-5xl mx-auto relative z-10">
                        <span className="inline-flex items-center px-4 py-1.5 rounded-full bg-slate-800 border border-slate-700 text-brand-orange text-sm font-bold tracking-wide uppercase mb-8 shadow-lg">
                            Upfront Pricing Model
                        </span>

                        <h1 className="text-5xl md:text-7xl font-extrabold text-white mb-8 leading-tight tracking-tight">
                            TRANSPARENT, <br />
                            <span className="text-brand-orange">VOLUME-BASED PRICING</span>
                        </h1>

                        <p className="text-2xl text-slate-300 max-w-3xl mx-auto mb-12 leading-relaxed font-light">
                            No hourly rates. No hidden surcharges. You simply pay for the amount of space your items occupy in our industrial-grade trucks.
                        </p>

                        <div className="flex justify-center">
                            <a href="#formula">
                                <Button size="lg" className="bg-brand-orange hover:bg-orange-600 text-white px-10 py-5 rounded-full text-xl font-bold shadow-2xl shadow-orange-900/20">
                                    View Pricing Formula
                                </Button>
                            </a>
                        </div>
                    </div>
                </section>

                {/* 2. TRUCK LOAD VISUALIZER (Moved Up) - py-32 for scale */}
                <section className="py-32 px-4 sm:px-6 lg:px-8 bg-slate-50 border-b border-slate-200">
                    <div className="max-w-7xl mx-auto">
                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-20 items-center">

                            {/* Left: Truck Visual */}
                            <div>
                                <h3 className="text-sm font-bold text-slate-400 uppercase tracking-widest mb-8">Load Estimator</h3>
                                <div className="bg-white p-12 rounded-[2.5rem] shadow-sm border border-slate-200">

                                    {/* The Truck Representation */}
                                    <div className="relative my-12">
                                        {/* Truck Cab Outline (Decorative) */}
                                        <div className="w-32 h-20 border-2 border-slate-300 rounded-t-2xl absolute -right-4 top-12 hidden md:block opacity-30"></div>

                                        {/* Truck Bed Container */}
                                        <div className="w-full h-96 border-4 border-slate-800 bg-slate-100 rounded-xl relative overflow-hidden flex flex-col-reverse shadow-inner">

                                            {/* Sections - Larger Hit Area */}
                                            <div className="h-1/4 w-full border-t-2 border-dashed border-slate-300 flex items-center justify-center text-slate-400 text-sm font-bold uppercase tracking-wider relative group hover:bg-orange-50 transition-colors cursor-pointer">
                                                <span className="bg-slate-100 px-3 py-1 rounded-full z-10 shadow-sm border border-slate-200">Full Truck</span>
                                                <div className="absolute inset-x-0 bottom-0 h-full bg-brand-orange opacity-0 group-hover:opacity-20 transition-opacity"></div>
                                            </div>

                                            <div className="h-1/4 w-full border-t-2 border-dashed border-slate-300 flex items-center justify-center text-slate-400 text-sm font-bold uppercase tracking-wider relative group hover:bg-orange-50 transition-colors cursor-pointer">
                                                <span className="bg-slate-100 px-3 py-1 rounded-full z-10 shadow-sm border border-slate-200">3/4 Load</span>
                                                <div className="absolute inset-x-0 bottom-0 h-full bg-brand-orange opacity-0 group-hover:opacity-30 transition-opacity"></div>
                                            </div>

                                            <div className="h-1/4 w-full border-t-2 border-dashed border-slate-300 flex items-center justify-center text-slate-400 text-sm font-bold uppercase tracking-wider relative group hover:bg-orange-50 transition-colors cursor-pointer">
                                                <span className="bg-slate-100 px-3 py-1 rounded-full z-10 shadow-sm border border-slate-200">1/2 Load</span>
                                                <div className="absolute inset-x-0 bottom-0 h-full bg-brand-orange opacity-0 group-hover:opacity-40 transition-opacity"></div>
                                            </div>

                                            <div className="h-1/4 w-full flex items-center justify-center text-slate-400 text-sm font-bold uppercase tracking-wider relative group hover:bg-orange-50 transition-colors cursor-pointer">
                                                <span className="bg-slate-100 px-3 py-1 rounded-full z-10 shadow-sm border border-slate-200">Min Load</span>
                                                <div className="absolute inset-x-0 bottom-0 h-full bg-brand-orange opacity-0 group-hover:opacity-50 transition-opacity"></div>
                                            </div>

                                        </div>

                                        {/* Wheels (Decorative) */}
                                        <div className="flex justify-between px-16 mt-[-20px] relative z-10">
                                            <div className="w-20 h-20 bg-slate-800 rounded-full border-4 border-slate-600 shadow-2xl"></div>
                                            <div className="w-20 h-20 bg-slate-800 rounded-full border-4 border-slate-600 shadow-2xl"></div>
                                        </div>
                                    </div>

                                </div>
                            </div>

                            {/* Right: Pricing Tiers */}
                            <div>
                                <h2 className="text-4xl font-extrabold text-slate-900 mb-10">Estimated Rate Guide</h2>
                                <div className="space-y-6">

                                    <div className="flex items-center justify-between p-8 bg-white rounded-2xl border border-slate-200 shadow-sm hover:border-brand-orange transition-colors group">
                                        <div className="flex items-center gap-6">
                                            <div className="w-16 h-16 bg-slate-100 rounded-2xl flex items-center justify-center text-slate-500 group-hover:bg-brand-orange group-hover:text-white transition-colors">
                                                <Box size={28} />
                                            </div>
                                            <div>
                                                <h4 className="font-bold text-slate-900 text-xl">Minimum Load</h4>
                                                <p className="text-slate-500 text-lg">Single item (e.g., Mattress)</p>
                                            </div>
                                        </div>
                                        <div className="text-right">
                                            <span className="block text-3xl font-bold text-slate-900">$99 - $149</span>
                                        </div>
                                    </div>

                                    <div className="flex items-center justify-between p-8 bg-white rounded-2xl border border-slate-200 shadow-sm hover:border-brand-orange transition-colors group">
                                        <div className="flex items-center gap-6">
                                            <div className="w-16 h-16 bg-slate-100 rounded-2xl flex items-center justify-center text-slate-500 group-hover:bg-brand-orange group-hover:text-white transition-colors">
                                                <Scale size={28} />
                                            </div>
                                            <div>
                                                <h4 className="font-bold text-slate-900 text-xl">1/2 Truck</h4>
                                                <p className="text-slate-500 text-lg">Garage cleanout / 1 Room</p>
                                            </div>
                                        </div>
                                        <div className="text-right">
                                            <span className="block text-3xl font-bold text-slate-900">$350 - $450</span>
                                        </div>
                                    </div>

                                    <div className="flex items-center justify-between p-8 bg-white rounded-2xl border border-slate-200 shadow-sm hover:border-brand-orange transition-colors group">
                                        <div className="flex items-center gap-6">
                                            <div className="w-16 h-16 bg-slate-100 rounded-2xl flex items-center justify-center text-slate-500 group-hover:bg-brand-orange group-hover:text-white transition-colors">
                                                <Truck size={28} />
                                            </div>
                                            <div>
                                                <h4 className="font-bold text-slate-900 text-xl">Full Truck</h4>
                                                <p className="text-slate-500 text-lg">Whole house / Large Reno</p>
                                            </div>
                                        </div>
                                        <div className="text-right">
                                            <span className="block text-3xl font-bold text-slate-900">$650 - $799</span>
                                        </div>
                                    </div>

                                </div>
                                <div className="mt-10 flex items-center gap-3 text-slate-500 text-base font-medium bg-slate-100 inline-block px-4 py-2 rounded-lg">
                                    <Info size={20} /> Prices are estimates and vary by region.
                                </div>
                            </div>
                        </div>
                    </div>
                </section>

                {/* 3. THE FORMULA (Moved Down + Added ID) */}
                <section id="formula" className="py-24 px-4 sm:px-6 lg:px-8 bg-white">
                    <div className="max-w-7xl mx-auto">
                        <div className="text-center mb-20">
                            <h2 className="text-4xl md:text-5xl font-extrabold text-slate-900 uppercase tracking-tight">The Pricing Formula</h2>
                        </div>

                        <div className="flex flex-col md:flex-row items-center justify-center gap-10 md:gap-6">
                            {/* Card 1: Volume */}
                            <div className="flex flex-col items-center text-center max-w-[280px]">
                                <div className="w-24 h-24 bg-orange-50 rounded-[2rem] flex items-center justify-center text-brand-orange mb-6 shadow-sm">
                                    <Box size={48} />
                                </div>
                                <h3 className="font-bold text-slate-900 text-2xl mb-2">Volume</h3>
                                <p className="text-slate-500 text-lg">Cubic footage in our 12ft bed.</p>
                            </div>

                            <span className="text-5xl font-light text-slate-200 hidden md:block">+</span>

                            {/* Card 2: Labor */}
                            <div className="flex flex-col items-center text-center max-w-[280px]">
                                <div className="w-24 h-24 bg-orange-50 rounded-[2rem] flex items-center justify-center text-brand-orange mb-6 shadow-sm">
                                    <User size={48} />
                                </div>
                                <h3 className="font-bold text-slate-900 text-2xl mb-2">Labor</h3>
                                <p className="text-slate-500 text-lg">Two insured professionals.</p>
                            </div>

                            <span className="text-5xl font-light text-slate-200 hidden md:block">+</span>

                            {/* Card 3: Disposal */}
                            <div className="flex flex-col items-center text-center max-w-[280px]">
                                <div className="w-24 h-24 bg-orange-50 rounded-[2rem] flex items-center justify-center text-brand-orange mb-6 shadow-sm">
                                    <Recycle size={48} />
                                </div>
                                <h3 className="font-bold text-slate-900 text-2xl mb-2">Disposal</h3>
                                <p className="text-slate-500 text-lg">Eco-friendly sorting.</p>
                            </div>

                            <span className="text-5xl font-light text-slate-200 hidden md:block">=</span>

                            {/* Card 4: Fair Price results */}
                            <div className="flex flex-col items-center text-center max-w-[280px]">
                                <div className="w-24 h-24 bg-slate-900 rounded-[2rem] flex items-center justify-center text-brand-orange mb-6 shadow-xl">
                                    <CheckCircle size={48} />
                                </div>
                                <h3 className="font-bold text-slate-900 text-2xl mb-2">Fair Price</h3>
                                <p className="text-slate-500 text-lg">Guaranteed upfront.</p>
                            </div>
                        </div>
                    </div>
                </section>

                {/* 4. PHOTO ESTIMATE CTA */}
                <section className="py-24 px-4 bg-slate-50">
                    <div className="max-w-6xl mx-auto">
                        <div className="bg-slate-900 rounded-[3rem] p-12 md:p-20 flex flex-col md:flex-row items-center justify-between shadow-2xl overflow-hidden relative">
                            {/* Abstract Accent */}
                            <div className="absolute top-0 right-0 w-96 h-96 bg-brand-orange rounded-full blur-[150px] opacity-20 pointer-events-none"></div>

                            <div className="relative z-10 flex flex-col md:flex-row items-center gap-10 text-center md:text-left">
                                <div className="w-24 h-24 bg-slate-800 rounded-full flex items-center justify-center text-brand-orange shrink-0 border border-slate-700 shadow-xl">
                                    <Camera size={48} />
                                </div>
                                <div>
                                    <h2 className="text-3xl md:text-4xl font-bold text-white mb-4 leading-tight">Upload Your Photos for <br /> a Guaranteed Price</h2>
                                    <p className="text-slate-400 text-xl">Skip the on-site estimate. Our AI analyzes your junk instantly.</p>
                                </div>
                            </div>

                            <Link href="/book" className="mt-10 md:mt-0 relative z-10">
                                <Button className="bg-brand-orange hover:bg-orange-500 text-white px-10 py-5 h-auto text-xl font-bold rounded-full shadow-2xl shadow-orange-900/30">
                                    START PHOTO ESTIMATE <ArrowRight className="ml-3" />
                                </Button>
                            </Link>

                        </div>
                    </div>
                </section>

                {/* 5. COMPARISON TABLE */}
                <section className="py-32 px-4 sm:px-6 lg:px-8 bg-white font-sans">
                    <div className="max-w-5xl mx-auto">
                        <div className="text-center mb-20">
                            <h2 className="text-4xl font-extrabold text-slate-900 mb-6">WHY WE ARE BETTER</h2>
                            <p className="text-xl text-slate-500">We set the standard for transparency in the industry.</p>
                        </div>

                        <div className="bg-slate-50 rounded-3xl shadow-sm border border-slate-200 overflow-hidden">
                            <table className="w-full">
                                <thead>
                                    <tr className="bg-slate-100 border-b border-slate-200">
                                        <th className="py-8 px-8 text-left text-slate-500 font-bold text-lg">Feature</th>
                                        <th className="py-8 px-8 text-center text-slate-500 font-bold text-lg">Typical Hauler</th>
                                        <th className="py-8 px-8 text-center text-brand-orange font-bold text-lg bg-orange-50/50">Clean Sweep</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-slate-100">
                                    <tr>
                                        <td className="py-8 px-8 text-slate-900 font-bold text-xl">Pricing Model</td>
                                        <td className="py-8 px-8 text-center text-slate-500 text-lg">Hourly + Fees</td>
                                        <td className="py-8 px-8 text-center text-slate-900 font-bold text-lg bg-orange-50/30">Volume Based</td>
                                    </tr>
                                    <tr>
                                        <td className="py-8 px-8 text-slate-900 font-bold text-xl">Hidden Fees</td>
                                        <td className="py-8 px-8 text-center">
                                            <div className="flex flex-col items-center">
                                                <X className="text-red-400 mb-2" size={28} />
                                                <span className="text-sm text-red-500 font-medium max-w-[140px] leading-tight">Surprise dumping fees added to the final bill.</span>
                                            </div>
                                        </td>
                                        <td className="py-8 px-8 text-center bg-orange-50/30">
                                            <div className="flex flex-col items-center">
                                                <CheckCircle className="text-green-500 mb-2" size={28} />
                                                <span className="text-sm text-slate-600 font-medium max-w-[180px] leading-tight">All-inclusive flat rate. Labor, transport, and disposal included.</span>
                                            </div>
                                        </td>
                                    </tr>
                                    <tr>
                                        <td className="py-8 px-8 text-slate-900 font-bold text-xl">On-Time Guarantee</td>
                                        <td className="py-8 px-8 text-center text-slate-500"><X className="text-red-400 mx-auto" size={28} /></td>
                                        <td className="py-8 px-8 text-center text-slate-900 bg-orange-50/30"><CheckCircle className="text-green-500 mx-auto" size={28} /></td>
                                    </tr>
                                    <tr>
                                        <td className="py-8 px-8 text-slate-900 font-bold text-xl">Eco-Friendly</td>
                                        <td className="py-8 px-8 text-center text-slate-500"><X className="text-red-400 mx-auto" size={28} /></td>
                                        <td className="py-8 px-8 text-center text-slate-900 bg-orange-50/30"><CheckCircle className="text-green-500 mx-auto" size={28} /></td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                </section>

            </main>
            <Footer />
        </div>
    );
}
