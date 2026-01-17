'use client';

import { useState } from 'react';
import { Navbar } from '@/components/Navbar';
import { Footer } from '@/components/Footer';
import { Button } from '@/components/ui/Button';
import Link from 'next/link';
import {
    Wallet,
    Truck,
    Calendar,
    Shield,
    ChevronDown,
    ChevronUp,
    Headset,
    Camera,
    ArrowRight
} from 'lucide-react';

// Terms for the categories
type CategoryId = 'pricing' | 'items' | 'scheduling' | 'insurance';

interface FAQItem {
    id: string;
    question: string;
    answer: string;
    hasSpecialCard?: boolean;
}

interface CategoryData {
    id: CategoryId;
    label: string;
    icon: React.ElementType;
    items: FAQItem[];
}

const FAQ_DATA: CategoryData[] = [
    {
        id: 'pricing',
        label: 'Pricing & Estimates',
        icon: Wallet,
        items: [
            {
                id: 'get-quote',
                question: 'How do I get a quote?',
                answer: 'We offer upfront, volume-based pricing. The best way to get an accurate price is to use our online booking tool or upload a photo of your junk.',
                hasSpecialCard: true
            },
            {
                id: 'min-charge',
                question: 'Is there a minimum charge?',
                answer: 'Yes, we have a minimum load charge which covers a single item or up to 1/8th of a truck load. This covers our travel, labor, and disposal fees.'
            },
            {
                id: 'hidden-fees',
                question: 'Are there any hidden fees?',
                answer: 'Never. Our upfront price includes labor, transportation, and disposal. We are transparent about any surcharges for specific items like tires or appliances.'
            }
        ]
    },
    {
        id: 'items',
        label: 'Items We Take',
        icon: Truck,
        items: [
            {
                id: 'hazardous',
                question: 'Do you take hazardous materials?',
                answer: 'No, we cannot accept hazardous materials such as paint, chemicals, asbestos, or oil drums due to disposal regulations. Please contact your local waste management facility.'
            },
            {
                id: 'heavy-furniture',
                question: 'Do you take heavy furniture from upstairs?',
                answer: 'Absolutely. Our two-person crews are trained to safely remove heavy items from anywhere in your home, including attics and basements.'
            }
        ]
    },
    {
        id: 'scheduling',
        label: 'Scheduling',
        icon: Calendar,
        items: [
            {
                id: 'home-needed',
                question: 'Do I need to be home for the pickup?',
                answer: 'Not necessarily. If the items are accessible (e.g., in a driveway) and we can process payment remotely, you do not need to be present.'
            },
            {
                id: 'how-quickly',
                question: 'How quickly can you come?',
                answer: 'We often offer same-day or next-day appointments. Check our online scheduler for real-time availability.'
            }
        ]
    },
    {
        id: 'insurance',
        label: 'Insurance & Safety',
        icon: Shield,
        items: [
            {
                id: 'insured',
                question: 'Are damages insured?',
                answer: 'Yes, Clean Sweep is fully licensed and insured. Our comprehensive coverage protects your property during every job.'
            }
        ]
    }
];

