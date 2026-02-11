import { Metadata } from 'next';
import Link from 'next/link';
import { Phone, MessageSquare, Recycle } from 'lucide-react';
import { Navbar } from '@/components/Navbar';
import { Footer } from '@/components/Footer';

export const metadata: Metadata = {
    title: 'Items We Take | Clean Sweep Junk Removal',
    description: 'We remove almost anything non-hazardous — from single items to full cleanouts. Furniture, appliances, e-waste, yard debris, construction materials, and more.',
};

const categories = [
    {
        icon: 'chair',
        title: 'Furniture',
        items: ['Sofas & Loveseats', 'Dining Tables & Chairs', 'Dressers & Wardrobes', 'Bookshelves', 'Office Desks'],
    },
    {
        icon: 'kitchen',
        title: 'Appliances',
        items: ['Refrigerators & Freezers', 'Washers & Dryers', 'Stoves & Ovens', 'Dishwashers', 'Microwaves'],
    },
    {
        icon: 'park',
        title: 'Yard Debris',
        items: ['Branches & Clippings', 'Landscaping Trimmings', 'Fencing Material', 'Soil & Sod (Bagged)', 'Storm Debris'],
    },
    {
        icon: 'bed',
        title: 'Mattresses',
        items: ['Mattresses (All Sizes)', 'Box Springs', 'Bed Frames', 'Futons', 'Headboards'],
    },
    {
        icon: 'computer',
        title: 'E-Waste',
        items: ['Computers & Laptops', 'Monitors & TVs', 'Printers & Scanners', 'Stereos & Speakers', 'Cables & Peripherals'],
    },
    {
        icon: 'construction',
        title: 'Construction Debris',
        items: ['Drywall & Plaster', 'Wood Scraps & Lumber', 'Tiling & Ceramics', 'Windows & Glass', 'Roofing Materials'],
    },
    {
        icon: 'inventory_2',
        title: 'Cardboard & Paper',
        items: ['Moving Boxes', 'Shipping Cartons', 'Old Files & Documents', 'Newspapers & Magazines', 'Packaging Material'],
    },
    {
        icon: 'garage',
        title: 'Garage & Attic',
        items: ['Old Tools', 'Sports Equipment', 'Bicycles', 'Holiday Decorations', 'General Household Junk'],
    },
    {
        icon: 'cleaning_services',
        title: 'Full Cleanouts',
        items: ['Estate Cleanouts', 'Foreclosure Cleanouts', 'Storage Unit Cleanouts', 'Office Cleanouts', 'Basement Cleanouts'],
    },
];

