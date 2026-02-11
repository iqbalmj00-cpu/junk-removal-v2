import { Metadata } from 'next';
import Link from 'next/link';
import { Phone, Info, ShieldX } from 'lucide-react';
import { Navbar } from '@/components/Navbar';
import { Footer } from '@/components/Footer';

export const metadata: Metadata = {
    title: "Items We Don't Take | Clean Sweep Junk Removal",
    description: 'List of prohibited items for junk removal services including hazardous materials, chemicals, and other restricted waste.',
};

const prohibitedItems = [
    {
        icon: 'format_paint',
        title: 'Paint & Solvents',
        description: 'Wet paint cans, thinners, strippers, and wood stains.',
    },
    {
        icon: 'local_gas_station',
        title: 'Gasoline & Propane',
        description: 'Fuel cans, propane tanks, and oil drums containing liquid.',
    },
    {
        icon: 'warning',
        title: 'Asbestos',
        description: 'Siding, tiles, or insulation materials containing asbestos fibers.',
    },
    {
        icon: 'medical_services',
        title: 'Medical Waste',
        description: 'Biohazards, needles, syringes, and pharmaceutical waste.',
    },
    {
        icon: 'whatshot',
        title: 'Explosives',
        description: 'Fireworks, ammunition, flares, and other combustible devices.',
    },
    {
        icon: 'science',
        title: 'Hazardous Liquids',
        description: 'Pesticides, herbicides, motor oil, and unknown chemical substances.',
    },
];

export default function ItemsWeDontTakePage() {
    return (
        <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
            <Navbar />
            <main className="flex-grow flex flex-col">
                {/* Hero Section */}
                <section className="relative bg-white border-b border-slate-200 pt-36 pb-20">
                    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
                        <div className="flex flex-col md:flex-row items-start gap-8">
                            <div className="hidden md:block w-2 h-32 bg-brand-orange rounded-full mt-2" />
                            <div>
                                <h1 className="text-4xl md:text-5xl lg:text-6xl font-extrabold text-slate-900 tracking-tight mb-6">
                                    Items We <span className="text-brand-orange">Don&apos;t Take</span>
                                </h1>
                                <p className="text-lg md:text-xl text-slate-500 max-w-3xl leading-relaxed">
                                    For the safety of our crew, our equipment, and in compliance with local environmental laws, we are unable to remove certain hazardous materials. Please review the list below before booking.
                                </p>
                            </div>
                        </div>
                    </div>
                    {/* Decorative icon */}
                    <div className="absolute top-0 right-0 w-1/3 h-full opacity-5 pointer-events-none overflow-hidden">
                        <ShieldX className="w-96 h-96 text-slate-900 absolute -top-20 -right-20" />
                    </div>
                </section>

                {/* Main Content */}
                <section className="flex-grow -mt-10 mb-20 relative z-20 px-4 sm:px-6 lg:px-8">
                    <div className="max-w-6xl mx-auto">
                        <div className="bg-white rounded-xl shadow-xl border border-slate-100 overflow-hidden">
                            {/* Card Header */}
                            <div className="bg-slate-50 border-b border-slate-100 px-8 py-6">
                                <h2 className="text-2xl font-bold text-slate-900 flex items-center gap-3">
                                    <span className="bg-red-100 text-red-600 p-2 rounded-full flex items-center justify-center">
                                        <span className="material-icons">gpp_bad</span>
                                    </span>
                                    We typically cannot accept:
                                </h2>
                            </div>

                            {/* Prohibited Items Grid */}
                            <div className="p-8">
                                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                                    {prohibitedItems.map((item) => (
                                        <div key={item.title} className="group relative bg-slate-50 rounded-lg p-6 border border-slate-100 hover:border-red-200 transition-colors">
                                            <div className="absolute top-4 right-4 text-red-500 opacity-20 group-hover:opacity-100 transition-opacity">
                                                <span className="material-icons text-3xl">close</span>
                                            </div>
                                            <div className="w-12 h-12 bg-slate-900 rounded-lg flex items-center justify-center mb-4 text-brand-orange">
                                                <span className="material-icons text-2xl">{item.icon}</span>
                                            </div>
                                            <h3 className="text-lg font-bold text-slate-900 mb-2">{item.title}</h3>
                                            <p className="text-sm text-slate-500">{item.description}</p>
                                        </div>
                                    ))}
                                </div>

                                {/* Info Box */}
                                <div className="mt-10 bg-blue-50 border-l-4 border-blue-500 rounded-r-lg p-6 flex flex-col sm:flex-row gap-4 items-start">
                                    <Info className="w-8 h-8 text-blue-600 flex-shrink-0 mt-0.5" />
                                    <div>
                                        <h4 className="text-lg font-bold text-slate-900 mb-1">What should I do with these items?</h4>
                                        <p className="text-slate-600 text-sm">
                                            We recommend contacting your city&apos;s <span className="font-semibold">household hazardous waste collection program</span>. Most municipalities offer free drop-off days for residents to safely dispose of these materials.
                                        </p>
                                    </div>
                                </div>
                            </div>

                            {/* Footer CTA */}
                            <div className="bg-slate-50 border-t border-slate-100 px-8 py-8 text-center">
                                <h3 className="text-xl font-bold text-slate-900 mb-4">Not sure about an item?</h3>
                                <p className="text-slate-500 mb-6 max-w-2xl mx-auto">
                                    If you have something that isn&apos;t on this list but looks questionable, give us a call. We&apos;re happy to clarify!
                                </p>
                                <Link
                                    href="/contact"
                                    className="inline-flex items-center gap-2 bg-brand-orange hover:bg-orange-500 text-white px-8 py-4 rounded-lg font-bold uppercase tracking-wider shadow-lg transition-transform transform hover:-translate-y-1"
                                >
                                    <Phone className="w-4 h-4" />
                                    Have Questions? Contact Us
                                </Link>
                            </div>
                        </div>
                    </div>
                </section>
            </main>
            <Footer />
        </div>
    );
}
