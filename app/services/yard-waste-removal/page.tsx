import { Navbar } from "@/components/Navbar";
import { Footer } from "@/components/Footer";
import {
    Calendar,
    Phone,
    ArrowRight,
    Check,
    Trees,
    Leaf,
    Trash2,
    Shovel,
    Truck,
    Wind,
    ShieldCheck,
    Recycle,
    Star
} from "lucide-react";
import Link from "next/link";
import { Metadata } from "next";

export const metadata: Metadata = {
    title: "Yard Waste & Storm Debris Removal in Houston | CleanSweep",
    description: "Fast yard waste removal and storm cleanup in Houston. We haul branches, leaves, old fencing, and debris. Same-day service available. Get a quote.",
};

export default function YardWasteRemovalPage() {
    return (
        <div className="min-h-screen bg-slate-50">
            <Navbar />

            {/* Hero Section */}
            <header className="relative bg-brand-navy overflow-hidden py-20 lg:py-32 pt-36">
                <div className="absolute inset-0 z-0 opacity-20 bg-[url('https://images.unsplash.com/photo-1592478411213-61535fdd28b6?q=80&w=2070&auto=format&fit=crop')] bg-cover bg-center"></div>
                <div className="absolute inset-0 z-0 bg-gradient-to-r from-brand-navy via-brand-navy/95 to-brand-navy/80"></div>
                <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col lg:flex-row items-center gap-12">
                    <div className="lg:w-1/2 space-y-6">
                        <div className="inline-flex items-center px-3 py-1 rounded-full bg-slate-800 text-xs font-semibold uppercase tracking-wider text-brand-orange border border-slate-700">
                            Available For Same-Day Pickup
                        </div>
                        <h1 className="text-4xl tracking-tight font-extrabold text-white sm:text-5xl md:text-6xl leading-tight">
                            Yard Waste & <br />
                            <span className="text-brand-orange">Storm Debris Cleanup</span>
                        </h1>
                        <p className="text-lg text-slate-300 max-w-xl leading-relaxed">
                            Don't let yard trimmings and storm wreckage ruin your curb appeal. We handle the heavy lifting, hauling, and eco-friendly disposal of all your yard waste so you can enjoy your outdoor space again.
                        </p>
                        <div className="flex flex-col sm:flex-row gap-4 pt-4">
                            <Link href="/get-started" className="bg-brand-orange hover:bg-orange-600 text-white font-bold py-4 px-8 rounded-full transition-all shadow-lg hover:shadow-orange-500/30 text-center flex items-center justify-center gap-2 group">
                                Get a Yard Cleanup Quote <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                            </Link>
                            <a href="tel:8327936566" className="border-2 border-slate-600 hover:border-white text-white font-semibold py-4 px-8 rounded-full transition-all text-center flex items-center justify-center gap-2">
                                <Phone className="w-5 h-5" /> (832) 793-6566
                            </a>
                        </div>
                        <div className="flex flex-wrap items-center gap-6 text-sm text-slate-400 pt-2 font-medium">
                            <span className="flex items-center gap-1"><Check className="text-brand-orange w-5 h-5" /> Upfront Pricing</span>
                            <span className="flex items-center gap-1"><Check className="text-brand-orange w-5 h-5" /> Fully Insured</span>
                            <span className="flex items-center gap-1"><Check className="text-brand-orange w-5 h-5" /> Eco-Friendly Disposal</span>
                        </div>
                    </div>
                    <div className="lg:w-1/2 relative lg:h-[500px]">
                        <img
                            alt="Professional team cleaning up yard waste and loading a truck"
                            className="rounded-2xl shadow-2xl border-4 border-slate-800 w-full h-full object-cover transform hover:scale-105 transition-transform duration-700"
                            src="https://lh3.googleusercontent.com/aida-public/AB6AXuDGPR69RR5d1hwgIXr6Do7n-UnjsESigbHdYAlBgAkcsZfpjyQ6uufZP344dGtmKlnrINtlOup5rGz9XFDVm0fZfCQsfqO4r9LzxylHXdQJbwf75yjmcm5pN09dy4N4npLXlWHf6FZ4jJmdJCDjZ-r6N_XagdFV8Ga_SwfkFpEYQiFla5Mh3Dk45RTV5pzSeaRqNhcDTHXC0T5A4pLRtvbw7kKL1LM2tM0G8dZaPV5731yPifCVtSnM_UkFNBZ86sJs7Lr3XVWFugw"
                        />
                    </div>
                </div>
            </header>

            {/* Storm Cleanup Banner */}
            <section className="bg-orange-50 border-b border-orange-100">
                <div className="max-w-7xl mx-auto py-12 px-4 sm:px-6 lg:px-8">
                    <div className="lg:grid lg:grid-cols-3 lg:gap-8 items-center">
                        <div className="lg:col-span-2">
                            <div className="flex items-center mb-4">
                                <Wind className="text-brand-orange w-10 h-10 mr-3" />
                                <h2 className="text-3xl font-extrabold text-slate-900">
                                    Houston Storm Cleanup Services
                                </h2>
                            </div>
                            <p className="mt-3 text-lg text-slate-600">
                                Severe weather hits hard. When the storm clears, we are ready to help. We provide rapid response for fallen branches, scattered debris, and bag pickup after major weather events. Don't wait for the city schedule.
                            </p>
                        </div>
                        <div className="mt-8 lg:mt-0 flex flex-col gap-3">
                            {[
                                { icon: Trees, text: "Fallen Branch Removal" },
                                { icon: Trash2, text: "Debris Bag Pickup" },
                                { icon: Shovel, text: "Fence & Structure Disposal" }
                            ].map((item, i) => (
                                <div key={i} className="flex items-start gap-3">
                                    <div className="flex-shrink-0 h-8 w-8 rounded-full bg-orange-100 flex items-center justify-center">
                                        <item.icon className="text-brand-orange w-5 h-5" />
                                    </div>
                                    <span className="text-slate-700 font-medium">{item.text}</span>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </section>

            {/* Process */}
            <section className="py-20 bg-white">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="text-center mb-16">
                        <h2 className="text-3xl font-extrabold text-slate-900 sm:text-4xl mb-4">
                            SIMPLE 3-STEP PROCESS
                        </h2>
                        <p className="max-w-2xl mx-auto text-lg text-slate-500">
                            No stress, no mess. Here is how we get your yard clean efficiently.
                        </p>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-12 relative">
                        <div className="hidden md:block absolute top-12 left-0 w-full h-0.5 bg-slate-100 -z-10"></div>
                        {[
                            { icon: Calendar, title: "1. Book Online", desc: "Schedule a no-obligation onsite estimate in seconds. Just tell us when to show up." },
                            { icon: Truck, title: "2. We Load It", desc: "Our friendly, uniformed team arrives and does the heavy lifting, clearing branches and bags." },
                            { icon: Check, title: "3. It's Gone!", desc: "We haul it away to be composted or responsibly disposed of. You enjoy your clean yard." }
                        ].map((step, i) => (
                            <div key={i} className="flex flex-col items-center text-center bg-white p-4">
                                <div className="mx-auto h-24 w-24 rounded-2xl bg-orange-50 flex items-center justify-center mb-6 shadow-lg rotate-3">
                                    <step.icon className="text-brand-orange w-10 h-10 -rotate-3" />
                                </div>
                                <h3 className="text-xl font-bold text-slate-900 mb-3">{step.title}</h3>
                                <p className="text-slate-500 text-sm px-4 leading-relaxed">{step.desc}</p>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* Items We Take */}
            <section className="bg-slate-50 py-20 border-t border-slate-200">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="text-center mb-16">
                        <h2 className="text-3xl font-extrabold text-slate-900 sm:text-4xl">WHAT WE TAKE</h2>
                        <Link href="/items-we-take" className="mt-4 inline-flex items-center text-brand-orange font-bold hover:text-orange-700 transition-colors gap-1">
                            View full item list <ArrowRight className="w-4 h-4" />
                        </Link>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
                        {[
                            { icon: Trees, title: "Branches & Limbs", desc: "Tree trimmings, large branches, and fallen limbs from storms." },
                            { icon: Leaf, title: "Leaves & Clippings", desc: "Bagged leaves, grass clippings, and hedge trimmings." },
                            { icon: Shovel, title: "Sod & Soil", desc: "Old sod, dirt piles, and landscaping removal debris." },
                            { icon: Shovel, title: "Fencing & Decking", desc: "Old wooden fences, rotten deck boards, and posts." }, // Reuse shovel/fence icon logic
                            { icon: Recycle, title: "Compost Material", desc: "Organic garden waste suitable for composting facilities." },
                            { icon: Trash2, title: "Sheds & Structures", desc: "Demolition and removal of small garden sheds and play structures." }
                        ].map((item, i) => (
                            <div key={i} className="bg-white rounded-xl shadow-sm border border-slate-100 p-8 text-center hover:shadow-md transition-shadow group">
                                <div className="mx-auto h-16 w-16 rounded-full bg-orange-50 flex items-center justify-center mb-6 group-hover:bg-brand-orange group-hover:text-white transition-colors text-brand-orange">
                                    <item.icon className="w-8 h-8" />
                                </div>
                                <h3 className="text-xl font-bold text-slate-900 mb-2">{item.title}</h3>
                                <p className="text-sm text-slate-500">{item.desc}</p>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* Trust Badges */}
            <section className="py-12 bg-white border-y border-slate-100">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
                        {[
                            { icon: Check, title: "Upfront Pricing", sub: "No hidden fees." },
                            { icon: Calendar, title: "Fast Service", sub: "Same-day/Next-day." },
                            { icon: ShieldCheck, title: "Fully Insured", sub: "Property protected." },
                            { icon: Recycle, title: "Eco-Friendly", sub: "We recycle up to 60%." } // Recycle stat?
                        ].map((item, i) => (
                            <div key={i} className="flex flex-col items-center">
                                <div className="w-12 h-12 bg-slate-900 rounded-full flex items-center justify-center mb-3 text-white">
                                    <item.icon className="w-6 h-6" />
                                </div>
                                <h4 className="font-bold text-slate-900">{item.title}</h4>
                                <p className="text-xs text-slate-500">{item.sub}</p>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* Testimonials */}
            <section className="bg-brand-navy py-16 sm:py-24 text-white relative">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
                    <h2 className="text-3xl font-extrabold text-center mb-16 uppercase tracking-wider">What Our Neighbors Say</h2>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                        {[
                            { quote: "After the hurricane, my backyard was a disaster zone. CleanSweep came out the next day and cleared two massive piles of branches in under an hour. Incredible service.", author: "Mark Thompson", role: "Homeowner" },
                            { quote: "I had an old wooden fence that needed to go. They dismantled it and hauled it away. The yard looks bigger and cleaner than it has in years. Highly recommend!", author: "Jessica Alvez", role: "Small Business Owner" },
                            { quote: "Best price I found for simple bag pickup. I had about 40 bags of leaves and they took them all without complaint. Friendly crew.", author: "David Chen", role: "Homeowner" }
                        ].map((t, i) => (
                            <div key={i} className="bg-slate-800/50 p-8 rounded-xl border border-slate-700 backdrop-blur-sm">
                                <div className="flex text-brand-orange mb-4 gap-1">
                                    {[...Array(5)].map((_, j) => <Star key={j} className="w-4 h-4 fill-current" />)}
                                </div>
                                <p className="italic text-slate-300 text-sm mb-6 leading-relaxed">"{t.quote}"</p>
                                <div>
                                    <p className="font-bold text-white text-sm">{t.author}</p>
                                    <p className="text-xs text-slate-500">{t.role}</p>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* CTA */}
            <div className="bg-brand-orange py-16 px-4 text-center">
                <div className="max-w-4xl mx-auto">
                    <h2 className="text-3xl md:text-4xl font-extrabold text-white mb-6">Ready to clear the clutter?</h2>
                    <p className="text-white/90 text-lg mb-8">Schedule your yard waste removal today and reclaim your outdoor space.</p>
                    <div className="flex flex-col sm:flex-row justify-center gap-4">
                        <Link href="/get-started" className="bg-white text-brand-orange hover:bg-slate-100 font-bold py-4 px-10 rounded-full transition shadow-lg text-lg flex items-center justify-center gap-2">
                            <Calendar className="w-5 h-5" /> Book Now
                        </Link>
                        <a href="tel:8327936566" className="bg-transparent border-2 border-white hover:bg-white/10 text-white font-bold py-4 px-10 rounded-full transition text-lg flex items-center justify-center gap-2">
                            <Phone className="w-5 h-5" /> Contact Us
                        </a>
                    </div>
                </div>
            </div>

            <Footer />
        </div>
    );
}
