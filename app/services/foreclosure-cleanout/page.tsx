import { Navbar } from "@/components/Navbar";
import { Footer } from "@/components/Footer";
import {
    Calendar,
    Phone,
    ArrowRight,
    Check,
    Clock,
    Truck,
    Key,
    Building,
    Store,
    Landmark,
    Zap,
    FileText,
    ShieldCheck,
    Recycle
} from "lucide-react";
import Link from "next/link";
import { Metadata } from "next";

export const metadata: Metadata = {
    title: "Foreclosure & Eviction Cleanouts in Houston | Fast Turnaround | CleanSweep",
    description: "Need a property cleared fast? We specialize in foreclosure and eviction cleanouts for landlords, banks, and realtors. Same-day service available. We handle the mess.",
};

export default function ForeclosureCleanoutPage() {
    return (
        <div className="min-h-screen bg-slate-50">
            <Navbar />

            {/* Hero Section */}
            <header className="relative bg-brand-navy overflow-hidden py-20 lg:py-32 pt-36">
                <div className="absolute inset-0 opacity-10 bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-white via-brand-navy to-transparent"></div>
                <div className="absolute inset-0 opacity-10 bg-[url('https://www.transparenttextures.com/patterns/carbon-fibre.png')]"></div>

                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
                    <div className="grid lg:grid-cols-2 gap-12 items-center">
                        <div className="space-y-8">
                            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-slate-800 border border-slate-700 text-xs font-semibold uppercase tracking-wide text-brand-orange">
                                <span className="w-2 h-2 rounded-full bg-brand-orange animate-pulse"></span>
                                Available for Same-Day Pickup
                            </div>
                            <h1 className="text-5xl lg:text-7xl font-extrabold text-white leading-tight">
                                FAST <br />
                                FORECLOSURE & <br />
                                <span className="text-brand-orange">EVICTION CLEANOUTS</span>
                            </h1>
                            <p className="text-lg text-slate-400 max-w-xl leading-relaxed">
                                Speed is key. We handle the mess so you can list the property immediately. Professional, full-service removal for banks, property managers, and landlords.
                            </p>
                            <div className="flex flex-col sm:flex-row gap-4 pt-4">
                                <Link href="/get-started" className="bg-brand-orange hover:bg-orange-600 text-white px-8 py-4 rounded-full text-lg font-bold transition-all shadow-xl shadow-orange-900/30 flex items-center justify-center gap-2 hover:-translate-y-1">
                                    Request Urgent Quote
                                    <ArrowRight className="w-5 h-5" />
                                </Link>
                                <a href="tel:8327936566" className="bg-transparent border-2 border-slate-600 hover:border-white text-white px-8 py-4 rounded-full text-lg font-semibold transition-all flex items-center justify-center gap-2 hover:bg-white/5">
                                    <Phone className="w-5 h-5" />
                                    (832) 793-6566
                                </a>
                            </div>
                            <div className="flex items-center gap-6 text-sm text-slate-500 pt-4">
                                <span className="flex items-center gap-1"><Check className="text-brand-orange w-5 h-5" /> Upfront Pricing</span>
                                <span className="flex items-center gap-1"><Check className="text-brand-orange w-5 h-5" /> Fully Insured</span>
                                <span className="flex items-center gap-1"><Check className="text-brand-orange w-5 h-5" /> Eco-Friendly Disposal</span>
                            </div>
                        </div>

                        <div className="relative lg:h-[600px] h-[400px] w-full rounded-2xl overflow-hidden shadow-2xl border-4 border-slate-800">
                            <div className="absolute inset-0 bg-gradient-to-t from-brand-navy/80 to-transparent z-10"></div>
                            <img
                                alt="Cleanout crew loading a truck with furniture"
                                className="w-full h-full object-cover"
                                src="https://lh3.googleusercontent.com/aida-public/AB6AXuAei-vQDZAnR4YQqXET0exwsn3d_izeYXf6hisBShG1U4ooZxIztaDNJrB0PBNB6KOdO6RxNZaXKkkxk8TGZXcVm-VV-JU4ZryKD5a0oKe9cGcvWNPo3Ch-YFkAK5WJpR2vIF73EKeuOabOgC7rlhPtQaCN_PdWMQ_r6sKD2KaexFpJjiTQyF03ak3arGo4F3V0NRxEgAem3MAU4jkC3-W6pAC4L5_SnZNJGStgPOD2qDr0MbuEQcYglxTAVxbE5SB6GOSR5p_PBAg"
                            />
                            <div className="absolute bottom-8 left-8 right-8 bg-brand-navy/90 backdrop-blur border border-slate-700 p-6 rounded-xl z-20 hidden sm:block">
                                <div className="flex items-start gap-4">
                                    <div className="bg-brand-orange/20 p-3 rounded-lg text-brand-orange">
                                        <Building className="w-8 h-8" />
                                    </div>
                                    <div>
                                        <h3 className="text-white font-bold text-lg">Property Ready in 24h</h3>
                                        <p className="text-slate-400 text-sm mt-1">Our specialized teams clear entire properties quickly so you can maximize ROI and minimize vacancy time.</p>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </header>

            {/* Process Section */}
            <section className="py-20 bg-white">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="text-center mb-16">
                        <h2 className="text-3xl md:text-4xl font-extrabold text-slate-900 mb-4">RAPID RESPONSE PROCESS</h2>
                        <p className="text-slate-600 max-w-2xl mx-auto">No stress, no delays. Here is how we get your property back on the market efficiently.</p>
                    </div>
                    <div className="grid md:grid-cols-3 gap-12">
                        {[
                            { icon: Clock, title: "1. Urgent Assessment", desc: "Call us for a same-day onsite estimate. We understand the urgency of eviction timelines." },
                            { icon: Truck, title: "2. Complete Clearing", desc: "Our uniformed team removes everything inside and out, including yard debris and hazardous items." },
                            { icon: Key, title: "3. Listing Ready", desc: "We sweep up and haul away responsibly. The property is empty, clean, and ready for photos." }
                        ].map((step, i) => (
                            <div key={i} className="text-center group">
                                <div className="w-20 h-20 bg-orange-50 rounded-2xl flex items-center justify-center mx-auto mb-6 transition-transform group-hover:scale-110 duration-300">
                                    <step.icon className="w-10 h-10 text-brand-orange" />
                                </div>
                                <h3 className="text-xl font-bold text-slate-900 mb-3">{step.title}</h3>
                                <p className="text-slate-600 leading-relaxed">{step.desc}</p>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* Commercial Solutions */}
            <section className="py-20 bg-slate-50">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="flex flex-col md:flex-row justify-between items-end mb-12 gap-6">
                        <div>
                            <h2 className="text-3xl md:text-4xl font-extrabold text-slate-900 mb-2">TAILORED SOLUTIONS</h2>
                            <p className="text-slate-600">Services designed for industry professionals.</p>
                        </div>
                        <Link href="/commercial" className="text-brand-orange font-bold hover:text-orange-700 flex items-center gap-1 group">
                            View all commercial services <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                        </Link>
                    </div>
                    <div className="grid md:grid-cols-3 gap-8">
                        <div className="bg-white rounded-2xl p-8 shadow-sm hover:shadow-xl transition-all duration-300 border border-slate-100 group">
                            <div className="w-14 h-14 rounded-full bg-slate-100 flex items-center justify-center mb-6 group-hover:bg-brand-orange group-hover:text-white transition-colors text-slate-600">
                                <Building className="w-6 h-6" />
                            </div>
                            <h3 className="text-xl font-bold text-slate-900 mb-3">For Landlords</h3>
                            <p className="text-slate-600 mb-6 text-sm leading-relaxed">
                                Dealing with a messy eviction? We handle the heavy lifting so you don't have to. Get your rental unit back to generating income faster.
                            </p>
                            <ul className="space-y-2 mb-6 text-sm text-slate-500">
                                <li className="flex items-center gap-2"><span className="w-1.5 h-1.5 rounded-full bg-brand-orange"></span>Unit cleanouts</li>
                                <li className="flex items-center gap-2"><span className="w-1.5 h-1.5 rounded-full bg-brand-orange"></span>Furniture removal</li>
                                <li className="flex items-center gap-2"><span className="w-1.5 h-1.5 rounded-full bg-brand-orange"></span>Bulk trash pickup</li>
                            </ul>
                        </div>

                        <div className="bg-white rounded-2xl p-8 shadow-sm hover:shadow-xl transition-all duration-300 border border-slate-100 group relative overflow-hidden">
                            <div className="absolute top-0 right-0 bg-brand-orange text-white text-xs font-bold px-3 py-1 rounded-bl-lg">POPULAR</div>
                            <div className="w-14 h-14 rounded-full bg-slate-100 flex items-center justify-center mb-6 group-hover:bg-brand-orange group-hover:text-white transition-colors text-slate-600">
                                <Store className="w-6 h-6" />
                            </div>
                            <h3 className="text-xl font-bold text-slate-900 mb-3">For Real Estate Agents</h3>
                            <p className="text-slate-600 mb-6 text-sm leading-relaxed">
                                A cluttered home won't sell. We help you prep listings for the market with speed and professionalism. Impress your clients with swift action.
                            </p>
                            <ul className="space-y-2 mb-6 text-sm text-slate-500">
                                <li className="flex items-center gap-2"><span className="w-1.5 h-1.5 rounded-full bg-brand-orange"></span>Pre-listing cleanouts</li>
                                <li className="flex items-center gap-2"><span className="w-1.5 h-1.5 rounded-full bg-brand-orange"></span>Curb appeal clearing</li>
                                <li className="flex items-center gap-2"><span className="w-1.5 h-1.5 rounded-full bg-brand-orange"></span>Lockbox access</li>
                            </ul>
                        </div>

                        <div className="bg-white rounded-2xl p-8 shadow-sm hover:shadow-xl transition-all duration-300 border border-slate-100 group">
                            <div className="w-14 h-14 rounded-full bg-slate-100 flex items-center justify-center mb-6 group-hover:bg-brand-orange group-hover:text-white transition-colors text-slate-600">
                                <Landmark className="w-6 h-6" />
                            </div>
                            <h3 className="text-xl font-bold text-slate-900 mb-3">For Banks & REO</h3>
                            <p className="text-slate-600 mb-6 text-sm leading-relaxed">
                                Asset management requires reliability. We offer streamlined invoicing and complete property clearing for foreclosed assets.
                            </p>
                            <ul className="space-y-2 mb-6 text-sm text-slate-500">
                                <li className="flex items-center gap-2"><span className="w-1.5 h-1.5 rounded-full bg-brand-orange"></span>Entire estate clearing</li>
                                <li className="flex items-center gap-2"><span className="w-1.5 h-1.5 rounded-full bg-brand-orange"></span>Professional invoicing</li>
                                <li className="flex items-center gap-2"><span className="w-1.5 h-1.5 rounded-full bg-brand-orange"></span>Before/After photos</li>
                            </ul>
                        </div>
                    </div>
                </div>
            </section>

            {/* Why Choose Us */}
            <section className="py-20 bg-white">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <h2 className="text-3xl font-extrabold text-center mb-16 text-slate-900">WHY CHOOSE US?</h2>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
                        {[
                            { icon: Zap, title: "Rapid Response", sub: "Same-day or next-day service available." },
                            { icon: FileText, title: "Professional Invoicing", sub: "Detailed billing for expense tracking." },
                            { icon: ShieldCheck, title: "Fully Insured", sub: "Your property is protected during work." },
                            { icon: Recycle, title: "Eco-Friendly", sub: "We donate and recycle up to 60%." }
                        ].map((item, i) => (
                            <div key={i} className="text-center p-4">
                                <div className="w-16 h-16 rounded-full bg-brand-navy text-white flex items-center justify-center mx-auto mb-4">
                                    <item.icon className="w-8 h-8" />
                                </div>
                                <h4 className="font-bold text-lg mb-2 text-slate-900">{item.title}</h4>
                                <p className="text-sm text-slate-500">{item.sub}</p>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* Testimonials */}
            <section className="py-24 bg-brand-navy text-white">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <h2 className="text-3xl md:text-4xl font-extrabold text-center mb-16">WHAT OUR COMMERCIAL PARTNERS SAY</h2>
                    <div className="grid md:grid-cols-3 gap-8">
                        {[
                            { quote: "CleanSweep saved our listing. The previous tenants left a disaster. The crew had it cleared in 4 hours. Incredible service.", author: "David Miller", role: "Real Estate Agent, Century 21" },
                            { quote: "As a property manager, I need speed. Their online booking was easy, the invoice was professional, and the job was done right.", author: "Sarah Jenkins", role: "Property Manager, Highland Properties" },
                            { quote: "Highly recommend for bank-owned properties. They handle everything from junk removal to deep cleaning referral.", author: "Robert Chen", role: "Asset Manager" }
                        ].map((story, i) => (
                            <div key={i} className="bg-slate-800 border border-slate-700 p-8 rounded-2xl relative">
                                <div className="flex text-brand-orange mb-4">
                                    {[...Array(5)].map((_, j) => <span key={j} className="text-sm">★</span>)}
                                </div>
                                <p className="text-slate-300 italic mb-6">"{story.quote}"</p>
                                <div>
                                    <p className="font-bold text-white">{story.author}</p>
                                    <p className="text-sm text-slate-500">{story.role}</p>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* Pre-footer CTA */}
            <div className="bg-brand-navy border-t border-slate-800 py-12">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col md:flex-row items-center justify-between gap-8">
                    <div className="flex items-center gap-2">
                        <span className="text-brand-orange font-bold text-2xl tracking-tighter">CLEAN</span><span className="font-bold text-2xl tracking-tighter text-white">SWEEP</span>
                    </div>
                    <Link href="/get-started" className="bg-brand-orange hover:bg-orange-600 text-white px-6 py-3 rounded-lg font-bold transition-all flex items-center gap-2">
                        <Calendar className="w-5 h-5" />
                        Book Now
                    </Link>
                </div>
            </div>

            <Footer />
        </div>
    );
}
