import { Navbar } from "@/components/Navbar";
import { Footer } from "@/components/Footer";
import {
    Phone,
    ArrowRight,
    Check,
    Heart,
    Recycle,
    Home,
    Calendar,
    ShieldCheck,
    Clock,
    Trash2,
    Box,
    Truck
} from "lucide-react";
import Link from "next/link";
import { Metadata } from "next";

export const metadata: Metadata = {
    title: "Estate Cleanouts in Houston | Compassionate & Respectful | CleanSweep",
    description: "Managing an estate? We provide professional, respectful estate cleanout services in Houston. We sort, donate, and haul away the rest. Call for a free estimate.",
};

export default function EstateCleanoutPage() {
    return (
        <div className="min-h-screen bg-slate-50">
            <Navbar />

            {/* Hero Section */}
            <header className="relative bg-brand-navy overflow-hidden py-20 lg:py-32 pt-36">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
                    <div className="grid lg:grid-cols-2 gap-12 items-center">
                        <div className="space-y-8">
                            <div className="inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold tracking-wide bg-slate-800 text-slate-300 border border-slate-700 uppercase">
                                Available for Urgent Situations
                            </div>
                            <h1 className="text-4xl tracking-tight font-extrabold text-white sm:text-5xl md:text-6xl leading-tight">
                                <span className="block xl:inline">Compassionate</span> <br />
                                <span className="block text-brand-orange xl:inline">Estate Cleanouts</span>
                            </h1>
                            <p className="mt-3 text-lg text-slate-400 sm:mt-5 sm:max-w-xl md:mt-5 leading-relaxed">
                                Managing an estate is emotional work. We handle the heavy lifting, sorting, and hauling so you can focus on family and memories during this difficult time.
                            </p>
                            <div className="mt-8 sm:mt-10 flex flex-col sm:flex-row gap-4">
                                <Link href="/get-started" className="w-full sm:w-auto flex items-center justify-center px-8 py-4 border border-transparent text-lg font-bold rounded-full text-white bg-brand-orange hover:bg-orange-600 transition-colors shadow-lg shadow-orange-900/30">
                                    Request Discreet Estimate
                                </Link>
                                <a href="tel:8327936566" className="w-full sm:w-auto flex items-center justify-center px-8 py-4 border-2 border-slate-600 text-lg font-bold rounded-full text-white bg-transparent hover:bg-white/10 hover:border-white transition-colors">
                                    <Phone className="mr-2 w-5 h-5" /> (832) 793-6566
                                </a>
                            </div>
                            <div className="mt-6 flex items-center gap-6 text-sm text-slate-500 font-medium">
                                <span className="flex items-center gap-1"><Check className="text-brand-orange w-5 h-5" /> Respectful Crew</span>
                                <span className="flex items-center gap-1"><Check className="text-brand-orange w-5 h-5" /> Fully Insured</span>
                            </div>
                        </div>
                        <div className="relative lg:h-full">
                            <img
                                alt="A clean, empty living room filled with natural warm light representing a cleared estate"
                                className="rounded-2xl shadow-2xl border-4 border-slate-800 w-full object-cover h-[400px] lg:h-[500px]"
                                src="https://lh3.googleusercontent.com/aida-public/AB6AXuAH9fTqqEoI0Wl29HlsxPvOwPsrnh0vBJQrYTs4y70zm4j7SAj8PfM78sEQa92Dl9KSTmtWe5cl5Oufu5354T6g5VycsKXCsm17MtHtQ3Dp5Q5TOe4owJxdSpyP9_Xzhe7oxVn_gxfwt0R5eZ95tBmcH2ZX78f9WxpEXK3rsvL4SIVsHn2T02XFqVPB9gSYS8WD5uS8qD4cN3tTUWfxCbrRqPF578gZaUaqn0_eMBR6JcP4KnoqCG7J8s8GRPEmgztvQSHPWQsdNWA"
                            />
                            <div className="absolute inset-0 bg-gradient-to-t from-brand-navy/60 to-transparent rounded-2xl"></div>
                        </div>
                    </div>
                </div>
            </header>

            {/* Approach Section */}
            <section className="py-16 bg-white">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
                    <h2 className="text-sm text-brand-orange font-bold tracking-wide uppercase">Our Approach</h2>
                    <p className="mt-2 text-3xl leading-8 font-extrabold tracking-tight text-slate-900 sm:text-4xl">
                        Respectful Service During Life's Transitions
                    </p>
                    <p className="mt-4 max-w-2xl text-xl text-slate-500 mx-auto">
                        We understand that these items aren't just "junk"—they are memories. We treat every home with the dignity it deserves.
                    </p>
                </div>
                <div className="mt-16 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="grid grid-cols-1 gap-10 md:grid-cols-3">
                        {[
                            { icon: Heart, title: "Zero-Judgment Team", desc: "Whether it's a neatly organized home or a cluttered property needing significant clearing, our uniformed team arrives with compassion, not judgment." },
                            { icon: Recycle, title: "Donation-First Approach", desc: "We prioritize donating usable furniture, clothing, and household goods to local charities. We aim to keep memories alive and landfills empty." },
                            { icon: Home, title: "Full Property Clearing", desc: "From the attic to the basement, and even the yard. We clear everything so the property is broom-swept and ready for sale or renovation." }
                        ].map((item, i) => (
                            <div key={i} className="flex flex-col items-center text-center p-8 bg-slate-50 rounded-2xl hover:shadow-xl transition-shadow border border-slate-100 group">
                                <div className="flex items-center justify-center h-16 w-16 rounded-full bg-orange-100 text-brand-orange mb-6 group-hover:scale-110 transition-transform">
                                    <item.icon className="w-8 h-8" />
                                </div>
                                <h3 className="text-xl font-bold text-slate-900 mb-3">{item.title}</h3>
                                <p className="text-slate-500 leading-relaxed text-sm">{item.desc}</p>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* Process Detail */}
            <section className="py-20 bg-slate-50">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="lg:grid lg:grid-cols-2 lg:gap-16 items-center">
                        <div className="mb-10 lg:mb-0">
                            <h2 className="text-3xl font-extrabold text-slate-900 sm:text-4xl mb-6">
                                Seamless Estate Cleanouts for Every Situation
                            </h2>
                            <p className="text-lg text-slate-600 mb-8">
                                We partner with families, estate attorneys, and real estate agents to ensure a smooth transition. Our process is designed to alleviate stress.
                            </p>
                            <div className="space-y-8">
                                {[
                                    { icon: Box, title: "Sorting & Separation", desc: "We can help separate heirlooms for family, items for auction, donations, and disposal." },
                                    { icon: Truck, title: "Efficient Removal", desc: "Our large trucks and experienced crews can clear an entire home in a fraction of the time it takes to do it yourself." },
                                    { icon: Check, title: "Post-Job Sweep", desc: "We never leave a mess behind. We ensure the space is clean, empty, and ready for its next chapter." }
                                ].map((item, i) => (
                                    <div key={i} className="flex">
                                        <div className="flex-shrink-0">
                                            <div className="flex items-center justify-center h-12 w-12 rounded-xl bg-brand-orange text-white shadow-lg shadow-orange-200">
                                                <item.icon className="w-6 h-6" />
                                            </div>
                                        </div>
                                        <div className="ml-4">
                                            <h3 className="text-lg leading-6 font-bold text-slate-900">{item.title}</h3>
                                            <p className="mt-2 text-base text-slate-500">{item.desc}</p>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                        <div className="relative">
                            <div className="absolute inset-0 bg-brand-orange/10 transform translate-x-3 translate-y-3 rounded-2xl"></div>
                            <img
                                alt="Two professional movers carefully carrying a sofa out of a home"
                                className="relative rounded-2xl shadow-xl w-full object-cover h-[500px]"
                                src="https://lh3.googleusercontent.com/aida-public/AB6AXuCp95u0BaZtqdZszrSVkoBqkkLNL4gekAbciB8NcYNqe8kiSe0zY6ObuqOLx6EZfTLbxVzTdwX3I3oA1xX3jl7ZICEznORLaWRO_27lhlaHuW-ZSXpWpPiH2iRF72mtqG1NwVDdU_52dLLf5CqCyKDxJAVsSdZAdNyNwbgMrRBKUSF_c3PX4j6KgUnBye296u9h2e6LU41fUXDs3ABdbDcbG6r7THkKcVYv4bnnbgQg_V1GKwlsrnBsW57seK2YCgCT8gT4rGprWZg"
                            />
                        </div>
                    </div>
                </div>
            </section>

            {/* Common Items */}
            <section className="py-20 bg-white">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="text-center mb-12">
                        <h2 className="text-3xl font-extrabold text-slate-900">Common Items We Remove</h2>
                    </div>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
                        {[
                            { title: "Furniture", icon: Home },
                            { title: "Appliances", icon: Trash2 },
                            { title: "Clothing & Linens", icon: Box },
                            { title: "Electronics", icon: Calendar } // Using Calendar as placeholder for electronics/TV, could swap for Monitor if available or similar
                        ].map((item, i) => (
                            <div key={i} className="bg-slate-50 p-8 rounded-xl text-center border border-slate-100 hover:border-brand-orange transition-colors group">
                                <item.icon className="mx-auto w-10 h-10 text-brand-orange mb-4 group-hover:scale-110 transition-transform" />
                                <h3 className="font-bold text-slate-900">{item.title}</h3>
                            </div>
                        ))}
                    </div>
                    <div className="mt-10 text-center">
                        <Link href="/items-we-take" className="text-brand-orange font-bold hover:text-orange-700 flex items-center justify-center gap-1 group">
                            View full list of prohibited & accepted items <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                        </Link>
                    </div>
                </div>
            </section>

            {/* Testimonials */}
            <section className="bg-brand-navy py-20 text-white">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="text-center mb-16">
                        <h2 className="text-3xl font-extrabold sm:text-4xl text-white">What Our Neighbors Say</h2>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                        {[
                            { quote: "Handling my mother's estate was overwhelming. The CleanSweep team was incredibly patient and respectful. They didn't just rush; they helped us identify items to donate. Truly grateful.", author: "Martha R.", role: "Homeowner, Westbury" },
                            { quote: "I'm a realtor and I recommend CleanSweep to all my clients dealing with estate sales. They are discreet, fast, and the property always looks immaculate when they leave.", author: "David K.", role: "Real Estate Agent" },
                            { quote: "Fair pricing and very compassionate crew. They cleared out a 4-bedroom house in one day. The donation receipt they provided was a huge help for the estate taxes.", author: "Sarah Jenkins", role: "Executor" }
                        ].map((story, i) => (
                            <div key={i} className="bg-slate-800 p-8 rounded-2xl relative border border-slate-700">
                                <div className="flex text-brand-orange mb-4">
                                    {[...Array(5)].map((_, j) => <span key={j} className="text-sm">★</span>)}
                                </div>
                                <p className="text-slate-300 italic mb-6 text-sm leading-relaxed">"{story.quote}"</p>
                                <div>
                                    <p className="font-bold text-white">{story.author}</p>
                                    <p className="text-slate-500 text-xs uppercase">{story.role}</p>
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
