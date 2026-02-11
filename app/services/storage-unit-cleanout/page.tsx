import { Navbar } from "@/components/Navbar";
import { Footer } from "@/components/Footer";
import {
    Calendar,
    Phone,
    ArrowRight,
    Check,
    Truck,
    Trash2,
    Key,
    Warehouse,
    DollarSign,
    Sparkles,
    Recycle,
    Gavel,
    CreditCard,
    Clock,
    ShieldCheck,
    Globe
} from "lucide-react";
import Link from "next/link";
import { Metadata } from "next";

export const metadata: Metadata = {
    title: "Storage Unit Cleanouts in Houston | Stop Paying Monthly Fees | CleanSweep",
    description: "Stop paying for junk! We provide fast, full-service storage unit cleanouts in Houston. We sweep it clean so you get your deposit back. Same-day service.",
};

export default function StorageUnitCleanoutPage() {
    return (
        <div className="min-h-screen bg-slate-50">
            <Navbar />

            {/* Hero Section */}
            <header className="relative bg-brand-navy overflow-hidden py-20 lg:py-32 pt-36">
                <div className="absolute inset-0 opacity-10 mix-blend-overlay bg-[url('https://images.unsplash.com/photo-1595846519845-68e298c2edd8?q=80&w=2574&auto=format&fit=crop')] bg-cover bg-center"></div>
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
                    <div className="grid lg:grid-cols-2 gap-12 items-center">
                        <div>
                            <div className="inline-flex items-center px-3 py-1 rounded-full bg-slate-800 border border-slate-700 text-xs font-semibold tracking-wide uppercase text-slate-300 mb-6">
                                Available for Same-Day Pickup
                            </div>
                            <h1 className="text-5xl lg:text-7xl font-black text-white leading-tight mb-6 tracking-tight">
                                STOP PAYING <br />
                                MONTHLY FEES <br />
                                FOR <span className="text-brand-orange">JUNK</span>
                            </h1>
                            <p className="text-lg text-slate-300 mb-8 max-w-lg leading-relaxed">
                                Reclaim your freedom from monthly storage costs. Professional, full-service removal for storage lockers. We handle the heavy lifting, sweeping, and disposal so you can stop the billing cycle.
                            </p>
                            <div className="flex flex-col sm:flex-row gap-4">
                                <Link href="/get-started" className="inline-flex justify-center items-center bg-brand-orange hover:bg-orange-600 text-white px-8 py-4 rounded-full font-bold text-base transition shadow-lg shadow-orange-900/30">
                                    Clean Out My Unit Now
                                    <ArrowRight className="ml-2 w-5 h-5" />
                                </Link>
                                <a href="tel:8327936566" className="inline-flex justify-center items-center px-8 py-4 rounded-full border-2 border-slate-600 hover:border-white text-white font-semibold transition group">
                                    <Phone className="mr-2 group-hover:text-brand-orange transition-colors w-5 h-5" />
                                    (832) 793-6566
                                </a>
                            </div>
                            <div className="mt-8 flex items-center gap-6 text-sm text-slate-400 font-medium">
                                <span className="flex items-center gap-1"><Check className="text-brand-orange w-5 h-5" /> Upfront Pricing</span>
                                <span className="flex items-center gap-1"><Check className="text-brand-orange w-5 h-5" /> Fully Insured</span>
                            </div>
                        </div>
                        <div className="relative lg:h-full flex items-center justify-center">
                            <div className="relative rounded-2xl overflow-hidden shadow-2xl border-4 border-slate-800 transform rotate-2 hover:rotate-0 transition duration-500">
                                <img
                                    alt="Workers clearing out a storage unit"
                                    className="w-full h-auto object-cover max-h-[600px]"
                                    src="https://lh3.googleusercontent.com/aida-public/AB6AXuB6lxdcGh7A9sZV80mobXiptdbgFMjdSGmWRyor93xSgskaYIRMoHypaBCES1PkDqb2mPFyOgNuaaYWtCbRyqXXj9TjMUIVU_EnvD08YJNY-_WdBKzzwwWWJjiZ25ez3yUMzSfv4v28ZMupUY94ku14alB7owblmFfv8VlnJWe6MosaIqzyFlDjzrZj39ydjO-0iYQLqQNOVx70khyp0-c_s96ZZ8ZoXOTlBIaKp7WC5mdTt3_G6ihZx_50yCCdzlt-tvkCQlZ_V-o"
                                />
                                <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 to-transparent p-6">
                                    <p className="text-white font-bold text-lg">Quick & Efficient Cleanouts</p>
                                    <p className="text-slate-300 text-sm">We sweep it clean so you get your deposit back.</p>
                                </div>
                            </div>
                            <div className="absolute -z-10 top-10 -right-10 w-64 h-64 bg-brand-orange/20 rounded-full blur-3xl"></div>
                        </div>
                    </div>
                </div>
            </header>

            {/* Process Section */}
            <section className="py-20 bg-white">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="text-center max-w-3xl mx-auto mb-16">
                        <h2 className="text-3xl md:text-4xl font-bold text-slate-900 mb-4">SIMPLE 3-STEP PROCESS</h2>
                        <p className="text-slate-500 text-lg">No stress, no mess. Here is how we get the job done efficiently.</p>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-12 text-center">
                        {[
                            { icon: Calendar, title: "Book Online", desc: "Schedule a no-obligation onsite estimate in seconds. Tell us your unit number and facility location." },
                            { icon: Truck, title: "We Load It", desc: "Our friendly, uniformed team arrives at the facility and does all the heavy lifting directly from your unit." },
                            { icon: Check, title: "It's Gone!", desc: "We haul it away to be responsibly disposed of and recycled. You stop paying storage fees immediately." }
                        ].map((step, i) => (
                            <div key={i} className="group p-6 rounded-2xl hover:bg-slate-50 transition duration-300">
                                <div className="w-20 h-20 mx-auto bg-orange-100 rounded-2xl flex items-center justify-center mb-6 text-brand-orange group-hover:scale-110 transition duration-300">
                                    <step.icon className="w-10 h-10" />
                                </div>
                                <h3 className="text-xl font-bold text-slate-900 mb-3">{step.title}</h3>
                                <p className="text-slate-500 leading-relaxed">{step.desc}</p>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* Specialized Services */}
            <section className="py-20 bg-slate-50">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="text-center mb-16">
                        <h2 className="text-3xl md:text-4xl font-bold text-slate-900 mb-4">SPECIALIZED STORAGE SERVICES</h2>
                        <Link href="/items-we-take" className="inline-flex items-center text-brand-orange font-semibold hover:text-orange-600 transition">
                            View full item list <ArrowRight className="ml-1 w-4 h-4" />
                        </Link>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
                        {[
                            { icon: Key, title: "Lost Key Services", desc: "Lost the key to your padlock? We have bolt cutters and tools to access your unit authorized by you, ensuring the cleanout happens without delay." },
                            { icon: Warehouse, title: "Direct Facility Pickup", desc: "We coordinate directly with storage facility managers if you can't be there, making remote cleanouts seamless and stress-free." },
                            { icon: DollarSign, title: "Transparent Volume Pricing", desc: "You only pay for the amount of junk we remove. Our volume-based pricing ensures you get a fair deal whether it's a 5x5 or 10x30 unit." },
                            { icon: Sparkles, title: "Sweep-Clean Guarantee", desc: "We don't just take the big stuff. We sweep the floor clean so you can confidently turn the unit back over to the facility manager." },
                            { icon: Recycle, title: "Donation & Recycling", desc: "Found some hidden gems? We sort through items to donate usable goods and recycle electronics, keeping them out of landfills." },
                            { icon: Gavel, title: "Auction Cleanouts", desc: "Did you buy a unit at auction? We help auction winners clear out unwanted debris quickly so they can profit from their find." }
                        ].map((item, i) => (
                            <div key={i} className="bg-white p-8 rounded-xl shadow-sm border border-slate-100 hover:shadow-md transition">
                                <div className="w-12 h-12 bg-orange-100 text-brand-orange rounded-lg flex items-center justify-center mb-6">
                                    <item.icon className="w-6 h-6" />
                                </div>
                                <h3 className="text-xl font-bold text-slate-900 mb-3">{item.title}</h3>
                                <p className="text-slate-500 text-sm leading-relaxed">{item.desc}</p>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* Trust Badges */}
            <section className="py-16 bg-white border-t border-slate-100">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
                        {[
                            { icon: CreditCard, title: "Upfront Pricing", sub: "No hidden fees. Firm quote." },
                            { icon: Clock, title: "Fast Service", sub: "Same-day/Next-day available." },
                            { icon: ShieldCheck, title: "Fully Insured", sub: "Your property is protected." },
                            { icon: Globe, title: "Eco-Friendly", sub: "We recycle up to 60%." }
                        ].map((item, i) => (
                            <div key={i} className="flex flex-col items-center text-center">
                                <div className="w-16 h-16 rounded-full bg-brand-navy flex items-center justify-center mb-4 shadow-lg">
                                    <item.icon className="text-white w-8 h-8" />
                                </div>
                                <h4 className="text-lg font-bold text-slate-900">{item.title}</h4>
                                <p className="text-xs text-slate-500 mt-1">{item.sub}</p>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* Testimonials */}
            <section className="py-20 bg-brand-navy text-white">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="text-center mb-16">
                        <h2 className="text-3xl md:text-4xl font-bold mb-4">WHAT OUR NEIGHBORS SAY</h2>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                        {[
                            { quote: "I was paying $150 a month for a unit full of old furniture I didn't want. Clean Sweep cleared it out in under an hour. Best decision ever.", author: "Sarah Jenkins", role: "Homeowner" },
                            { quote: "As a storage facility manager, I need units cleared quickly when tenants default. Clean Sweep is my go-to. Reliable, fast, and they sweep up!", author: "Mike Ross", role: "Facility Manager" },
                            { quote: "I lost the key to my unit and lived in another state. They handled the lock cutting and sent me photos of the empty unit. Incredible service.", author: "Emily Chen", role: "Remote Customer" }
                        ].map((story, i) => (
                            <div key={i} className="bg-slate-800 p-8 rounded-xl border border-slate-700 hover:border-brand-orange transition duration-300">
                                <div className="flex text-brand-orange mb-4">
                                    {[...Array(5)].map((_, j) => <span key={j} className="text-sm">★</span>)}
                                </div>
                                <p className="text-slate-300 text-sm italic mb-6 leading-relaxed">"{story.quote}"</p>
                                <div>
                                    <p className="font-bold text-white text-sm">{story.author}</p>
                                    <p className="text-slate-500 text-xs">{story.role}</p>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            <Footer />
        </div>
    );
}
