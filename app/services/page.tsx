"use client";

import { Navbar } from '@/components/Navbar';
import { Footer } from '@/components/Footer';
import { Button } from '@/components/ui/Button';
import Link from 'next/link';
import { ArrowRight, FileText, Ban, ShieldCheck, MapPin, Building2, Sofa, Tv, Monitor, Construction, Leaf, Home, ChevronUp, ChevronDown, BedDouble, Warehouse, Heart, Landmark, Package, Flame, Hammer, Fence, Briefcase } from 'lucide-react';
import { useState } from 'react';

// --- SERVICE CARD COMPONENT ---
// Handling interactivity inline as requested manually
interface ServiceCardProps {
    icon: React.ReactNode;
    title: string;
    description: string;
    fullDescription: string;
    slug: string;
}

function ServiceCard({ icon, title, description, fullDescription, slug }: ServiceCardProps) {
    const [isExpanded, setIsExpanded] = useState(false);

    return (
        <div
            className={`bg-white rounded-2xl p-8 border border-slate-200 shadow-sm transition-all duration-300 group flex flex-col h-full
            ${isExpanded ? 'shadow-xl ring-2 ring-brand-orange/10' : 'hover:shadow-lg hover:border-orange-200'}`}
        >
            <div className="w-16 h-16 bg-orange-50 rounded-xl flex items-center justify-center text-orange-600 mb-6 group-hover:bg-brand-orange group-hover:text-white transition-colors duration-300">
                {icon}
            </div>

            <h3 className="text-2xl font-bold text-slate-900 mb-3 tracking-tight">
                {title}
            </h3>

            <div className="flex-grow">
                <p className="text-slate-500 leading-relaxed mb-4 text-lg">
                    {description}
                </p>

                {/* Expandable Content */}
                <div className={`overflow-hidden transition-all duration-500 ease-in-out ${isExpanded ? 'max-h-96 opacity-100 mb-6' : 'max-h-0 opacity-0'}`}>
                    <p className="text-slate-600 leading-relaxed border-t border-slate-100 pt-4">
                        {fullDescription}
                    </p>
                </div>
            </div>

            <div className="mt-auto pt-2 flex items-center justify-between">
                <button
                    onClick={() => setIsExpanded(!isExpanded)}
                    className="flex items-center text-sm font-bold text-slate-900 group-hover:text-brand-orange transition-colors uppercase tracking-wide hover:underline focus:outline-none"
                >
                    {isExpanded ? (
                        <>Show Less <ChevronUp size={16} className="ml-1" /></>
                    ) : (
                        <>Learn More <ArrowRight size={16} className="ml-1" /></>
                    )}
                </button>
                <Link
                    href={`/services/${slug}`}
                    className="text-sm font-bold text-brand-orange hover:text-orange-600 transition-colors flex items-center gap-1"
                >
                    View Details <ArrowRight size={14} />
                </Link>
            </div>
        </div>
    );
}

