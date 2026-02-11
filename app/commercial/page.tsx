import { Metadata } from 'next';
import Link from 'next/link';
import Image from 'next/image';
import { Phone, Camera, Building2, HardHat, Briefcase, Store, Clock, Receipt, ShieldCheck } from 'lucide-react';
import { Navbar } from '@/components/Navbar';
import { Footer } from '@/components/Footer';

export const metadata: Metadata = {
    title: 'Commercial Junk Removal | Clean Sweep Junk Removal',
    description: 'Professional commercial junk removal for property managers, contractors, offices, and retail. Reliable scheduling, upfront pricing, and full liability insurance.',
};

const industries = [
    {
        icon: <Building2 className="w-10 h-10" />,
        title: 'Property Managers & Landlords',
        description: 'Apartment cleanouts, eviction debris removal, and common area clearing.',
    },
    {
        icon: <HardHat className="w-10 h-10" />,
        title: 'Contractors & Renovation Crews',
        description: 'Construction debris, drywall, flooring, and job site waste management.',
    },
    {
        icon: <Briefcase className="w-10 h-10" />,
        title: 'Offices & Warehouses',
        description: 'Old furniture, e-waste, shelving units, and pallet removal services.',
    },
    {
        icon: <Store className="w-10 h-10" />,
        title: 'Retail Stores & Storage Units',
        description: 'Store closures, inventory disposal, display rack removal, and seasonal cleanups.',
    },
];

const features = [
    {
        icon: <Clock className="w-12 h-12" />,
        title: 'Priority Scheduling & Fleet Dispatch',
        description: "We respect your business hours. Book same-day or next-day pickups with guaranteed 2-hour arrival windows. Dedicated account managers for recurring contracts.",
    },
    {
        icon: <Receipt className="w-12 h-12" />,
        title: 'Net-30 Terms for Commercial Accounts',
        description: 'Streamlined billing built for procurement teams. We accept PO numbers, offer Net-30 payment terms for approved accounts, and provide detailed electronic invoices for your AP department.',
    },
    {
        icon: <ShieldCheck className="w-12 h-12" />,
        title: 'Fully Insured & Bonded',
        description: 'Your property is protected. We carry comprehensive general liability insurance and are fully bonded. Certificate of Insurance (COI) available on request for your records.',
    },
];

