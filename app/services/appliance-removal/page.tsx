import { Navbar } from "@/components/Navbar";
import { Footer } from "@/components/Footer";
import {
    Calendar,
    Phone,
    ArrowRight,
    Check,
    Recycle,
    Refrigerator,
    WashingMachine,
    Tv,
    Flame,
    Wind,
    Menu,
    Zap,
    PowerOff,
    Dumbbell,
    Leaf,
    ShieldCheck
} from "lucide-react";
import Link from "next/link";
import { Metadata } from "next";

export const metadata: Metadata = {
    title: "Appliance Removal & Recycling in Houston | CleanSweep",
    description: "Safe, eco-friendly appliance removal in Houston. We recycle refrigerators, washers, dryers, and more. Disconnection included. Schedule online.",
};

export default function ApplianceRemovalPage() {
    return (
        <div className="min-h-screen bg-slate-50">
            <Navbar />

            {/* Hero Section */}
            <header className="relative bg-brand-navy overflow-hidden py-20 lg:py-32 pt-36">
                <div className="absolute inset-0 z-0 opacity-20 bg-[url('/images/services/appliance-removal.png')] bg-cover bg-center"></div>
                <div className="absolute inset-0 z-0 bg-gradient-to-r from-brand-navy via-brand-navy/95 to-brand-navy/80"></div>
                <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
                        <div className="space-y-6">
                            <div className="inline-block bg-slate-800 backdrop-blur-sm border border-slate-700 rounded-full px-4 py-1 text-xs font-semibold text-brand-orange uppercase tracking-wider">
                                Responsible Recycling & Disposal
                            </div>
                            <h1 className="text-5xl md:text-6xl font-extrabold text-white leading-tight">
                                Safe Appliance <br />
                                <span className="text-brand-orange">Removal Services</span>
                            </h1>
                            <p className="text-slate-300 text-lg md:text-xl max-w-lg leading-relaxed">
                                Don't break your back trying to move that old fridge. We handle refrigerator recycling, freezer disposal, washer removal, and more. We disconnect, haul, and responsibly recycle.
                            </p>
                            <div className="flex flex-col sm:flex-row gap-4 pt-4">
                                <Link href="/get-started" className="bg-brand-orange hover:bg-orange-600 text-white font-bold py-4 px-8 rounded-full transition shadow-xl hover:shadow-2xl flex items-center justify-center gap-2 text-lg group">
                                    Request Appliance Removal
                                    <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                                </Link>
                                <a href="tel:8327936566" className="border-2 border-slate-500 hover:border-white text-white font-semibold py-4 px-8 rounded-full transition flex items-center justify-center gap-2 text-lg">
                                    <Phone className="w-5 h-5" /> (832) 793-6566
                                </a>
                            </div>
                            <div className="flex items-center gap-6 text-sm text-slate-400 pt-2 font-medium">
                                <span className="flex items-center gap-1"><Check className="text-brand-orange w-5 h-5" /> Eco-Friendly Disposal</span>
                                <span className="flex items-center gap-1"><Check className="text-brand-orange w-5 h-5" /> Licensed & Insured</span>
                            </div>
                        </div>
                        <div className="relative hidden lg:block">
                            <div className="absolute -inset-4 bg-brand-orange/20 rounded-2xl blur-xl"></div>
                            <img
                                alt="Team members moving a large refrigerator"
                                className="relative rounded-2xl shadow-2xl border-4 border-slate-800 object-cover h-[500px] w-full transform -rotate-1 hover:rotate-0 transition duration-500"
                                src="https://lh3.googleusercontent.com/aida-public/AB6AXuCg2QhfoIbFobhFLsBqnMe9sKux04MMxzQGVh4tPhm1CwdO0fCAxShTW0A6C8qZ9_mOu0cDuPDyn1jtgg0cvPQdb2LTilsNhJqg-lCFU23wM46uNJ_7oImbrKQY5KCEvLfM48yv7YM6ajOGmspnUVRrMBDxr5t8h0oQXrs7DEDUvoCAPaAtacwttUrOeiEADAxyaSsurEIfm3iC2MYMA_RTfIqg-khu374WbLz5gJ5343yiTER5APbvN6PLyEwTDlY94144RFQr2lo"
                            />
                            <div className="absolute -bottom-6 -left-6 bg-white p-4 rounded-xl shadow-lg border-l-4 border-brand-orange max-w-xs animate-bounce" style={{ animationDuration: '3s' }}>
                                <div className="flex items-start gap-3">
                                    <div className="bg-green-100 p-2 rounded-full text-green-600">
                                        <Recycle className="w-6 h-6" />
                                    </div>
                                    <div>
                                        <p className="font-bold text-slate-900">We Recycle!</p>
                                        <p className="text-xs text-slate-500">Over 60% of collected appliances are recycled or donated.</p>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </header>

            {/* Why Choose Us */}
            <section className="py-20 bg-white">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="text-center mb-16">
                        <h2 className="text-3xl md:text-4xl font-bold text-slate-900 mb-4">Why Choose Us For Appliance Disposal?</h2>
                        <p className="text-slate-600 max-w-2xl mx-auto text-lg">Getting rid of old appliances is tough. They are heavy, awkward, and hard to dispose of legally. Let our professionals handle the hard work.</p>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                        {[
                            { icon: PowerOff, title: "We Disconnect & Unplug", desc: "Unsure how to disconnect that washer? Our trained team can safely disconnect water lines and unplug units before removal." },
                            { icon: Dumbbell, title: "No Heavy Lifting", desc: "Save your back and your walls. We have the dollies, straps, and muscle to maneuver heavy items out of tight spaces safely." },
                            { icon: Leaf, title: "Eco-Friendly Disposal", desc: "We don't just dump it. We ensure Freon is handled correctly and metals are recycled, keeping toxic waste out of landfills." }
                        ].map((item, i) => (
                            <div key={i} className="bg-slate-50 p-8 rounded-2xl text-center hover:-translate-y-1 transition duration-300 border border-slate-100 group">
                                <div className="bg-orange-100 text-brand-orange w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-6 group-hover:scale-110 transition-transform">
                                    <item.icon className="w-8 h-8" />
                                </div>
                                <h3 className="text-xl font-bold text-slate-900 mb-3">{item.title}</h3>
                                <p className="text-slate-600 text-sm leading-relaxed">{item.desc}</p>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* Items We Take */}
            <section className="py-20 bg-slate-50 border-y border-slate-200">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="flex flex-col md:flex-row justify-between items-end mb-12 gap-4">
                        <div>
                            <h2 className="text-3xl md:text-4xl font-bold text-slate-900 mb-2">What We Take</h2>
                            <p className="text-slate-600">If it's an appliance, big or small, we can haul it.</p>
                        </div>
                        <Link href="/items-we-take" className="hidden md:flex items-center text-brand-orange font-bold hover:text-orange-700 transition gap-1 group">
                            View full item list <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                        </Link>
                    </div>
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
                        {[
                            { icon: Refrigerator, title: "Refrigerators", sub: "Fridges, Freezers, Mini-fridges" },
                            { icon: WashingMachine, title: "Washers & Dryers", sub: "Top-load, Front-load, Stackables" },
                            { icon: Menu, title: "Kitchen Appliances", sub: "Stoves, Microwaves, Dishwashers" }, // Menu icon as placeholder for stove/microwave
                            { icon: Wind, title: "AC Units", sub: "Window units, Portable ACs, Fans" },
                            { icon: Tv, title: "Televisions", sub: "CRT, Plasma, LED, Flat screens", href: "/services/e-waste-recycling" },
                            { icon: Flame, title: "Water Heaters", sub: "Tank, Tankless, Electric, Gas" },
                            { icon: Zap, title: "Grills & Outdoor", sub: "BBQ Grills, Smokers, Patio Heaters" },
                            { icon: Zap, title: "And More", sub: "Small electronics, vacuums, etc." }
                        ].map((item, i) => (
                            <div key={i} className="bg-white p-6 rounded-xl shadow-sm border border-slate-100 hover:shadow-md transition group">
                                <div className="bg-orange-50 text-brand-orange w-12 h-12 rounded-full flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                                    <item.icon className="w-6 h-6" />
                                </div>
                                {item.href ? (
                                    <Link href={item.href} className="hover:text-brand-orange transition-colors">
                                        <h4 className="text-lg font-bold text-slate-900 mb-1">{item.title}</h4>
                                    </Link>
                                ) : (
                                    <h4 className="text-lg font-bold text-slate-900 mb-1">{item.title}</h4>
                                )}
                                <p className="text-xs text-slate-500">{item.sub}</p>
                            </div>
                        ))}
                    </div>
                    <div className="mt-8 text-center md:hidden">
                        <Link href="/items-we-take" className="inline-flex items-center text-brand-orange font-bold hover:text-orange-600 transition gap-1">
                            View full item list <ArrowRight className="w-4 h-4" />
                        </Link>
                    </div>
                </div>
            </section>

            {/* How It Works */}
            <section className="py-20 bg-white">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="text-center mb-16">
                        <h2 className="text-3xl md:text-4xl font-bold text-slate-900 mb-4">How It Works</h2>
                        <p className="text-slate-500">Simple, transparent, and hassle-free removal.</p>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-12 text-center relative">
                        <div className="hidden md:block absolute top-12 left-0 w-full h-0.5 bg-slate-100 -z-10"></div>
                        {[
                            { icon: Calendar, title: "1. Book Online", desc: "Schedule a no-obligation estimate in seconds." },
                            { icon: Refrigerator, title: "2. We Load It", desc: "Our friendly team arrives and does the heavy lifting." }, // Truck icon better here?
                            { icon: Check, title: "3. It's Gone!", desc: "We haul it away to be responsibly disposed of and recycled." }
                        ].map((step, i) => (
                            <div key={i} className="bg-white p-4 z-10">
                                <div className="bg-white border-2 border-brand-orange w-24 h-24 rounded-2xl flex items-center justify-center mx-auto mb-6 shadow-lg text-brand-orange">
                                    <step.icon className="w-10 h-10" />
                                </div>
                                <h4 className="text-xl font-bold text-slate-900 mb-2">{step.title}</h4>
                                <p className="text-slate-500 text-sm">{step.desc}</p>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* Trust Badges */}
            <section className="py-12 bg-slate-50 border-t border-slate-200">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
                        {[
                            { icon: Check, title: "Upfront Pricing", sub: "No hidden fees." },
                            { icon: Calendar, title: "Fast Service", sub: "Same-day/Next-day." },
                            { icon: ShieldCheck, title: "Fully Insured", sub: "Property protected." },
                            { icon: Recycle, title: "Eco-Friendly", sub: "We recycle up to 60%." }
                        ].map((item, i) => (
                            <div key={i} className="flex flex-col items-center text-center">
                                <div className="bg-slate-900 text-white rounded-full p-3 mb-3">
                                    <item.icon className="w-6 h-6" />
                                </div>
                                <h5 className="font-bold text-slate-900 text-sm">{item.title}</h5>
                                <p className="text-xs text-slate-500">{item.sub}</p>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* CTA */}
            <section className="bg-brand-navy py-16 px-6 md:px-12 text-center">
                <div className="max-w-4xl mx-auto">
                    <h2 className="text-3xl md:text-4xl font-bold text-white mb-6">Ready to clear the clutter?</h2>
                    <p className="text-slate-400 mb-8 text-lg">Schedule your appliance removal today and reclaim your space.</p>
                    <div className="flex flex-col sm:flex-row justify-center gap-4">
                        <Link href="/get-started" className="bg-brand-orange hover:bg-orange-600 text-white font-bold py-4 px-10 rounded-full transition shadow-lg text-lg flex items-center justify-center gap-2">
                            <Calendar className="w-5 h-5" /> Book Now
                        </Link>
                        <a href="tel:8327936566" className="bg-transparent border-2 border-slate-600 hover:bg-slate-800 text-white font-bold py-4 px-10 rounded-full transition text-lg flex items-center justify-center gap-2">
                            <Phone className="w-5 h-5" /> Contact Us
                        </a>
                    </div>
                </div>
            </section>

            <Footer />
        </div>
    );
}