export default function FAQPage() {
    const [activeCategory, setActiveCategory] = useState<CategoryId>('pricing');
    const [openQuestions, setOpenQuestions] = useState<Record<string, boolean>>({});

    const toggleQuestion = (id: string) => {
        setOpenQuestions(prev => ({
            ...prev,
            [id]: !prev[id]
        }));
    };

    const currentCategoryData = FAQ_DATA.find(cat => cat.id === activeCategory);
    const CategoryIcon = currentCategoryData?.icon || Wallet;

    return (
        <div className="min-h-screen bg-gray-50 flex flex-col font-sans">
            <Navbar />

            <main className="flex-grow pt-40 pb-32 px-4 sm:px-6 lg:px-8">
                <div className="max-w-7xl mx-auto">

                    {/* Header */}
                    <div className="text-center mb-20">
                        <h1 className="text-5xl lg:text-6xl font-extrabold text-slate-900 mb-6 tracking-tight">FREQUENTLY ASKED QUESTIONS</h1>
                        <p className="text-2xl text-slate-500 max-w-3xl mx-auto font-light leading-relaxed">
                            Clear answers for a clutter-free experience. Find everything you need to know.
                        </p>
                    </div>

                    <div className="grid grid-cols-1 lg:grid-cols-4 gap-12 lg:gap-16">

                        {/* LEFT SIDEBAR */}
                        <div className="lg:col-span-1 space-y-10">

                            {/* Categories Menu */}
                            <div>
                                <h3 className="text-sm font-bold text-slate-400 uppercase tracking-widest mb-6 px-3">Topics</h3>
                                <nav className="flex flex-col space-y-3">
                                    {FAQ_DATA.map((category) => (
                                        <button
                                            key={category.id}
                                            onClick={() => setActiveCategory(category.id)}
                                            className={`text-left px-6 py-5 rounded-xl font-bold transition-all duration-200 flex items-center gap-4 text-lg ${activeCategory === category.id
                                                ? 'bg-white shadow-md border-l-8 border-brand-orange text-slate-900'
                                                : 'text-slate-500 hover:bg-white hover:text-slate-700'
                                                }`}
                                        >
                                            <category.icon size={22} className={activeCategory === category.id ? 'text-brand-orange' : 'text-slate-400'} />
                                            {category.label}
                                        </button>
                                    ))}
                                </nav>
                            </div>

                            {/* "Still Have Questions?" Card */}
                            <div className="bg-slate-900 rounded-2xl p-8 text-center text-white shadow-xl">
                                <div className="w-14 h-14 bg-slate-800 rounded-full flex items-center justify-center mx-auto mb-6 text-brand-orange">
                                    <Headset size={28} />
                                </div>
                                <h3 className="font-bold text-xl mb-3">Still Have Questions?</h3>
                                <p className="text-slate-400 text-base mb-8 leading-relaxed">Our dedicated support team is ready to help you.</p>
                                <Link href="/contact">
                                    <Button variant="outline" className="w-full h-12 bg-white text-slate-900 border-white hover:bg-slate-100 font-bold text-lg">
                                        Contact Support
                                    </Button>
                                </Link>
                            </div>

                        </div>

                        {/* RIGHT CONTENT AREA */}
                        <div className="lg:col-span-3">

                            {/* Section Header */}
                            <div className="flex items-center gap-5 mb-10 pb-6 border-b border-slate-200">
                                <div className="p-4 bg-orange-50 rounded-2xl text-brand-orange">
                                    <CategoryIcon size={36} />
                                </div>
                                <h2 className="text-4xl font-extrabold text-slate-900">{currentCategoryData?.label}</h2>
                            </div>

                            {/* Accordions */}
                            <div className="space-y-6">
                                {currentCategoryData?.items.map((item) => (
                                    <div key={item.id} className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden transition-shadow hover:shadow-lg">
                                        <button
                                            onClick={() => toggleQuestion(item.id)}
                                            className="w-full flex items-center justify-between p-8 text-left group"
                                        >
                                            <span className="font-bold text-xl text-slate-900 group-hover:text-brand-orange transition-colors">{item.question}</span>
                                            {openQuestions[item.id]
                                                ? <ChevronUp size={24} className="text-brand-orange" />
                                                : <ChevronDown size={24} className="text-slate-400" />
                                            }
                                        </button>

                                        {/* Answer Content */}
                                        <div className={`px-8 text-slate-600 text-lg leading-relaxed overflow-hidden transition-all duration-300 ease-in-out ${openQuestions[item.id] ? 'max-h-[600px] pb-8 opacity-100' : 'max-h-0 opacity-0'}`}>
                                            <div className="pt-2 border-t border-slate-50">
                                                <p className="mb-6 mt-4">{item.answer}</p>

                                                {/* SPECIAL DETAIL: Photo Estimate Box */}
                                                {item.hasSpecialCard && (
                                                    <div className="mt-8 border-2 border-dashed border-slate-300 bg-slate-50 rounded-2xl p-8 flex flex-col md:flex-row items-center justify-between gap-8">
                                                        <div className="flex items-center gap-6">
                                                            <div className="w-16 h-16 bg-white rounded-full flex items-center justify-center text-brand-orange shadow-md border border-slate-200 shrink-0">
                                                                <Camera size={32} />
                                                            </div>
                                                            <div>
                                                                <h4 className="font-bold text-slate-900 text-lg">Get an instant estimate.</h4>
                                                                <p className="text-slate-500">Snap a photo and let our AI do the math.</p>
                                                            </div>
                                                        </div>
                                                        <Link href="/book" className="w-full md:w-auto">
                                                            <Button className="w-full md:w-auto bg-brand-orange hover:bg-orange-600 text-white font-bold px-8 py-4 text-lg h-auto rounded-xl shadow-lg">
                                                                Upload Photos <ArrowRight size={20} className="ml-2" />
                                                            </Button>
                                                        </Link>
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>

                        </div>
                    </div>

                </div>
            </main>
            <Footer />
        </div>
    );
}