export default function ItemsWeTakePage() {
    return (
        <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
            <Navbar />
            <main className="flex-grow">
                {/* Hero */}
                <section className="relative bg-slate-50 border-b border-slate-200 pt-36 pb-20">
                    <div className="absolute inset-0 z-0 opacity-5 pointer-events-none" style={{ backgroundImage: 'radial-gradient(#1e293b 1px, transparent 1px)', backgroundSize: '20px 20px' }} />
                    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center relative z-10">
                        <h1 className="text-4xl font-extrabold text-slate-900 sm:text-5xl lg:text-6xl uppercase mb-6">
                            Items We Take
                        </h1>
                        <p className="max-w-2xl mx-auto text-xl text-slate-500">
                            We remove almost anything non-hazardous — from single items to full cleanouts. Fast, professional, and eco-friendly.
                        </p>
                    </div>
                </section>

                {/* Disposal Promise */}
                <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 -mt-8 relative z-10">
                    <div className="bg-white rounded-xl shadow-xl border-l-8 border-brand-orange p-8 max-w-4xl mx-auto">
                        <div className="flex flex-col md:flex-row items-center md:items-start gap-6">
                            <div className="flex-shrink-0 bg-brand-orange/10 rounded-full p-4">
                                <Recycle className="w-8 h-8 text-brand-orange" />
                            </div>
                            <div className="text-center md:text-left">
                                <h3 className="text-lg font-bold text-slate-900 uppercase tracking-wide mb-2">Our Disposal Promise</h3>
                                <p className="text-slate-500 leading-relaxed">
                                    We don&apos;t just dump your junk. Our team is committed to diverting waste from landfills. We actively donate usable goods to local charities and recycle eligible materials whenever possible.
                                </p>
                            </div>
                        </div>
                    </div>
                </section>

                {/* Category Grid */}
                <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-20">
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8 mb-16">
                        {categories.map((cat) => (
                            <div key={cat.title} className="group bg-white rounded-xl shadow-sm hover:shadow-xl transition-all duration-300 border-t-4 border-transparent hover:border-brand-orange overflow-hidden">
                                <div className="p-8">
                                    <div className="w-14 h-14 bg-brand-orange/10 rounded-lg flex items-center justify-center mb-6 group-hover:bg-brand-orange transition-colors duration-300">
                                        <span className="material-icons text-brand-orange text-3xl group-hover:text-white transition-colors duration-300">{cat.icon}</span>
                                    </div>
                                    <h3 className="text-xl font-bold text-slate-900 mb-4 uppercase">{cat.title}</h3>
                                    <ul className="space-y-2 text-slate-500 text-sm">
                                        {cat.items.map((item) => (
                                            <li key={item} className="flex items-center">
                                                <span className="w-1.5 h-1.5 bg-brand-orange rounded-full mr-2 flex-shrink-0" />
                                                {item}
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            </div>
                        ))}
                    </div>

                    {/* Exclusion Notice */}
                    <div className="max-w-3xl mx-auto bg-slate-50 border border-slate-200 rounded-xl p-6 flex flex-col sm:flex-row items-center sm:items-start gap-4 mb-16">
                        <span className="material-icons text-slate-400 text-4xl flex-shrink-0">warning_amber</span>
                        <div className="text-center sm:text-left">
                            <h4 className="text-lg font-bold text-slate-900 mb-2">What We Don&apos;t Take</h4>
                            <p className="text-slate-500 text-sm mb-3">
                                For safety and legal reasons, we cannot accept hazardous waste, chemicals, fuels, oils, paints, or asbestos.
                            </p>
                            <Link
                                href="/items-we-dont-take"
                                className="inline-flex items-center text-brand-orange font-semibold hover:text-orange-600 text-sm transition-colors group"
                            >
                                View Prohibited Items
                                <span className="material-icons text-sm ml-1 transform group-hover:translate-x-1 transition-transform">arrow_forward</span>
                            </Link>
                        </div>
                    </div>
                </section>

                {/* Bottom CTA */}
                <section className="bg-slate-900 py-16">
                    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                        <div className="bg-white/5 rounded-2xl p-8 md:p-12 backdrop-blur-sm border border-white/10 flex flex-col lg:flex-row items-center justify-between gap-8">
                            <div className="text-center lg:text-left max-w-2xl">
                                <h2 className="text-3xl font-bold text-white mb-4">Not sure about an item?</h2>
                                <p className="text-slate-300 text-lg">
                                    Don&apos;t guess. Text us a photo of your junk pile and we&apos;ll confirm instantly if we can take it — and give you a rough estimate.
                                </p>
                            </div>
                            <div className="flex flex-col sm:flex-row items-center gap-6">
                                <Link
                                    href="/get-started"
                                    className="bg-brand-orange hover:bg-orange-600 text-white font-bold py-5 px-10 rounded-full shadow-2xl shadow-orange-900/30 transition-all flex items-center gap-3 text-xl"
                                >
                                    <MessageSquare className="w-6 h-6" />
                                    SEND A PHOTO
                                </Link>
                                <Link
                                    href="tel:8327936566"
                                    className="bg-transparent border-2 border-white text-white hover:bg-white hover:text-slate-900 font-bold py-5 px-10 rounded-full transition-all duration-300 flex items-center gap-3 text-xl"
                                >
                                    <Phone className="text-brand-orange w-6 h-6" />
                                    (832) 793-6566
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
