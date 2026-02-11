import { Navbar } from "@/components/Navbar";
import { Footer } from "@/components/Footer";
import {
    Check,
    Calendar,
    Phone,
    ArrowRight,
    Trash2,
    Truck,
    Recycle,
    Clock,
    ShieldCheck,
    CreditCard,
    Box,
    Wrench,
    Dumbbell,
    Monitor
} from "lucide-react";
import Link from "next/link";
import { Metadata } from "next";

export const metadata: Metadata = {
    title: "Garage Cleanouts in Houston | Reclaim Your Parking Spot | CleanSweep",
    description: "Can't park in your garage? We offer fast, affordable garage cleanout services in Houston. Same-day pickup available. We sort, haul, and recycle.",
};

export default function GarageCleanoutPage() {
    return (
        <div className="min-h-screen bg-slate-50">
            <Navbar />

            {/* Hero Section */}
            <header className="relative bg-brand-navy overflow-hidden py-20 lg:py-32 pt-36">
                <div className="absolute inset-0 opacity-10 pointer-events-none bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-brand-orange via-brand-navy to-transparent"></div>
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
                    <div className="grid lg:grid-cols-2 gap-12 items-center">
                        <div className="space-y-8">
                            <div className="inline-flex items-center gap-2 bg-white/10 px-4 py-1.5 rounded-full text-sm font-medium text-brand-orange border border-white/10">
                                <span className="w-2 h-2 rounded-full bg-brand-orange animate-pulse"></span>
                                Available for Same-Day Pickup
                            </div>
                            <h1 className="text-5xl lg:text-7xl font-extrabold text-white leading-tight tracking-tight">
                                RECLAIM YOUR <br />
                                <span className="text-brand-orange">PARKING SPOT</span>
                            </h1>
                            <p className="text-lg text-slate-300 max-w-lg leading-relaxed">
                                Professional garage junk removal and decluttering services. We handle the heavy lifting, sorting, and disposal so you can finally fit your car inside again.
                            </p>
                            <div className="flex flex-col sm:flex-row gap-4 pt-4">
                                <Link href="/get-started" className="bg-brand-orange hover:bg-orange-600 text-white px-8 py-4 rounded-full font-bold text-lg transition-all shadow-lg shadow-orange-900/30 flex items-center justify-center gap-2">
                                    Get a Fast Garage Quote <ArrowRight className="w-5 h-5" />
                                </Link>
                                <a href="tel:8327936566" className="bg-transparent border-2 border-slate-600 hover:border-white text-white px-8 py-4 rounded-full font-bold text-lg transition-all flex items-center justify-center gap-2">
                                    <Phone className="w-5 h-5 text-brand-orange" /> (832) 793-6566
                                </a>
                            </div>
                            <div className="flex items-center gap-6 text-sm text-slate-400 pt-4">
                                <span className="flex items-center gap-1"><Check className="text-brand-orange w-5 h-5" /> Upfront Pricing</span>
                                <span className="flex items-center gap-1"><Check className="text-brand-orange w-5 h-5" /> Fully Insured</span>
                            </div>
                        </div>
                        <div className="relative">
                            <div className="absolute -inset-4 bg-brand-orange/20 rounded-2xl blur-xl"></div>
                            <img
                                alt="Cluttered garage full of boxes and old furniture"
                                className="relative rounded-2xl shadow-2xl border-4 border-white/10 w-full object-cover h-[500px]"
                                src="https://lh3.googleusercontent.com/aida-public/AB6AXuA16BdoVlhbML5wYF7IW-WomY4Wb_8Xk7bssZvRifejzQrVhm0qqNxe_PjCWFJG2bN51VGorMn3n6UCT0W4J4SLic5EOngi2C3CbB9gl-21nI8z-3B0p1kuOUWAyFTXsLOUJ-QyUBoyW1pLRKYNiE4GFO0BZ6iUJiIklrwjAS-vB9ieyuKDBWyLtby6UFM6K090PZbKqUVavSSmypKwrmhWXp39ZvBZ7E5jZoBgGlA6n-TXMjPQ25xJ0NHPHQKT80Y5keMxZZ0fKHA"
                            />
                            <div className="absolute bottom-8 left-8 bg-white p-4 rounded-xl shadow-lg border border-slate-100 flex items-center gap-4 max-w-xs animate-bounce" style={{ animationDuration: '3s' }}>
                                <div className="bg-green-100 p-2 rounded-full">
                                    <Recycle className="text-green-600 w-6 h-6" />
                                </div>
                                <div>
                                    <p className="font-bold text-slate-900 text-sm">We Donate & Recycle</p>
                                    <p className="text-xs text-slate-500">Keeping garages clean & green.</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </header>

            {/* Transformation Section (Replaced Slider with Side-by-Side) */}
            <section className="py-20 bg-white">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="text-center mb-16">
                        <span className="text-brand-orange font-bold tracking-wider uppercase text-sm">Real Results</span>
                        <h2 className="text-3xl md:text-4xl font-bold mt-2 text-slate-900">From Cluttered Mess to Car-Ready</h2>
                        <p className="text-slate-600 mt-4 max-w-2xl mx-auto">See the difference a professional cleanout makes. We clear it all out, from floor to ceiling.</p>
                    </div>

                    <div className="grid md:grid-cols-2 gap-8 max-w-6xl mx-auto">
                        <div className="relative rounded-2xl overflow-hidden shadow-xl group">
                            <div className="absolute top-4 left-4 bg-black/70 text-white px-4 py-1 rounded-full text-sm font-bold z-10">BEFORE</div>
                            <img
                                src="https://lh3.googleusercontent.com/aida-public/AB6AXuD3Hlpd5MJod_8A5uyOnGgAOcB2siOv8-H1-OgBSEXGjCQ4M9vv25VAAEpigh3WCeCIbvB3UVavuXmGw2C_8rZCoKglnxsz1FOrxrwuQtYcDC02b1Lq-KhkfITxBxaTDzxuLf7OnJqxZWvy-70YMUmODl5jly07EZuAC__CeWn12HPQ7YDJihj2vWiDmdvr8srSKHRO-zNg-Ig_BPneeUwLWxQga0SXM-FdeYizJk8vQObub9gbK3louzKpi0tr_BrQ-Yc5G7toIU0"
                                alt="Messy garage before cleanout"
                                className="w-full h-[400px] object-cover transition-transform duration-500 group-hover:scale-105"
                            />
                        </div>
                        <div className="relative rounded-2xl overflow-hidden shadow-xl group">
                            <div className="absolute top-4 left-4 bg-brand-orange text-white px-4 py-1 rounded-full text-sm font-bold z-10">AFTER</div>
                            <img
                                src="https://lh3.googleusercontent.com/aida-public/AB6AXuDx-tYgYhonraU_rlfMy0602yB-Gaj9LdLm3I5A9HUKG88xYjy1tXvhm4O_Mq36xx2nSAv_YyUXTnIekGTeVW_odXvRkkPsQ3lhg00p41IQ9qr23uotrILvT4y34cJhPjwK4RE4toRLUK1j_iFn30WilTL2qvM1FBP0CgrD2dD7t4BMTclQqfKF6N_yu3w9GER4T4oXbb3MeIfcWzZ8KLz-6cdMpl-s6_5l7cI64xCcuZkeRTBX77YVvkeqDzwmsy3DxXVIyQcLyag"
                                alt="Clean garage after cleanout"
                                className="w-full h-[400px] object-cover transition-transform duration-500 group-hover:scale-105"
                            />
                        </div>
                    </div>

                    <div className="mt-8 text-center">
                        <p className="text-sm text-slate-500 italic">"The crew cleared out my entire garage in less than 3 hours." - Sarah J.</p>
                    </div>
                </div>
            </section>

            {/* What We Remove */}
            <section className="py-20 bg-slate-50">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="text-center mb-16">
                        <h2 className="text-3xl md:text-4xl font-bold text-slate-900 uppercase tracking-tight">What We Remove</h2>
                        <Link href="/items-we-take" className="inline-flex items-center text-brand-orange font-semibold mt-4 hover:underline">
                            View full item list <ArrowRight className="w-4 h-4 ml-1" />
                        </Link>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
                        {[
                            { icon: Box, title: "Furniture Removal", desc: "Old sofas, broken tables, dusty shelves, and cabinets taking up precious floor space.", href: "/services/furniture-removal" },
                            { icon: Wrench, title: "Old Tool Disposal", desc: "Rusted tools, broken lawnmowers, unused workbenches, and scrap metal piles." },
                            { icon: Trash2, title: "Trash Hauling", desc: "General household junk, boxes of old papers, holiday decorations, and miscellaneous clutter." },
                            { icon: Box, title: "Appliance Disposal", desc: "Unwanted fridges, freezers, washing machines, and dryers that are just gathering dust.", href: "/services/appliance-removal" },
                            { icon: Dumbbell, title: "Sports Equipment", desc: "Bicycles, treadmills, weights, kayaks, and old camping gear you no longer use." },
                            { icon: Monitor, title: "E-Waste Recycling", desc: "We recycle the old electronics found in your garage.", href: "/services/e-waste-recycling" }
                        ].map((item, i) => (
                            <div key={i} className="bg-white p-8 rounded-2xl hover:shadow-xl transition-shadow border border-slate-100 group">
                                <div className="w-14 h-14 bg-orange-100 rounded-xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
                                    <item.icon className="text-brand-orange w-8 h-8" />
                                </div>
                                {item.href ? (
                                    <Link href={item.href} className="hover:text-brand-orange transition-colors">
                                        <h3 className="text-xl font-bold text-slate-900 mb-3">{item.title}</h3>
                                    </Link>
                                ) : (
                                    <h3 className="text-xl font-bold text-slate-900 mb-3">{item.title}</h3>
                                )}
                                <p className="text-slate-600 text-sm leading-relaxed">{item.desc}</p>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* Process Steps */}
            <section className="py-20 bg-white">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="text-center mb-16">
                        <h2 className="text-3xl md:text-4xl font-bold text-slate-900 uppercase tracking-tight">Simple 3-Step Process</h2>
                        <p className="text-slate-600 mt-4">No stress, no mess. Here is how we get the job done efficiently.</p>
                    </div>
                    <div className="grid md:grid-cols-3 gap-8 relative">
                        <div className="hidden md:block absolute top-12 left-[16%] right-[16%] h-0.5 bg-slate-200 -z-0"></div>
                        {[
                            { icon: Calendar, title: "1. Book Online", desc: "Schedule a no-obligation onsite estimate in seconds. Pick a time that works for you." },
                            { icon: Truck, title: "2. We Load It", desc: "Our friendly, uniformed team arrives and does all the heavy lifting from your garage." },
                            { icon: Box, title: "3. It's Gone!", desc: "We haul it away to be responsibly disposed of and recycled. You enjoy your space." }
                        ].map((step, i) => (
                            <div key={i} className="relative z-10 flex flex-col items-center text-center">
                                <div className="w-24 h-24 bg-white border-2 border-orange-100 rounded-2xl flex items-center justify-center shadow-lg mb-6">
                                    <step.icon className="text-brand-orange w-10 h-10" />
                                </div>
                                <h3 className="text-xl font-bold text-slate-900 mb-2">{step.title}</h3>
                                <p className="text-slate-600 text-sm max-w-xs">{step.desc}</p>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* Trust Badges */}
            <section className="py-12 bg-slate-50 border-y border-slate-200">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
                        {[
                            { icon: CreditCard, title: "Upfront Pricing", sub: "No hidden fees." },
                            { icon: Clock, title: "Fast Service", sub: "Same-day available." },
                            { icon: ShieldCheck, title: "Fully Insured", sub: "Your property protected." },
                            { icon: Recycle, title: "Eco-Friendly", sub: "We recycle up to 60%." }
                        ].map((item, i) => (
                            <div key={i} className="flex flex-col items-center text-center">
                                <div className="w-12 h-12 bg-brand-navy rounded-full flex items-center justify-center mb-3">
                                    <item.icon className="text-white w-6 h-6" />
                                </div>
                                <h4 className="font-bold text-slate-900">{item.title}</h4>
                                <p className="text-xs text-slate-500">{item.sub}</p>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* CTA */}
            <section className="py-24 bg-brand-navy relative overflow-hidden">
                <div className="absolute inset-0 opacity-20 pointer-events-none bg-[radial-gradient(circle_at_center,_var(--tw-gradient-stops))] from-brand-orange via-brand-navy to-transparent"></div>
                <div className="max-w-4xl mx-auto px-4 text-center relative z-10">
                    <h2 className="text-4xl md:text-5xl font-extrabold text-white mb-6">Ready to Park Your Car Inside?</h2>
                    <p className="text-xl text-slate-300 mb-10">Don't let junk take over your garage. Get a free estimate today and reclaim your space tomorrow.</p>
                    <div className="flex flex-col sm:flex-row justify-center gap-4">
                        <Link href="/get-started" className="bg-brand-orange hover:bg-orange-600 text-white px-8 py-4 rounded-full font-bold text-lg transition-all shadow-lg shadow-orange-900/30">
                            Get a Free Quote
                        </Link>
                        <a href="tel:8327936566" className="bg-white text-brand-navy hover:bg-slate-100 px-8 py-4 rounded-full font-bold text-lg transition-all">
                            Call (832) 793-6566
                        </a>
                    </div>
                </div>
            </section>

            <Footer />
        </div>
    );
}
