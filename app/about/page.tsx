import { Navbar } from '@/components/Navbar';
import { Footer } from '@/components/Footer';
import { Button } from '@/components/ui/Button';
import Link from 'next/link';
import { Briefcase, Recycle, Tag, Cog, ArrowRight, Settings } from 'lucide-react';

export default function AboutPage() {
    return (
        <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
            <Navbar />

            <main className="flex-grow pt-28">

                {/* 1. HERO SECTION (Background Image) */}
                <section className="relative min-h-[700px] flex items-center bg-slate-900 overflow-hidden pt-32 pb-24">
                    {/* Background Overlay */}
                    <div className="absolute inset-0 z-0">
                        <div className="absolute inset-0 bg-slate-900/80 z-10"></div>
                        <div
                            className="absolute inset-0 bg-cover bg-center bg-no-repeat grayscale opacity-40 transform scale-105"
                            style={{ backgroundImage: "url('https://placehold.co/1920x1080/1e293b/FFFFFF/png?text=Truck+Background')" }}
                        ></div>
                    </div>

                    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-20 w-full text-center lg:text-left">
                        <span className="inline-block bg-brand-orange text-white text-sm font-bold px-4 py-1.5 rounded-full mb-8 tracking-widest">
                            EST. 2024
                        </span>

                        <h1 className="text-6xl md:text-8xl font-extrabold text-white leading-[1.1] mb-10 tracking-tight">
                            OUR MISSION: <br />
                            <span className="text-brand-orange">CLEANING UP</span> <br />
                            THE COMMUNITY
                        </h1>

                        <div className="max-w-3xl mx-auto lg:mx-0 border-l-4 border-brand-orange pl-8 lg:pl-10">
                            <p className="text-2xl text-slate-300 font-light leading-relaxed">
                                We are dedicated to keeping our neighborhoods clean, safe, and clutter-free through professional, environmentally responsible junk removal services.
                            </p>
                        </div>
                    </div>
                </section>

                {/* 2. THE STORY ("Built on Hard Work") */}
                <section className="py-32 px-4 sm:px-6 lg:px-8 bg-slate-50">
                    <div className="max-w-7xl mx-auto">
                        <div className="bg-white rounded-3xl shadow-xl overflow-hidden border border-slate-100 relative">
                            {/* Decorative Gear Icon */}
                            <div className="absolute top-8 right-8 text-slate-100 opacity-50 hidden md:block pointer-events-none">
                                <Cog size={160} />
                            </div>

                            <div className="grid grid-cols-1 lg:grid-cols-2">
                                <div className="p-16 lg:p-24 flex flex-col justify-center relative z-10">
                                    <h2 className="text-4xl lg:text-5xl font-extrabold text-slate-900 mb-8 tracking-tight">
                                        BUILT ON HARD WORK
                                    </h2>
                                    <p className="text-slate-500 text-xl leading-relaxed mb-8">
                                        Our story began with a simple pickup truck and a commitment to engineering precision in an industry often known for chaos.
                                    </p>
                                    <p className="text-slate-500 text-xl leading-relaxed">
                                        We realized that junk removal needed a professional upgrade—clean uniforms, honest pricing, and a rigorous recycling protocol. Today, we treat every pickup like a critical mission.
                                    </p>
                                </div>
                                <div className="h-full min-h-[500px] bg-slate-100 relative">
                                    <img
                                        src="https://placehold.co/800x800/e2e8f0/475569/png?text=Worker+With+Blueprints"
                                        alt="Worker with Blueprints"
                                        className="w-full h-full object-cover"
                                    />
                                    {/* Overlay */}
                                    <div className="absolute inset-0 bg-gradient-to-r from-white/10 to-transparent"></div>
                                </div>
                            </div>
                        </div>
                    </div>
                </section>

                {/* 3. THE INDUSTRIAL STANDARD (Dark Section) */}
                <section className="py-32 px-4 sm:px-6 lg:px-8 bg-slate-900">
                    <div className="max-w-7xl mx-auto">
                        <div className="text-center mb-24">
                            <h3 className="text-brand-orange font-bold text-sm uppercase tracking-widest mb-4">Core Standards</h3>
                            <h2 className="text-4xl md:text-5xl font-extrabold text-white tracking-tight">THE INDUSTRIAL STANDARD</h2>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-3 gap-10">
                            {/* Card 1 */}
                            <div className="bg-slate-800 p-12 rounded-2xl border border-slate-700 hover:border-brand-orange transition-colors group flex flex-col items-center text-center">
                                <div className="w-20 h-20 bg-slate-700 rounded-2xl flex items-center justify-center text-white mb-8 group-hover:bg-brand-orange transition-colors">
                                    <Briefcase size={40} />
                                </div>
                                <h3 className="text-2xl font-bold text-white mb-4">Professionalism</h3>
                                <p className="text-slate-400 text-lg leading-relaxed">Uniformed crews, timely arrivals, and white-glove service for every job site.</p>
                            </div>

                            {/* Card 2 */}
                            <div className="bg-slate-800 p-12 rounded-2xl border border-slate-700 hover:border-brand-orange transition-colors group flex flex-col items-center text-center">
                                <div className="w-20 h-20 bg-slate-700 rounded-2xl flex items-center justify-center text-white mb-8 group-hover:bg-brand-orange transition-colors">
                                    <Recycle size={40} />
                                </div>
                                <h3 className="text-2xl font-bold text-white mb-4">Eco-Friendly Disposal</h3>
                                <p className="text-slate-400 text-lg leading-relaxed">We sort, recycle, and donate items to minimize landfill impact. Up to 60% diverted.</p>
                            </div>

                            {/* Card 3 */}
                            <div className="bg-slate-800 p-12 rounded-2xl border border-slate-700 hover:border-brand-orange transition-colors group flex flex-col items-center text-center">
                                <div className="w-20 h-20 bg-slate-700 rounded-2xl flex items-center justify-center text-white mb-8 group-hover:bg-brand-orange transition-colors">
                                    <Tag size={40} />
                                </div>
                                <h3 className="text-2xl font-bold text-white mb-4">Transparent Pricing</h3>
                                <p className="text-slate-400 text-lg leading-relaxed">Upfront quotes based on volume. No hidden fees or surprise surcharges.</p>
                            </div>
                        </div>
                    </div>
                </section>

                {/* 4. MEET THE CREW */}
                <section className="py-32 px-4 sm:px-6 lg:px-8 bg-white border-t border-slate-200">
                    <div className="max-w-7xl mx-auto">
                        <div className="flex flex-col md:flex-row justify-between items-end md:items-center mb-16 gap-6">
                            <h2 className="text-4xl font-extrabold text-slate-900">MEET THE CREW</h2>
                            <Link href="#" className="text-brand-orange font-bold text-lg flex items-center hover:text-orange-600 transition-colors">
                                VIEW ALL STAFF <ArrowRight size={20} className="ml-2" />
                            </Link>
                        </div>

                        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-10">
                            {/* Profile 1 */}
                            <div className="group">
                                <div className="aspect-square bg-slate-100 rounded-2xl overflow-hidden mb-6 relative">
                                    <img
                                        src="https://placehold.co/400x400/cbd5e1/64748b/png?text=Mike"
                                        alt="Mike Ross"
                                        className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                                    />
                                </div>
                                <h3 className="font-bold text-slate-900 text-xl mb-1">Mike Ross</h3>
                                <p className="text-slate-500 font-medium">Operations Lead</p>
                            </div>

                            {/* Profile 2 */}
                            <div className="group">
                                <div className="aspect-square bg-slate-100 rounded-2xl overflow-hidden mb-6 relative">
                                    <img
                                        src="https://placehold.co/400x400/cbd5e1/64748b/png?text=Sarah"
                                        alt="Sarah Jenkins"
                                        className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                                    />
                                </div>
                                <h3 className="font-bold text-slate-900 text-xl mb-1">Sarah Jenkins</h3>
                                <p className="text-slate-500 font-medium">Logistics Manager</p>
                            </div>

                            {/* Profile 3 */}
                            <div className="group">
                                <div className="aspect-square bg-slate-100 rounded-2xl overflow-hidden mb-6 relative">
                                    <img
                                        src="https://placehold.co/400x400/cbd5e1/64748b/png?text=David"
                                        alt="David Chen"
                                        className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                                    />
                                </div>
                                <h3 className="font-bold text-slate-900 text-xl mb-1">David Chen</h3>
                                <p className="text-slate-500 font-medium">Senior Hauler</p>
                            </div>

                            {/* Profile 4 */}
                            <div className="group">
                                <div className="aspect-square bg-slate-100 rounded-2xl overflow-hidden mb-6 relative">
                                    <img
                                        src="https://placehold.co/400x400/cbd5e1/64748b/png?text=Marcus"
                                        alt="Marcus Johnson"
                                        className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                                    />
                                </div>
                                <h3 className="font-bold text-slate-900 text-xl mb-1">Marcus Johnson</h3>
                                <p className="text-slate-500 font-medium">Fleet Supervisor</p>
                            </div>
                        </div>
                    </div>
                </section>

                {/* 5. BOTTOM CTA */}
                <section className="py-32 px-4 bg-slate-50 border-t border-slate-200">
                    <div className="max-w-4xl mx-auto text-center">
                        <h2 className="text-4xl md:text-5xl font-extrabold text-slate-900 mb-8 tracking-tight">
                            READY TO CLEAR THE CLUTTER?
                        </h2>
                        <p className="text-2xl text-slate-500 mb-12 max-w-3xl mx-auto font-light">
                            Schedule your pickup today or join our team of professionals.
                        </p>
                        <div className="flex flex-col sm:flex-row gap-6 justify-center">
                            <Link href="/book">
                                <Button className="w-full sm:w-auto bg-brand-orange hover:bg-orange-600 text-white px-10 py-5 h-auto rounded-full text-xl font-bold shadow-2xl shadow-orange-900/20">
                                    BOOK A SERVICE
                                </Button>
                            </Link>

                        </div>
                    </div>
                </section>

            </main>
            <Footer />
        </div>
    );
}