export default function CommercialPage() {
    return (
        <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
            <Navbar />
            <main className="flex-grow">
                {/* Hero */}
                <section className="relative bg-slate-900 overflow-hidden">
                    {/* Background Image (decorative) */}
                    <div className="absolute inset-0 z-0">
                        <Image
                            alt="Modern spacious clean office interior"
                            className="object-cover opacity-20"
                            src="https://lh3.googleusercontent.com/aida-public/AB6AXuCJ5QDW1Rdx8DmZFxe-BWCyNwS4MuViUV5kDMsvIBmpZWhCoS6blfiiqFZ0J7slg-Uj0hu9hVAhCFWZZXdZLh8byC13j_otx2X1UJFu8ibnuQehuwpyjBreVuiKk0d5VagqKrlQ-KV9mvyRkDAHKQt5LZKcsW5FfMeahTnmk5xqvH4R2MHfAslfYqOXyFUl8a_6DQ0hw6CdsUqY7QAni_WBu2WotZOE0madPPrOkHvsNLsORtFQGC4_2ZPjybB085mgqOhylTmmkY0"
                            fill
                            sizes="100vw"
                            priority
                        />
                        <div className="absolute inset-0 bg-gradient-to-r from-slate-900 via-slate-900/90 to-transparent" />
                    </div>
                    <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-36 pb-24 lg:pb-32">
                        <div className="max-w-3xl">
                            <div className="inline-flex items-center px-3 py-1 rounded bg-brand-orange/10 border border-brand-orange/30 mb-6 backdrop-blur-sm">
                                <span className="w-2 h-2 rounded-full bg-brand-orange mr-2 animate-pulse" />
                                <span className="text-brand-orange font-bold text-xs uppercase tracking-widest">B2B Commercial Services</span>
                            </div>
                            <h1 className="text-5xl lg:text-7xl font-extrabold text-white uppercase tracking-tight leading-tight mb-6">
                                Commercial <br />
                                <span className="text-transparent bg-clip-text bg-gradient-to-r from-brand-orange to-orange-400">Junk Removal</span>
                            </h1>
                            <p className="text-xl text-slate-300 mb-8 max-w-2xl leading-relaxed">
                                We help businesses remove junk quickly with reliable scheduling and upfront pricing. Ideal for property managers, contractors, offices, and retail.
                            </p>
                            <div className="flex flex-wrap gap-x-6 gap-y-2 mb-10 text-sm font-bold text-slate-300 uppercase tracking-wider">
                                <span className="flex items-center gap-2"><ShieldCheck className="w-4 h-4 text-brand-orange" /> Fully Insured & Bonded</span>
                                <span className="flex items-center gap-2"><Receipt className="w-4 h-4 text-brand-orange" /> COI Available on Request</span>
                                <span className="flex items-center gap-2"><Clock className="w-4 h-4 text-brand-orange" /> Net-30 Terms</span>
                            </div>
                            <div className="flex flex-col sm:flex-row gap-6">
                                <Link
                                    href="/get-started"
                                    className="flex items-center justify-center bg-brand-orange hover:bg-orange-600 text-white px-10 py-5 rounded-full font-bold text-xl transition-all shadow-2xl shadow-orange-900/30 uppercase tracking-wide gap-3"
                                >
                                    <Camera className="w-6 h-6" />
                                    Get A Quote
                                </Link>
                                <Link
                                    href="tel:8327936566"
                                    className="flex items-center justify-center bg-transparent border-2 border-white text-white hover:bg-white hover:text-slate-900 px-10 py-5 rounded-full font-bold text-xl transition-all duration-300 gap-3"
                                >
                                    <Phone className="text-brand-orange w-6 h-6" />
                                    (832) 793-6566
                                </Link>
                            </div>
                        </div>
                    </div>
                </section>

                {/* Industries */}
                <section className="py-16 lg:py-24 bg-white border-b border-slate-100">
                    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                        <div className="text-center mb-16">
                            <h2 className="text-3xl font-bold text-slate-900 uppercase tracking-tight">Industries We Serve</h2>
                            <div className="w-20 h-1.5 bg-brand-orange mx-auto mt-4 rounded-full" />
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
                            {industries.map((ind) => (
                                <div key={ind.title} className="group p-8 bg-slate-50 rounded-xl border border-slate-100 hover:border-brand-orange transition-all duration-300 hover:-translate-y-1">
                                    <div className="w-16 h-16 bg-brand-orange/10 rounded-lg flex items-center justify-center mb-6 text-brand-orange group-hover:bg-brand-orange group-hover:text-white transition-colors duration-300">
                                        {ind.icon}
                                    </div>
                                    <h3 className="text-lg font-bold text-slate-900 mb-2 uppercase">{ind.title}</h3>
                                    <p className="text-slate-500 text-sm">{ind.description}</p>
                                </div>
                            ))}
                        </div>
                    </div>
                </section>

                {/* Features */}
                <section className="py-20 bg-slate-50">
                    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-12">
                            {features.map((feat) => (
                                <div key={feat.title} className="flex flex-col items-start">
                                    <div className="mb-4 text-brand-orange">
                                        {feat.icon}
                                    </div>
                                    <h3 className="text-2xl font-bold text-slate-900 mb-3 uppercase tracking-tight">{feat.title}</h3>
                                    <p className="text-slate-500 leading-relaxed">{feat.description}</p>
                                </div>
                            ))}
                        </div>
                    </div>
                </section>

                {/* CTA */}
                <section className="py-16 px-4">
                    <div className="max-w-5xl mx-auto bg-brand-orange rounded-2xl shadow-2xl overflow-hidden relative">
                        <div className="absolute inset-0 opacity-10" style={{ backgroundImage: 'repeating-linear-gradient(45deg, #000 0, #000 10px, transparent 10px, transparent 20px)' }} />
                        <div className="relative z-10 px-8 py-16 text-center">
                            <h2 className="text-4xl md:text-5xl font-black text-white uppercase tracking-tight mb-4">
                                Request a Commercial Quote
                            </h2>
                            <p className="text-white/90 text-lg mb-10 font-medium max-w-2xl mx-auto">
                                Get a fast, accurate estimate for your business cleanout needs. Choose the method that works best for you.
                            </p>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-3xl mx-auto">
                                <Link
                                    href="/get-started"
                                    className="group bg-white hover:bg-slate-50 rounded-xl p-6 transition-all duration-200 shadow-lg hover:shadow-xl transform hover:-translate-y-1 flex flex-col items-center"
                                >
                                    <div className="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mb-4 group-hover:bg-slate-200 transition-colors">
                                        <Camera className="w-8 h-8 text-slate-900" />
                                    </div>
                                    <h3 className="text-xl font-bold text-slate-900 uppercase mb-1">Upload Photos</h3>
                                    <p className="text-slate-500 text-sm">For an instant price estimate</p>
                                </Link>
                                <Link
                                    href="tel:8327936566"
                                    className="group bg-slate-900 hover:bg-slate-800 rounded-xl p-6 transition-all duration-200 shadow-lg hover:shadow-xl transform hover:-translate-y-1 flex flex-col items-center"
                                >
                                    <div className="w-16 h-16 bg-white/10 rounded-full flex items-center justify-center mb-4 group-hover:bg-white/20 transition-colors">
                                        <Phone className="w-8 h-8 text-white" />
                                    </div>
                                    <h3 className="text-xl font-bold text-white uppercase mb-1">Call For Site Visit</h3>
                                    <p className="text-slate-400 text-sm">Schedule a free on-site assessment</p>
                                </Link>
                            </div>
                        </div>
                    </div>
                </section>

                {/* Stats Bar */}
                <section className="py-12 bg-white border-t border-slate-200">
                    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
                            {[
                                { number: '10k+', label: 'Jobs Completed' },
                                { number: '500+', label: 'Commercial Partners' },
                                { number: '100%', label: 'Recycling Rate' },
                                { number: '24h', label: 'Response Time' },
                            ].map((stat) => (
                                <div key={stat.label}>
                                    <span className="block text-4xl font-black text-slate-900 mb-1">{stat.number}</span>
                                    <span className="text-sm font-semibold text-slate-500 uppercase tracking-wide">{stat.label}</span>
                                </div>
                            ))}
                        </div>
                    </div>
                </section>
            </main>
            <Footer />
        </div>
    );
}
