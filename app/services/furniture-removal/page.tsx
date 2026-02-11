import { Navbar } from "@/components/Navbar";
import { Footer } from "@/components/Footer";
import {
    Calendar,
    Phone,
    ArrowRight,
    Check,
    Recycle,
    Sofa,
    Bed,
    Table2,
    Armchair,
    Monitor,
    Truck,
    Clock,
    Box
} from "lucide-react";
import Link from "next/link";
import { Metadata } from "next";

export const metadata: Metadata = {
    title: "Furniture Removal in Houston | Same-Day Pickup | CleanSweep",
    description: "Don't lift a finger. We provide fast, professional furniture removal and donation services in Houston. Sofas, mattresses, tables, and more. Call today.",
};

export default function FurnitureRemovalPage() {
    return (
        <div className="min-h-screen bg-slate-50">
            <Navbar />

            {/* Hero Section */}
            <header className="relative bg-brand-navy overflow-hidden py-20 lg:py-32 pt-36">
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,_var(--tw-gradient-stops))] from-slate-800 to-brand-navy opacity-50"></div>
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
                    <div className="grid lg:grid-cols-2 gap-12 items-center">
                        <div className="space-y-8">
                            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-slate-800 border border-slate-700 text-xs font-semibold text-brand-orange uppercase tracking-wide">
                                <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
                                Available for same-day pickup
                            </div>
                            <h1 className="text-5xl lg:text-7xl font-extrabold text-white leading-tight tracking-tight">
                                FURNITURE <br />
                                <span className="text-brand-orange">REMOVAL</span> & DONATION
                            </h1>
                            <p className="text-lg text-slate-300 max-w-xl leading-relaxed">
                                Don't break your back trying to move that old couch. We handle the heavy lifting for sofa removal, mattress disposal, and full estate cleanouts.
                            </p>
                            <div className="flex flex-col sm:flex-row gap-4 pt-4">
                                <Link href="/get-started" className="bg-brand-orange hover:bg-orange-600 text-white px-8 py-4 rounded-full font-bold text-lg transition-all shadow-xl shadow-orange-900/20 flex items-center justify-center gap-2 group">
                                    Get a Furniture Quote
                                    <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                                </Link>
                                <a href="tel:8327936566" className="bg-transparent border-2 border-slate-500 hover:border-white text-white px-8 py-4 rounded-full font-bold text-lg transition-all flex items-center justify-center gap-2">
                                    <Phone className="w-5 h-5" />
                                    (832) 793-6566
                                </a>
                            </div>
                            <div className="flex flex-col sm:flex-row gap-6 text-sm text-slate-400 font-medium pt-2">
                                <span className="flex items-center gap-1"><Check className="text-brand-orange w-5 h-5" /> Upfront Pricing</span>
                                <span className="flex items-center gap-1"><Check className="text-brand-orange w-5 h-5" /> Fully Insured</span>
                                <span className="flex items-center gap-1"><Check className="text-brand-orange w-5 h-5" /> Donation Receipts Provided</span>
                            </div>
                        </div>
                        <div className="relative">
                            <div className="absolute -inset-4 bg-brand-orange/20 rounded-3xl blur-2xl"></div>
                            <img
                                alt="CleanSweep team loading a sofa into a truck"
                                className="relative rounded-2xl shadow-2xl border-4 border-white/10 w-full object-cover aspect-[4/3] transform hover:scale-[1.01] transition-transform duration-500"
                                src="https://lh3.googleusercontent.com/aida-public/AB6AXuC-PNnWEGKa3n6hufD7DkWviNwAzz9bqvSVApT-DsrxF_jdCnSbp0pS8SrDbje2MO5_vsR9KBaDyLttjJtpU12CYmFy5avpdm5zZOWTOL12rzNq7DrtcAIJp-2HqrTukbrQ5803im2b-PyNrRAwDQE7fNOqmzX1wr2aAgb3zQAmuVdFlx5Q1isEONzWTelBTaZUFDLMrpBjeZqcTJAghA1vYBV9G-8vxfpJ9n3QQv4k-HGY53ZSwv8RiqJMeHCpe8x3brnpKNX_24k"
                            />
                            <div className="absolute -bottom-6 -left-6 bg-white p-4 rounded-xl shadow-xl border border-slate-100 flex items-center gap-4 max-w-xs hidden md:flex">
                                <div className="w-12 h-12 rounded-full bg-green-100 flex items-center justify-center text-green-600">
                                    <Recycle className="w-6 h-6" />
                                </div>
                                <div>
                                    <p className="font-bold text-sm text-slate-900">Eco-Friendly Disposal</p>
                                    <p className="text-xs text-slate-500">We donate & recycle first.</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </header>

            {/* Furniture Items */}
            <section className="py-20 bg-white">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="text-center max-w-3xl mx-auto mb-16">
                        <h2 className="text-3xl md:text-4xl font-bold mb-4 text-slate-900">Furniture We Remove</h2>
                        <p className="text-slate-600 text-lg mb-4">Whether it's a single recliner or a whole house of furniture, our team is ready to help.</p>
                        <p className="text-slate-500 text-sm bg-blue-50 inline-block px-4 py-2 rounded-lg border border-blue-100">
                            Have a whole house of furniture? Check out our <Link href="/services/estate-cleanout" className="text-brand-orange font-bold hover:underline">Estate Cleanout service</Link>.
                        </p>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {[
                            { icon: Sofa, title: "Sofas & Sectionals", desc: "Large sectionals, sleeper sofas, loveseats, and heavy couches. We disassemble if needed." },
                            { icon: Bed, title: "Mattresses & Beds", desc: "King, Queen, Twin mattresses, box springs, bed frames, and headboards." },
                            { icon: Table2, title: "Tables & Dining Sets", desc: "Dining tables, coffee tables, end tables, and heavy oak or glass furniture." },
                            { icon: Monitor, title: "Desks & Office", desc: "Heavy wooden desks, filing cabinets, office chairs, and cubicle partitions." },
                            { icon: Box, title: "Bookcases & Dressers", desc: "Wardrobes, armoires, tall bookcases, chest of drawers, and vanity units." }, // Used Recycle icon as placeholder, or could use generic Box
                            { icon: Armchair, title: "Patio Furniture", desc: "Outdoor lounge sets, rusty metal chairs, heavy grills, and patio tables." }
                        ].map((item, i) => (
                            <div key={i} className="group bg-slate-50 border border-slate-100 rounded-2xl p-8 hover:shadow-xl transition-all duration-300">
                                <div className="w-14 h-14 rounded-xl bg-orange-100 text-brand-orange flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
                                    <item.icon className="w-8 h-8" />
                                </div>
                                <h3 className="text-xl font-bold mb-2 text-slate-900">{item.title}</h3>
                                <p className="text-slate-600 text-sm leading-relaxed">{item.desc}</p>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* Donation Focus */}
            <section className="bg-slate-50 py-20 border-y border-slate-200">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col md:flex-row items-center gap-12">
                    <div className="w-full md:w-1/2">
                        <div className="relative">
                            <div className="absolute -top-4 -left-4 w-24 h-24 bg-brand-orange/20 rounded-full blur-xl"></div>
                            <img
                                alt="Donating furniture to charity"
                                className="relative rounded-2xl shadow-xl w-full object-cover h-[400px]"
                                src="https://lh3.googleusercontent.com/aida-public/AB6AXuCJI4D3fji_t72UYzuNzRp5yXd0RRM_JHZkPD_NJ92d8ZnAp7C7W6xNLbaVSsO6M7RUAkvawASxxZXvb-aYDxOcVS5fJzpe_ULeAibUZxnX9Y_Z77aQ2ET-a6asiR74kE-yVJ_AocXfuOE-RA0HLg__1vp7uNP34xADBOAyDEOP1enj1jeuwa4BBec0SGZ5SoGJugvvM1FEOX2JXR7IOtnJPoon1MXIoH77RPt58CtM4bAZQQPJQKaj5X0pbJ5Ke0_CNbeC8fTmu1g"
                            />
                            <div className="absolute bottom-6 right-6 bg-white p-4 rounded-lg shadow-lg max-w-[200px]">
                                <p className="text-brand-orange font-bold text-lg mb-1">Tax Deductible</p>
                                <p className="text-xs text-slate-500">We provide donation receipts for all eligible items.</p>
                            </div>
                        </div>
                    </div>
                    <div className="w-full md:w-1/2 space-y-6">
                        <div className="inline-block text-brand-orange font-bold tracking-wider text-sm uppercase">Community Focused</div>
                        <h2 className="text-3xl md:text-4xl font-bold text-slate-900">The "Donation First" Approach</h2>
                        <p className="text-slate-600 text-lg leading-relaxed">
                            We hate landfills as much as you do. That's why CleanSweep prioritizes donating your usable furniture to local charities like Habitat for Humanity, Goodwill, and local shelters.
                        </p>
                        <ul className="space-y-4 pt-4">
                            <li className="flex items-start gap-3">
                                <Check className="text-green-500 mt-1 w-5 h-5" />
                                <div>
                                    <h4 className="font-bold text-slate-900">Supporting Local Families</h4>
                                    <p className="text-sm text-slate-500">Your old sofa could be a fresh start for a family in need.</p>
                                </div>
                            </li>
                            <li className="flex items-start gap-3">
                                <Check className="text-green-500 mt-1 w-5 h-5" />
                                <div>
                                    <h4 className="font-bold text-slate-900">Environmental Impact</h4>
                                    <p className="text-sm text-slate-500">Keeping bulky items out of the landfill reduces waste significantly.</p>
                                </div>
                            </li>
                        </ul>
                    </div>
                </div>
            </section>

            {/* Process */}
            <section className="py-20 bg-white">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="text-center mb-16">
                        <h2 className="text-3xl font-bold text-slate-900">Simple 3-Step Process</h2>
                        <p className="text-slate-500 mt-2">No stress, no mess. Here is how we get the job done efficiently.</p>
                    </div>
                    <div className="grid md:grid-cols-3 gap-12 text-center relative">
                        <div className="hidden md:block absolute top-12 left-[16%] right-[16%] h-0.5 bg-slate-200 -z-10"></div>
                        {[
                            { icon: Calendar, title: "1. Book Online", desc: "Schedule a no-obligation onsite estimate in seconds via our website or phone." },
                            { icon: Truck, title: "2. We Load It", desc: "Our friendly, uniformed team arrives and does all the heavy lifting from anywhere in your home." },
                            { icon: Check, title: "3. It's Gone!", desc: "We haul it away to be responsibly disposed of, donated, or recycled." }
                        ].map((step, i) => (
                            <div key={i} className="flex flex-col items-center">
                                <div className="w-24 h-24 bg-orange-50 rounded-2xl flex items-center justify-center text-brand-orange mb-6 shadow-sm">
                                    <step.icon className="w-10 h-10" />
                                </div>
                                <h3 className="text-xl font-bold mb-3 text-slate-900">{step.title}</h3>
                                <p className="text-slate-500 text-sm max-w-xs mx-auto">{step.desc}</p>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* Testimonials */}
            <section className="bg-brand-navy py-20 px-6 text-center text-white">
                <div className="max-w-7xl mx-auto">
                    <h2 className="text-3xl font-bold mb-12">WHAT OUR NEIGHBORS SAY</h2>
                    <div className="grid md:grid-cols-3 gap-6">
                        {[
                            { quote: "They removed a massive sectional from my 3rd-floor apartment without scratching a single wall. The price was exactly what they quoted upfront.", author: "Marcus Johnson", role: "Apartment Resident" },
                            { quote: "I love that they donate! knowing my grandma's old dining set went to a shelter instead of a dump made the whole process feel so much better.", author: "Sarah P.", role: "Homeowner" },
                            { quote: "Fast, efficient, and polite. Called them at 9am and the old mattresses were gone by noon. Highly recommend CleanSweep.", author: "David Chen", role: "Small Business Owner" }
                        ].map((story, i) => (
                            <div key={i} className="bg-slate-800 border border-slate-700 p-8 rounded-xl text-left hover:border-slate-600 transition-colors">
                                <div className="flex gap-1 text-brand-orange mb-4">
                                    {[...Array(5)].map((_, j) => <span key={j} className="text-sm">★</span>)}
                                </div>
                                <p className="text-slate-300 italic mb-6 text-sm leading-relaxed">"{story.quote}"</p>
                                <div>
                                    <p className="text-white font-bold text-sm">{story.author}</p>
                                    <p className="text-slate-500 text-xs">{story.role}</p>
                                </div>
                            </div>
                        ))}
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
