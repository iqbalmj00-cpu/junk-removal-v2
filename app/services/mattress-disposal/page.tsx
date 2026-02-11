import { Navbar } from "@/components/Navbar";
import { Footer } from "@/components/Footer";
import {
    Calendar,
    Phone,
    ArrowRight,
    Check,
    Recycle,
    Trash2,
    Truck,
    ShieldCheck,
    Bed,
    HelpCircle,
    Clock
} from "lucide-react";
import Link from "next/link";
import { Metadata } from "next";

export const metadata: Metadata = {
    title: "Mattress Disposal & Recycling in Houston | Eco-Friendly | CleanSweep",
    description: "Need to get rid of an old mattress? We provide fast, eco-friendly mattress disposal and recycling in Houston. We do the heavy lifting. Book online.",
};

export default function MattressDisposalPage() {
    return (
        <div className="min-h-screen bg-slate-50">
            <Navbar />

            {/* Hero Section */}
            <header className="relative bg-brand-navy overflow-hidden py-20 lg:py-32 pt-36">
                <div className="absolute inset-0 bg-[url('/images/services/mattress-disposal.png')] bg-cover bg-center opacity-10 mix-blend-overlay"></div>
                <div className="absolute inset-0 bg-gradient-to-r from-brand-navy via-brand-navy/95 to-brand-navy/80"></div>
                <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
                        <div className="space-y-8">
                            <div className="inline-flex items-center px-4 py-1.5 rounded-full bg-slate-800 text-brand-orange text-xs font-bold tracking-wide uppercase border border-slate-700">
                                Eco-Friendly Disposal
                            </div>
                            <h1 className="text-5xl lg:text-7xl font-extrabold text-white tracking-tight leading-tight">
                                Professional <br />
                                <span className="text-brand-orange">Mattress Disposal</span>
                            </h1>
                            <p className="text-lg text-slate-300 max-w-xl leading-relaxed">
                                Don't struggle with that heavy, awkward mattress alone. Our uniformed pros will remove it from any room, wrap it for safe transport, and ensure it's recycled responsibly. No lifting required.
                            </p>
                            <div className="flex flex-col sm:flex-row gap-4 pt-4">
                                <Link href="/get-started" className="bg-brand-orange hover:bg-orange-600 text-white px-8 py-4 rounded-full font-bold text-lg transition-all shadow-xl shadow-orange-900/30 flex justify-center items-center gap-2 group">
                                    Schedule Pickup
                                    <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                                </Link>
                                <a href="tel:8327936566" className="bg-transparent border-2 border-slate-500 hover:border-white text-white px-8 py-4 rounded-full font-bold text-lg transition-all flex justify-center items-center gap-2">
                                    <Phone className="w-5 h-5" />
                                    (832) 793-6566
                                </a>
                            </div>
                            <div className="flex items-center gap-6 text-sm text-slate-400 font-medium pt-4">
                                <span className="flex items-center gap-1"><Check className="text-brand-orange w-5 h-5" /> Upfront Pricing</span>
                                <span className="flex items-center gap-1"><Check className="text-brand-orange w-5 h-5" /> Fully Insured</span>
                            </div>
                        </div>
                        <div className="relative lg:h-[500px] rounded-2xl overflow-hidden shadow-2xl border-4 border-slate-800 group">
                            <div className="absolute inset-0 bg-gradient-to-t from-brand-navy/60 to-transparent z-10"></div>
                            <img
                                alt="Workers removing a mattress"
                                className="w-full h-full object-cover transform group-hover:scale-105 transition-transform duration-700"
                                src="https://lh3.googleusercontent.com/aida-public/AB6AXuDD6UMGgnDJZkTim7ySCdN9FvilnMTwbzdKPwh4ds2TliGAraT9MHCgsNxxJB5LEINgDvv60n2uOeEK-ckHUcsrhV-e8mRZFOwU_Ocj2Do-HOZ5VqbJF1ejPWfs7nUgk6kgNB4bnRZt_PBnWteLL5kGyH9U2W34fiwltHy5QLbglDtlP3IEIYgIxoU74B_fGsFknl389AUF06nE1j-Yk2GrxLqIwwibPn41UkulE3vyFY7aWpebnrlam4sr9S2Dkr989IzMARvCEcA"
                            />
                            <div className="absolute bottom-6 left-6 z-20 bg-slate-900/80 backdrop-blur-md border border-slate-700 p-4 rounded-xl max-w-xs hidden md:block">
                                <p className="text-white font-medium text-sm">"The team handled my king size mattress with ease. Couldn't be happier!"</p>
                                <div className="flex items-center gap-2 mt-2">
                                    <div className="flex text-brand-orange text-xs">
                                        {[...Array(5)].map((_, i) => <span key={i} className="text-sm">★</span>)}
                                    </div>
                                    <span className="text-slate-400 text-xs">- Jessica M.</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </header>

            {/* Why Choose Us */}
            <section className="py-24 bg-white">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="text-center max-w-3xl mx-auto mb-16">
                        <h2 className="text-3xl md:text-4xl font-bold text-slate-900 mb-4">Why Choose CleanSweep for Mattresses?</h2>
                        <p className="text-slate-600 text-lg">Hygiene and proper disposal are our top priorities. We don't just dump your old mattress; we handle it with care from bedroom to recycling center.</p>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-12">
                        {[
                            { icon: ShieldCheck, title: "Hygienic Removal", desc: "For health and safety, we can wrap your mattress in protective plastic before carrying it through your home, ensuring no dust or allergens are spread." },
                            { icon: Truck, title: "We Do The Heavy Lifting", desc: "Stairs, tight corners, or second floors? No problem. Our team is trained to maneuver bulky mattresses safely without damaging your walls or floors." },
                            { icon: Recycle, title: "Eco-Responsible Disposal", desc: "We partner with certified recycling facilities to break down your mattress into steel, foam, and wood, keeping up to 90% of the materials out of landfills." }
                        ].map((item, i) => (
                            <div key={i} className="flex flex-col items-center text-center group">
                                <div className="w-20 h-20 bg-orange-50 rounded-2xl flex items-center justify-center mb-6 transition-colors group-hover:bg-brand-orange group-hover:text-white text-brand-orange">
                                    <item.icon className="w-10 h-10" />
                                </div>
                                <h3 className="text-xl font-bold text-slate-900 mb-3">{item.title}</h3>
                                <p className="text-slate-600 leading-relaxed">{item.desc}</p>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* Types of Mattresses */}
            <section className="py-24 bg-slate-50 border-y border-slate-200">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="text-center mb-16">
                        <h2 className="text-3xl font-bold text-slate-900">We Take All Sizes & Types</h2>
                        <p className="text-slate-500 mt-2">From box springs to memory foam, we haul it all.</p>
                    </div>
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
                        {[
                            { letter: "T", title: "Twin & Twin XL", sub: "Perfect for kids rooms and dorms." },
                            { letter: "F", title: "Full / Double", sub: "Standard guest room size." },
                            { letter: "Q", title: "Queen Size", sub: "Most common master bed size.", popular: true },
                            { letter: "K", title: "King & CA King", sub: "Heavy lifting required? We got it." }
                        ].map((item, i) => (
                            <div key={i} className="bg-white p-8 rounded-2xl shadow-sm hover:shadow-lg transition-all border border-slate-100 flex flex-col items-center text-center relative overflow-hidden group">
                                {item.popular && (
                                    <div className="absolute top-0 right-0 bg-brand-orange text-white text-[10px] px-2 py-1 font-bold rounded-bl-lg">POPULAR</div>
                                )}
                                <div className="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mb-4 text-slate-600 font-bold text-xl group-hover:bg-brand-orange group-hover:text-white transition-colors">
                                    {item.letter}
                                </div>
                                <h3 className="font-bold text-lg text-slate-900">{item.title}</h3>
                                <p className="text-sm text-slate-500 mt-2">{item.sub}</p>
                            </div>
                        ))}
                    </div>
                    <div className="mt-8 text-center">
                        <p className="text-slate-600 text-sm">Also accepting: <span className="font-bold text-slate-800">Box Springs, Bed Frames, Headboards, Futons, and Sofa Beds.</span></p>
                    </div>
                </div>
            </section>

            {/* Eco Impact */}
            <section className="py-24 bg-brand-navy relative overflow-hidden">
                <div className="absolute top-0 right-0 w-96 h-96 bg-brand-orange/10 rounded-full filter blur-3xl -translate-y-1/2 translate-x-1/2"></div>
                <div className="absolute bottom-0 left-0 w-64 h-64 bg-blue-500/10 rounded-full filter blur-3xl translate-y-1/2 -translate-x-1/2"></div>
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
                        <div className="order-2 lg:order-1">
                            <img
                                alt="Recycling facility sorting materials"
                                className="rounded-2xl shadow-2xl border-4 border-slate-800 w-full h-full object-cover"
                                src="https://lh3.googleusercontent.com/aida-public/AB6AXuDQwVQAGm_6qnxAHo7Qie8ggGbRt3Ssykpn08viiZVig23gMXGgmlnoYPqBhk9w9LRMmeeGkLB1nGGC_5kF2vmjB6rlEwFVO89PrWMa5Ft9ykVJRXUhoHkP7li42-EStRaKjbW98Zn0yWFN1to-SpFHklffACTBjwJznQb_YsspfSNvJdZ5IciyO9XSnjo1Wp0AJ2DaGxz5uQBaQMiUTRrSiYYvn4xXJsPBqLfY2dMTprCJW2igz-pXgc6f29EFGVPS2kTqK4ztRzw"
                            />
                        </div>
                        <div className="order-1 lg:order-2">
                            <div className="inline-flex items-center px-3 py-1 rounded-full bg-green-900/50 text-green-400 text-xs font-bold tracking-wide uppercase border border-green-700/50 mb-6 gap-1">
                                <Recycle className="w-4 h-4" /> Sustainable Choice
                            </div>
                            <h2 className="text-3xl md:text-4xl font-bold text-white mb-6">Did you know a mattress takes 80+ years to decompose?</h2>
                            <p className="text-slate-300 text-lg mb-6 leading-relaxed">
                                Mattresses are a nightmare for landfills. They don't compact well and clog machinery. That's why we prioritize recycling.
                            </p>
                            <ul className="space-y-4 mb-8">
                                {[
                                    { title: "Steel Springs", desc: "Melted down and repurposed for new steel products." },
                                    { title: "Polyurethane Foam", desc: "Shredded and turned into carpet padding." },
                                    { title: "Wood Frames", desc: "Chipped into mulch or used for fuel." }
                                ].map((item, i) => (
                                    <li key={i} className="flex items-start">
                                        <Check className="text-brand-orange mr-3 mt-1 w-5 h-5" />
                                        <div>
                                            <h4 className="text-white font-bold">{item.title}</h4>
                                            <p className="text-slate-400 text-sm">{item.desc}</p>
                                        </div>
                                    </li>
                                ))}
                            </ul>
                        </div>
                    </div>
                </div>
            </section>

            {/* FAQ */}
            <section className="py-20 bg-white border-t border-slate-200">
                <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
                    <h2 className="text-3xl font-bold text-slate-900 text-center mb-12">Common Questions</h2>
                    <div className="space-y-4">
                        <div className="bg-slate-50 rounded-xl p-6 border border-slate-100">
                            <h3 className="text-lg font-bold text-slate-900 flex justify-between items-center">
                                Do I need to bring the mattress to the curb?
                            </h3>
                            <p className="text-slate-600 mt-2 text-sm leading-relaxed">
                                No! Our full-service removal includes picking up the mattress from wherever it is in your home. You don't have to lift a finger.
                            </p>
                        </div>
                        <div className="bg-slate-50 rounded-xl p-6 border border-slate-100 opacity-60">
                            <h3 className="text-lg font-bold text-slate-900 flex justify-between items-center">
                                Do you take bed bug infested mattresses?
                            </h3>
                        </div>
                        <div className="bg-slate-50 rounded-xl p-6 border border-slate-100 opacity-60">
                            <h3 className="text-lg font-bold text-slate-900 flex justify-between items-center">
                                Can you take my old bed frame too?
                            </h3>
                        </div>
                    </div>
                </div>
            </section>

            {/* CTA */}
            <section className="bg-brand-orange py-16 px-6 text-center">
                <div className="max-w-4xl mx-auto">
                    <h2 className="text-3xl md:text-4xl font-extrabold text-white mb-6">Ready to Reclaim Your Space?</h2>
                    <p className="text-white/90 text-lg mb-8 max-w-2xl mx-auto">Get a free estimate today. Same-day service available in most areas.</p>
                    <div className="flex flex-col sm:flex-row justify-center gap-4">
                        <Link href="/get-started" className="bg-white text-brand-orange hover:bg-slate-100 px-8 py-4 rounded-full font-bold text-lg shadow-lg transition-colors flex items-center justify-center gap-2">
                            <Calendar className="w-5 h-5" /> Book Online Now
                        </Link>
                        <a href="tel:8327936566" className="bg-transparent border-2 border-white text-white hover:bg-white/10 px-8 py-4 rounded-full font-bold text-lg transition-colors flex items-center justify-center gap-2">
                            <Phone className="w-5 h-5" /> Call (832) 793-6566
                        </a>
                    </div>
                </div>
            </section>

            <Footer />
        </div>
    );
}
