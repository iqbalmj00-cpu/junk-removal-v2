import { Navbar } from "@/components/Navbar";
import { Footer } from "@/components/Footer";
import {
    Calendar,
    Phone,
    ArrowRight,
    Check,
    Recycle,
    Monitor,
    Tv,
    Printer,
    Smartphone,
    ShieldCheck,
    Truck,
    FileText,
    Server
} from "lucide-react";
import Link from "next/link";
import { Metadata } from "next";

export const metadata: Metadata = {
    title: "E-Waste Recycling & Disposal in Houston | Secure & Eco-Friendly | CleanSweep",
    description: "Secure, R2-certified e-waste recycling in Houston. We recycle computers, TVs, monitors, and more. Data destruction guaranteed. Book a pickup.",
};

export default function EWasteRecyclingPage() {
    return (
        <div className="min-h-screen bg-slate-50">
            <Navbar />

            {/* Hero Section */}
            <header className="relative bg-brand-navy overflow-hidden py-20 lg:py-32 pt-36">
                <div className="absolute inset-0 bg-[url('/images/services/e-waste-recycling.png')] bg-cover bg-center opacity-10"></div>
                <div className="absolute inset-0 bg-gradient-to-r from-brand-navy via-brand-navy to-transparent"></div>
                <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col lg:flex-row items-center gap-12">
                    <div className="lg:w-1/2 space-y-6">
                        <div className="inline-flex items-center px-3 py-1 rounded-full bg-slate-800 text-xs font-semibold uppercase tracking-wider text-brand-orange border border-slate-700">
                            Responsible Disposal Guaranteed
                        </div>
                        <h1 className="text-4xl lg:text-6xl font-extrabold text-white leading-tight">
                            ECO-FRIENDLY <br />
                            <span className="text-brand-orange">E-WASTE RECYCLING</span>
                        </h1>
                        <p className="text-lg text-slate-300 max-w-xl leading-relaxed">
                            Don't let old electronics clutter your space or harm the environment. We provide secure, certified recycling for computers, TVs, appliances, and more.
                        </p>
                        <div className="flex flex-col sm:flex-row gap-4 pt-4">
                            <Link href="/get-started" className="bg-brand-orange hover:bg-orange-600 text-white text-lg font-bold py-4 px-8 rounded-full transition-all shadow-lg hover:shadow-orange-500/30 text-center flex items-center justify-center gap-2 group">
                                Get Price Now <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                            </Link>
                            <a href="tel:8327936566" className="border-2 border-slate-600 hover:border-white text-white text-lg font-semibold py-4 px-8 rounded-full transition-all text-center flex items-center justify-center gap-2">
                                <Phone className="w-5 h-5" /> (832) 793-6566
                            </a>
                        </div>
                        <div className="flex items-center gap-6 text-sm text-slate-400 pt-2 font-medium">
                            <span className="flex items-center gap-1"><Check className="text-brand-orange w-5 h-5" /> R2 Certified Partners</span>
                            <span className="flex items-center gap-1"><Check className="text-brand-orange w-5 h-5" /> Data Security</span>
                        </div>
                    </div>
                    <div className="lg:w-1/2 relative">
                        <div className="relative rounded-2xl overflow-hidden shadow-2xl border-4 border-slate-700/50">
                            <img
                                alt="Professional recycling team collecting electronic waste"
                                className="w-full h-auto object-cover transform hover:scale-105 transition-transform duration-700"
                                src="https://lh3.googleusercontent.com/aida-public/AB6AXuDIqs-52l7tcDvtyuLkvf7rxyrmNSohqxtqH3MUVRJN31QLeS2XfwsQ5seW6fMAakVYXbVNlgRYpnrpQy_xFoVpZOGgXtSzWaHbm8aQiQR-qQUSIL14RC8zfq6KppIPP0lIclH4Gyrm1ZpQMR_utkAsvRAZuV7m-7PNKlEn639trJkEN4jWt61LzHT8SNGZfwiTrmJdxzRS3BRzeEjvVZx6xno65vGvpEsyu5IMoO6xPUY_EoucNPpa_5OOFsfkkLKOQno6r2hBbHQ"
                            />
                            <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 to-transparent p-8">
                                <p className="text-white font-medium">We handle the heavy lifting safely.</p>
                            </div>
                        </div>
                        <div className="absolute -bottom-6 -right-6 bg-white p-4 rounded-xl shadow-xl flex items-center gap-3 border border-slate-100 max-w-xs hidden md:flex">
                            <div className="bg-green-100 p-2 rounded-full">
                                <Recycle className="w-6 h-6 text-green-600" />
                            </div>
                            <div>
                                <p className="text-sm font-bold text-slate-900">100% Landfill Diversion</p>
                                <p className="text-xs text-slate-500">Target for all electronics</p>
                            </div>
                        </div>
                    </div>
                </div>
            </header>

            {/* What We Recycle */}
            <section className="py-20 bg-white">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="text-center mb-16">
                        <h2 className="text-3xl lg:text-4xl font-extrabold text-slate-900 mb-4">WHAT WE RECYCLE</h2>
                        <p className="text-slate-600 max-w-2xl mx-auto">
                            From outdated office equipment to household gadgets, we ensure every component is processed responsibly.
                        </p>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
                        {[
                            { icon: Tv, title: "TV Disposal", desc: "CRT, LED, LCD, Plasma. We handle heavy screens safely." },
                            { icon: Monitor, title: "Computers & Monitors", desc: "Desktops, laptops, servers, and peripherals." },
                            { icon: Printer, title: "Printers & Scanners", desc: "Large office copiers or small home printers." },
                            { icon: Smartphone, title: "Mobile Devices", desc: "Phones, tablets, and small handheld electronics." }
                        ].map((item, i) => (
                            <div key={i} className="group bg-slate-50 rounded-2xl p-8 text-center hover:shadow-xl transition-all border border-slate-100 hover:border-brand-orange/30">
                                <div className="w-16 h-16 bg-orange-100 rounded-2xl flex items-center justify-center mx-auto mb-6 group-hover:bg-brand-orange group-hover:text-white transition-colors text-brand-orange">
                                    <item.icon className="w-8 h-8" />
                                </div>
                                <h3 className="text-xl font-bold text-slate-900 mb-2">{item.title}</h3>
                                <p className="text-sm text-slate-500">{item.desc}</p>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* Corporate Services */}
            <section className="py-20 bg-slate-100 border-y border-slate-200">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="bg-white rounded-3xl overflow-hidden shadow-2xl flex flex-col lg:flex-row">
                        <div className="lg:w-1/2 p-10 lg:p-16 flex flex-col justify-center">
                            <div className="flex items-center gap-2 mb-4">
                                <span className="bg-blue-100 text-blue-700 text-xs font-bold px-3 py-1 rounded-full uppercase tracking-wider">For Business</span>
                            </div>
                            <h2 className="text-3xl lg:text-4xl font-extrabold text-slate-900 mb-6">Corporate E-Waste & Data Destruction</h2>
                            <p className="text-slate-600 mb-8 text-lg">
                                We offer specialized bulk pickup services for offices undergoing upgrades or cleanouts. Our process ensures sensitive data is physically destroyed or digitally wiped according to industry standards.
                            </p>
                            <ul className="space-y-4 mb-8">
                                {[
                                    { icon: ShieldCheck, title: "Secure Chain of Custody", desc: "Tracked from pickup to destruction." },
                                    { icon: Truck, title: "Bulk Logistics", desc: "Palletized pickups and loading dock service." },
                                    { icon: FileText, title: "Certificates of Destruction", desc: "Provided for compliance and peace of mind." }
                                ].map((item, i) => (
                                    <li key={i} className="flex items-start">
                                        <item.icon className="text-brand-orange mr-3 mt-1 w-6 h-6" />
                                        <div>
                                            <h4 className="font-bold text-slate-900">{item.title}</h4>
                                            <p className="text-sm text-slate-500">{item.desc}</p>
                                        </div>
                                    </li>
                                ))}
                            </ul>
                            <Link href="/commercial" className="inline-block w-fit bg-brand-navy hover:bg-slate-800 text-white font-bold py-3 px-8 rounded-lg transition-colors">
                                Request Corporate Quote
                            </Link>
                        </div>
                        <div className="lg:w-1/2 bg-slate-200 h-96 lg:h-auto relative">
                            <img
                                alt="Server room recycling"
                                className="w-full h-full object-cover"
                                src="https://lh3.googleusercontent.com/aida-public/AB6AXuBG02V8gmK0rw7esChuAs-6NFKY_BkdVDP22tOTphgvLxz4FT1KOLQW_VP2tLxSSpAMr49CZIA0jcD1lJEjUASoJGcOM3wDO7UuXT61fLwpAy8Ax0rYlrPhpR-GXZTVuVGvCB9Asr69ll9C_aPtqzcsb5v3LFjuX7TpXUVdQ7pVgV0qHEtXMhyE-BBD_so3kDIIqQXO0txhVf7H4OyJ2hQlmd7Ls3AYR-rF7EKdPlobdpl4mcbDhacviNoPRsCF0jm2xsd5FWeo82s"
                            />
                            <div className="absolute inset-0 bg-brand-navy/10 mix-blend-multiply"></div>
                        </div>
                    </div>
                </div>
            </section>

            {/* How It Works */}
            <section className="py-20 bg-white">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="text-center mb-16">
                        <h2 className="text-3xl lg:text-4xl font-extrabold text-slate-900">HOW E-WASTE RECYCLING WORKS</h2>
                        <p className="mt-4 text-slate-600">Simple, secure, and sustainable.</p>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-8 relative">
                        <div className="hidden md:block absolute top-12 left-[16%] right-[16%] h-0.5 bg-slate-200 -z-10"></div>
                        {[
                            { icon: Calendar, title: "1. Schedule Pickup", desc: "Book online or call. We offer same-day service for urgent needs." },
                            { icon: Truck, title: "2. We Load & Haul", desc: "Our uniformed team does the heavy lifting. You point, we clear." },
                            { icon: Recycle, title: "3. Responsible Recycling", desc: "Items are sorted at our facility. Hazardous materials are processed safely." }
                        ].map((step, i) => (
                            <div key={i} className="flex flex-col items-center text-center bg-white p-4">
                                <div className="w-24 h-24 bg-white border-4 border-brand-orange rounded-full flex items-center justify-center shadow-lg mb-6 z-10 text-brand-orange">
                                    <step.icon className="w-10 h-10" />
                                </div>
                                <h3 className="text-xl font-bold text-slate-900 mb-2">{step.title}</h3>
                                <p className="text-sm text-slate-500 px-8">{step.desc}</p>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* Trust Badges */}
            <section className="py-16 bg-slate-100 border-t border-slate-200">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
                        {[
                            { icon: Check, title: "Upfront Pricing", sub: "No hidden fees. Firm quote." },
                            { icon: Calendar, title: "Fast Service", sub: "Same-day/Next-day available." },
                            { icon: ShieldCheck, title: "Fully Insured", sub: "Your property is protected." },
                            { icon: Recycle, title: "Eco-Friendly", sub: "We target 0% landfill." }
                        ].map((item, i) => (
                            <div key={i} className="flex flex-col items-center text-center">
                                <div className="bg-slate-900 text-white p-4 rounded-full mb-4 shadow-lg">
                                    <item.icon className="w-6 h-6" />
                                </div>
                                <h4 className="font-bold text-slate-900">{item.title}</h4>
                                <p className="text-xs text-slate-500 mt-1">{item.sub}</p>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* CTA */}
            <section className="bg-brand-navy py-16 relative overflow-hidden text-center">
                <div className="max-w-4xl mx-auto px-4 relative z-10">
                    <h2 className="text-3xl lg:text-5xl font-extrabold text-white mb-6">Ready to clear the clutter?</h2>
                    <p className="text-xl text-slate-300 mb-10">
                        Professional e-waste removal for homes and businesses. Schedule your pickup today.
                    </p>
                    <div className="flex flex-col sm:flex-row justify-center gap-4">
                        <Link href="/get-started" className="bg-brand-orange hover:bg-orange-600 text-white font-bold py-4 px-10 rounded-full text-lg shadow-xl hover:shadow-orange-500/20 transition-all">
                            Book E-Waste Pickup
                        </Link>
                    </div>
                </div>
            </section>

            <Footer />
        </div>
    );
}