export default function ServicesPage() {
    const services = [
        {
            icon: <Sofa size={36} />,
            title: "Furniture Removal",
            slug: "furniture-removal",
            description: "We handle heavy lifting for couches, tables, mattresses, chairs, and love seats.",
            fullDescription: "Our team is trained to safely maneuver large items through tight hallways and stairwells without damaging your property. We disassemble bulky pieces when necessary and ensure every item is donated or recycled whenever possible to minimize landfill waste."
        },
        {
            icon: <Tv size={36} />,
            title: "Appliance Removal",
            slug: "appliance-removal",
            description: "Responsible disposal of fridges, washers, dryers, and ovens.",
            fullDescription: "Old appliances often contain hazardous chemicals like freon that require specialized handling. We partner with certified recycling facilities to ensure these materials are extracted safely before the metal is scrapped, keeping our community safe and compliant."
        },
        {
            icon: <Monitor size={36} />,
            title: "E-Waste Recycling",
            slug: "e-waste-recycling",
            description: "Secure and eco-friendly disposal for computers, monitors, printers, and TVs.",
            fullDescription: "Electronic waste is a growing global problem. We ensure your old devices are stripped for valuable components like copper and gold, while hazardous elements like lead and mercury are responsibly contained. Your data privacy is respected throughout the process."
        },
        {
            icon: <BedDouble size={36} />,
            title: "Mattress Disposal",
            slug: "mattress-disposal",
            description: "We pick up mattresses and box springs of any size — king, queen, twin, and more.",
            fullDescription: "Curbside pickup won't take mattresses and they don't fit in your car. Our crew handles all the heavy lifting, including navigating tight hallways and staircases. Mattresses in good condition are donated, and the rest goes to certified recycling facilities."
        },
        {
            icon: <Leaf size={36} />,
            title: "Yard Waste Removal",
            slug: "yard-waste-removal",
            description: "Seasonal cleanup made easy. Branches, leaves, dirt, mulch, and small trees removed.",
            fullDescription: "From storm cleanup to annual landscaping projects, organic waste can pile up fast. We compost the majority of yard waste we collect, turning your old branches and clippings into nutrient-rich soil for local parks and gardens."
        },
        {
            icon: <Construction size={36} />,
            title: "Construction Debris Removal",
            slug: "construction-debris-removal",
            description: "Fast cleanup for renovation sites. We take drywall, wood, tiles, flooring, and roofing.",
            fullDescription: "Whether you're a DIY enthusiast or a professional contractor, job site debris can slow you down. We offer scheduled pickups to keep your workspace clear, ensuring safety and compliance with local disposal regulations for heavier construction materials."
        },
        {
            icon: <Home size={36} />,
            title: "Estate Cleanouts",
            slug: "estate-cleanout",
            description: "Total property cleanouts for garages, attics, basements, and estates.",
            fullDescription: "Dealing with a hoard or an estate cleanout can be emotional and overwhelming. Our compassionate team handles these respectful large-scale jobs with discretion and efficiency, sorting items for donation, recycling, and disposal to get the property ready for its next chapter."
        },
        {
            icon: <Warehouse size={36} />,
            title: "Garage Cleanout",
            slug: "garage-cleanout",
            description: "Can't park in your garage anymore? We clear decades of accumulated clutter.",
            fullDescription: "Over the years, holiday decorations, old furniture, broken tools, and forgotten boxes pile up. Our crew removes everything you point to, donating usable items and recycling what we can. Most single-car garage cleanouts are completed in 2-3 hours."
        },
        {
            icon: <Heart size={36} />,
            title: "Hoarder Cleanout",
            slug: "hoarder-cleanout",
            description: "Compassionate, non-judgmental cleanout services for hoarding situations.",
            fullDescription: "Our crews are trained to work with patience and discretion. We work at the homeowner's pace, carefully setting aside sentimental items. Our service is fully confidential — we use unmarked vehicles and maintain complete privacy."
        },
        {
            icon: <Landmark size={36} />,
            title: "Foreclosure Cleanout",
            slug: "foreclosure-cleanout",
            description: "Fast property clearing for banks, REO companies, and property managers.",
            fullDescription: "We remove all contents, sweep and clean the property, and haul everything away in a single visit. Most properties are cleared and ready to list within 24 hours. Volume pricing available for portfolios of multiple properties."
        },
        {
            icon: <Package size={36} />,
            title: "Storage Unit Cleanout",
            slug: "storage-unit-cleanout",
            description: "Stop paying rent on stuff you don't need. We clear units of any size.",
            fullDescription: "We handle units from 5x5 lockers to 10x30 warehouse-style units. Our crew loads everything directly into our truck, sorting donations and recyclables. Most units are cleared in under 2 hours — you don't even need to be present."
        },
        {
            icon: <Flame size={36} />,
            title: "Hot Tub Removal",
            slug: "hot-tub-removal",
            description: "We safely disconnect, disassemble, and haul away your old hot tub or spa.",
            fullDescription: "Our crew handles the full process: disconnecting electrical and water lines, draining the tub, disassembling it when needed, and hauling everything away. Acrylic, wood, and metal components are recycled wherever possible."
        },
        {
            icon: <Hammer size={36} />,
            title: "Shed Demolition",
            slug: "shed-demolition",
            description: "We demolish and haul away old sheds, playsets, and outdoor structures.",
            fullDescription: "We dismantle wood, metal, and vinyl sheds of all sizes. Everything is broken down and hauled to recycling or disposal facilities. We also remove concrete pads, playsets, pergolas, fencing, and other yard structures."
        },
        {
            icon: <Fence size={36} />,
            title: "Deck Removal",
            slug: "deck-removal",
            description: "We tear down old wood and composite decks and haul everything away.",
            fullDescription: "We remove decks of all sizes, from small porches to large multi-level structures. Our crew carefully dismantles boards, railing, stairs, and support posts. Concrete footings removed on request. Site left clean and level."
        },
        {
            icon: <Briefcase size={36} />,
            title: "Office Furniture Removal",
            slug: "office-furniture-removal",
            description: "Cubicles, desks, chairs, filing cabinets, and full office cleanouts.",
            fullDescription: "We work evenings and weekends to minimize disruption to your business. Our crews disassemble cubicle systems, remove heavy conference tables, and clear entire floors. Usable furniture is donated to Houston nonprofits and schools."
        }
    ];

    const prohibitedItems = [
        "Hazardous Chemicals",
        "Paint & Solvents",
        "Asbestos",
        "Car Batteries",
        "Medical Waste",
        "Oil Drums / Tanks",
        "Propane Tanks",
        "Explosives / Ammunition"
    ];

    return (
        <div className="min-h-screen bg-slate-50 flex flex-col font-sans pt-28">
            <Navbar />

            <main className="flex-grow">

                {/* 1. HERO SECTION (Dark Navy) */}
                <section className="bg-slate-900 pt-24 pb-32 px-4 sm:px-6 lg:px-8 relative overflow-hidden text-center">
                    {/* Decorative background element */}
                    <div className="absolute top-0 right-0 w-1/3 h-full bg-slate-800/20 skew-x-12 translate-x-20 pointer-events-none"></div>

                    <div className="max-w-7xl mx-auto relative z-10">
                        <span className="inline-flex items-center px-4 py-1.5 rounded-full bg-slate-800 border border-slate-700 text-brand-orange text-sm font-bold tracking-wide uppercase mb-8">
                            <ShieldCheck size={16} className="mr-2" /> Licensed & Insured
                        </span>

                        <h1 className="text-5xl md:text-7xl font-extrabold text-white mb-8 leading-tight tracking-tight">
                            OUR PROFESSIONAL <span className="text-brand-orange">SERVICES</span>
                        </h1>

                        <p className="text-2xl text-slate-300 max-w-3xl mb-12 leading-relaxed font-light mx-auto">
                            We provide efficient, reliable junk removal for homes, construction sites, and businesses.
                        </p>

                        <div className="flex flex-col sm:flex-row gap-6 justify-center">
                            {/* Task 1: High Visibility White Button -> Orange High Contrast */}
                            <Link href="/locations">
                                <Button className="bg-brand-orange text-white hover:bg-orange-600 text-lg font-bold px-10 py-5 rounded-full shadow-xl transition-all h-auto">
                                    <MapPin size={22} className="mr-3" /> VIEW COVERAGE AREA
                                </Button>
                            </Link>

                            <Link href="/commercial">
                                <Button variant="outline" className="text-white border-2 border-slate-600 hover:bg-white hover:text-slate-900 hover:border-white text-lg font-bold px-10 py-5 rounded-full h-auto transition-all">
                                    <Building2 size={22} className="mr-3" /> BUSINESS SOLUTIONS
                                </Button>
                            </Link>
                        </div>
                    </div>
                </section>

                {/* 2. PRO SERVICE CARDS */}
                <section className="py-32 px-4 sm:px-6 lg:px-8 bg-slate-50">
                    <div className="max-w-7xl mx-auto">
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-10">
                            {services.map((service, index) => (
                                <ServiceCard
                                    key={index}
                                    {...service}
                                />
                            ))}
                        </div>
                    </div>
                </section>

                {/* 3. ITEMS WE DO NOT ACCEPT (Expanded Scale) */}
                <section className="bg-white py-32 px-4 sm:px-6 lg:px-8 border-y border-slate-100">
                    <div className="max-w-5xl mx-auto text-center">

                        <div className="inline-block p-4 bg-red-50 text-red-500 rounded-full mb-8">
                            <Ban size={48} strokeWidth={2.5} />
                        </div>

                        <h2 className="text-4xl md:text-5xl font-extrabold text-slate-900 mb-16">Items We Do Not Accept</h2>

                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-x-8 gap-y-6 text-left max-w-4xl mx-auto">
                            {prohibitedItems.map((item, idx) => (
                                <div key={idx} className="flex items-center gap-4 p-3 rounded-lg hover:bg-slate-50 transition-colors">
                                    <span className="w-3 h-3 bg-red-500 rounded-full flex-shrink-0 shadow-sm" />
                                    <span className="text-slate-700 font-bold text-lg">{item}</span>
                                </div>
                            ))}
                        </div>

                        <div className="mt-16 max-w-3xl mx-auto p-6 bg-slate-50 border border-slate-200 rounded-2xl text-slate-500 text-base leading-relaxed">
                            * For safety and legal reasons, we cannot transport these materials. Please contact your local municipal waste management for disposal instructions.
                        </div>
                    </div>
                </section>

                {/* 4. CTA SECTION (Expanded Scale) */}
                <section className="bg-slate-900 py-32 px-4 sm:px-6 lg:px-8 text-center relative overflow-hidden">
                    {/* Background pattern */}
                    <div className="absolute inset-0 opacity-10" style={{ backgroundImage: 'radial-gradient(#ffffff 1px, transparent 1px)', backgroundSize: '40px 40px' }}></div>

                    <div className="max-w-5xl mx-auto relative z-10">
                        <h2 className="text-5xl md:text-6xl font-extrabold text-white mb-6 tracking-tight">
                            Ready to clear the clutter?
                        </h2>
                        <p className="text-slate-400 text-2xl mb-14 font-light max-w-3xl mx-auto">
                            Get honest, upfront pricing in seconds with our AI-powered tool.
                        </p>

                        <div className="flex flex-col items-center gap-8">
                            <Link href="/get-started">
                                <Button data-track="book_now" className="h-auto px-12 py-6 text-xl font-bold shadow-2xl shadow-orange-900/50 bg-brand-orange hover:bg-orange-600 text-white rounded-full transition-transform hover:scale-105">
                                    <FileText size={28} className="mr-3" /> GET AN INSTANT QUOTE
                                </Button>
                            </Link>
                            <span className="text-slate-500 text-lg font-medium">
                                or call us at <a href="tel:8327936566" className="inline-block"><span className="text-slate-300 hover:text-white cursor-pointer transition-colors border-b border-slate-600 hover:border-white pb-0.5">(832) 793-6566</span></a>
                            </span>
                        </div>
                    </div>
                </section>

            </main>
            <Footer />
        </div>
    );
}
