import { Navbar } from "@/components/Navbar";
import { Footer } from "@/components/Footer";
import {
    Check,
    Calendar,
    Phone,
    ArrowRight,
    ShieldCheck,
    Clock,
    Heart,
    Search,
    Recycle,
    Hammer,
    Sparkles,
    Trash2,
    Lock,
    EyeOff
} from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { Metadata } from "next";

export const metadata: Metadata = {
    title: "Hoarder Cleanouts in Houston | Compassionate & Discreet | CleanSweep",
    description: "Overwhelmed by clutter? We provide respectful, non-judgmental hoarder cleanout services in Houston. 100% confidential. Call for a private consultation.",
};

export default function HoarderCleanoutPage() {
    return (
        <div className="min-h-screen bg-slate-50">
            <Navbar />

            {/* Hero Section */}
            <header className="relative bg-brand-navy overflow-hidden py-20 lg:py-32 pt-36">
                <div className="absolute inset-0 opacity-10 bg-[url('https://www.transparenttextures.com/patterns/cubes.png')]"></div>
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
                    <div className="grid lg:grid-cols-2 gap-12 items-center">
                        <div className="space-y-8">
                            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/10 text-xs font-semibold tracking-wide text-brand-orange uppercase border border-white/10">
                                <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
                                Discreet & Confidential Service
                            </div>
                            <h1 className="text-5xl lg:text-6xl font-extrabold text-white leading-tight">
                                Professional & Compassionate <br />
                                <span className="text-brand-orange">Hoarder Cleanouts</span>
                            </h1>
                            <p className="text-lg text-slate-300 max-w-xl leading-relaxed">
                                We provide private, respectful property restoration services. Our empathy-first team helps you reclaim your space without judgment. We handle the heavy lifting, sorting, and cleaning so you can focus on a fresh start.
                            </p>
                            <div className="flex flex-col sm:flex-row gap-4 pt-4">
                                <Link href="/contact" className="bg-brand-orange hover:bg-orange-600 text-white px-8 py-4 rounded-full text-base font-bold transition-all shadow-lg shadow-orange-900/20 text-center flex items-center justify-center gap-2">
                                    Contact for Private Consultation <ArrowRight className="w-5 h-5" />
                                </Link>
                                <a href="tel:8327936566" className="border border-slate-600 hover:border-brand-orange hover:text-brand-orange text-white px-8 py-4 rounded-full text-base font-bold transition-all text-center flex items-center justify-center gap-2">
                                    <Phone className="w-5 h-5" /> (832) 793-6566
                                </a>
                            </div>
                            <div className="flex items-center gap-6 text-sm text-slate-400 pt-4">
                                <span className="flex items-center gap-1"><Check className="text-brand-orange w-5 h-5" /> 100% Confidential</span>
                                <span className="flex items-center gap-1"><Check className="text-brand-orange w-5 h-5" /> Unmarked Trucks Available</span>
                            </div>
                        </div>
                        <div className="relative">
                            <div className="absolute -inset-4 bg-brand-orange/20 blur-2xl rounded-3xl -z-10"></div>
                            <img
                                alt="Compassionate team helping clean a cluttered room"
                                className="rounded-2xl shadow-2xl border-4 border-white/10 object-cover h-[500px] w-full"
                                src="https://lh3.googleusercontent.com/aida-public/AB6AXuB1inQ7YqPPGQdxd7wMRiacEKSguCS04KyO7jQTcFEMuYSSnUVKjdHY8kRn-xffln9C4PaAG4uajG8kpfBQLfrNO7S1M4Fzy4iBzDm_LRUV5UbZSwot5ng0dmCuZ8vKg8qv8VcAh6xL_wYQsAgD-vDCL_r1n_1H4-q87EA-RmAVux3EGZUIqhZVtYzFZe2V6009Wk7HEnuIWDkq5S5dAXQiw2TGA5i2VbnfDrm04aZcClxOvtPwZA7LSnR2s635EZUkrsAExMzmHus"
                            />
                            <div className="absolute -bottom-6 -left-6 bg-white p-4 rounded-xl shadow-xl flex items-center gap-4 max-w-xs border border-slate-100">
                                <div className="bg-green-100 p-2 rounded-full">
                                    <ShieldCheck className="text-green-600 w-6 h-6" />
                                </div>
                                <div>
                                    <p className="font-bold text-slate-900 text-sm">OSHA Certified</p>
                                    <p className="text-xs text-slate-500">Safety & Sanitation Experts</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </header>

            {/* Process Section */}
            <section className="py-20 bg-white">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="text-center max-w-3xl mx-auto mb-16">
                        <h2 className="text-3xl md:text-4xl font-bold text-slate-900 mb-4">A Respectful, 3-Step Process</h2>
                        <p className="text-slate-600">
                            We understand this is more than just junk removal. Our process is designed to be slow, steady, and supportive, ensuring you feel in control every step of the way.
                        </p>
                    </div>
                    <div className="grid md:grid-cols-3 gap-8">
                        <div className="bg-slate-50 p-8 rounded-2xl text-center group hover:shadow-xl transition-all border border-transparent hover:border-brand-orange/20">
                            <div className="w-16 h-16 mx-auto bg-orange-100 rounded-2xl flex items-center justify-center mb-6 text-brand-orange group-hover:scale-110 transition-transform">
                                <Heart className="w-8 h-8" />
                            </div>
                            <h3 className="text-xl font-bold text-slate-900 mb-3">1. Assessment & Listening</h3>
                            <p className="text-slate-600 text-sm leading-relaxed">
                                We start with a free, no-pressure consultation. We listen to your goals and establish a plan that respects your emotional readiness and timeline.
                            </p>
                        </div>
                        <div className="bg-slate-50 p-8 rounded-2xl text-center group hover:shadow-xl transition-all border border-transparent hover:border-brand-orange/20">
                            <div className="w-16 h-16 mx-auto bg-orange-100 rounded-2xl flex items-center justify-center mb-6 text-brand-orange group-hover:scale-110 transition-transform">
                                <Search className="w-8 h-8" />
                            </div>
                            <h3 className="text-xl font-bold text-slate-900 mb-3">2. Collaborative Sorting</h3>
                            <p className="text-slate-600 text-sm leading-relaxed">
                                Our team works <em>with</em> you, not just around you. We help separate items to keep, donate, recycle, or discard, ensuring nothing important is lost.
                            </p>
                        </div>
                        <div className="bg-slate-50 p-8 rounded-2xl text-center group hover:shadow-xl transition-all border border-transparent hover:border-brand-orange/20">
                            <div className="w-16 h-16 mx-auto bg-orange-100 rounded-2xl flex items-center justify-center mb-6 text-brand-orange group-hover:scale-110 transition-transform">
                                <Sparkles className="w-8 h-8" />
                            </div>
                            <h3 className="text-xl font-bold text-slate-900 mb-3">3. Deep Clean & Restore</h3>
                            <p className="text-slate-600 text-sm leading-relaxed">
                                Once cleared, we can provide deep cleaning and sanitation services to restore the safety and livability of the home, giving you a truly fresh start.
                            </p>
                        </div>
                    </div>
                </div>
            </section>

            {/* Services Grid */}
            <section className="py-20 bg-slate-50">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="text-center mb-12">
                        <h2 className="text-3xl md:text-4xl font-bold text-slate-900 mb-4">Comprehensive Restoration Services</h2>
                        <Link href="/services" className="text-brand-orange font-semibold hover:text-orange-600 flex items-center justify-center gap-1 group">
                            View full service list <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                        </Link>
                    </div>
                    <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {[
                            { icon: EyeOff, title: "Discreet Removal", desc: "Privacy is paramount. We offer unmarked vehicles and plain-clothed crews upon request to maintain confidentiality within your neighborhood." },
                            { icon: Heart, title: "Empathy-First Approach", desc: "Our staff is trained in sensitivity and compassion. We understand the attachment to items and proceed with patience and zero judgment.", href: "/services/estate-cleanout" },
                            { icon: Trash2, title: "Biohazard & Sanitation", desc: "We are equipped to handle hazardous materials, pests, mold, and deep grime, ensuring the property is safe for habitation." },
                            { icon: Search, title: "Valuables Recovery", desc: "We meticulously sort through clutter to locate lost documents, heirlooms, photos, and valuables, returning them safely to you." },
                            { icon: Recycle, title: "Sustainable Disposal", desc: "We prioritize donation and recycling. Items in good condition are donated to local charities, minimizing landfill impact." },
                            { icon: Hammer, title: "Minor Repairs", desc: "After the clear-out, we can assist with minor drywall repairs, painting prep, and carpet removal to get the home ready for sale or living.", href: "/services/foreclosure-cleanout" }
                        ].map((item, i) => (
                            <div key={i} className="bg-white p-6 rounded-xl shadow-sm hover:shadow-md transition-shadow flex flex-col items-start border border-slate-100">
                                <div className="p-3 bg-orange-50 rounded-lg mb-4">
                                    <item.icon className="text-brand-orange w-6 h-6" />
                                </div>
                                {item.href ? (
                                    <Link href={item.href} className="hover:text-brand-orange transition-colors">
                                        <h3 className="text-lg font-bold text-slate-900 mb-2">{item.title}</h3>
                                    </Link>
                                ) : (
                                    <h3 className="text-lg font-bold text-slate-900 mb-2">{item.title}</h3>
                                )}
                                <p className="text-sm text-slate-500">{item.desc}</p>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* Trust Badges */}
            <section className="py-12 bg-white border-y border-slate-100">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
                        {[
                            { icon: ShieldCheck, title: "Fully Insured", sub: "Property protection guaranteed" },
                            { icon: Clock, title: "Flexible Scheduling", sub: "Weekends & evenings available" },
                            { icon: Heart, title: "Compassionate", sub: "Kindness in every interaction" },
                            { icon: Lock, title: "Transparent Pricing", sub: "Free onsite estimates" }
                        ].map((item, i) => (
                            <div key={i} className="text-center">
                                <div className="w-12 h-12 mx-auto bg-brand-navy text-white rounded-full flex items-center justify-center mb-3">
                                    <item.icon className="w-6 h-6" />
                                </div>
                                <h4 className="font-bold text-slate-900">{item.title}</h4>
                                <p className="text-xs text-slate-500">{item.sub}</p>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* Stories */}
            <section className="py-20 bg-brand-navy text-white">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="text-center mb-16">
                        <h2 className="text-3xl font-bold uppercase tracking-wider mb-2">Stories of Renewal</h2>
                        <div className="w-16 h-1 bg-brand-orange mx-auto rounded-full"></div>
                    </div>
                    <div className="grid md:grid-cols-3 gap-8">
                        {[
                            { quote: "I was overwhelmed and embarrassed about the state of my father's house. CleanSweep came in without a hint of judgment. They were so kind to him, letting him tell stories about his things as they worked.", author: "Jennifer M.", role: "Daughter of client" },
                            { quote: "The 'discreet service' promise is real. No logos on the trucks, quiet crew. They cleared out 20 years of accumulation in 3 days. They found my grandmother's ring which I thought was gone forever.", author: "Robert T.", role: "Homeowner" },
                            { quote: "Professional, safe, and incredibly hardworking. The sanitation team did a miracle job after the cleanout. It feels like a brand new house. Thank you for giving me a fresh start.", author: "Sarah L.", role: "Homeowner" }
                        ].map((story, i) => (
                            <div key={i} className="bg-white/5 p-8 rounded-xl backdrop-blur-sm border border-white/10">
                                <div className="flex text-brand-orange mb-4">
                                    {[...Array(5)].map((_, j) => <span key={j} className="text-sm">★</span>)}
                                </div>
                                <p className="italic text-slate-300 mb-6 text-sm leading-relaxed">"{story.quote}"</p>
                                <div>
                                    <p className="font-bold text-white">{story.author}</p>
                                    <p className="text-xs text-slate-400">{story.role}</p>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* CTA */}
            <section className="py-20 bg-brand-orange" id="contact">
                <div className="max-w-4xl mx-auto px-4 text-center">
                    <h2 className="text-3xl md:text-4xl font-bold text-white mb-6">Ready to Reclaim Your Space?</h2>
                    <p className="text-white/90 text-lg mb-8">
                        Take the first step today. Contact us for a 100% confidential, judgment-free consultation. We are here to help, not to judge.
                    </p>
                    <div className="flex flex-col sm:flex-row justify-center gap-4">
                        <Link href="/get-started" className="bg-white text-brand-orange hover:bg-slate-100 font-bold py-4 px-8 rounded-full shadow-lg transition-colors flex items-center justify-center gap-2">
                            <Calendar className="w-5 h-5" /> Schedule Free Estimate
                        </Link>
                        <a href="tel:8327936566" className="bg-brand-navy text-white hover:bg-slate-900 font-bold py-4 px-8 rounded-full shadow-lg transition-colors flex items-center justify-center gap-2">
                            <Phone className="w-5 h-5" /> (832) 793-6566
                        </a>
                    </div>
                </div>
            </section>

            <Footer />
        </div>
    );
}
