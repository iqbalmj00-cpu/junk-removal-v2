import { Metadata } from 'next';
import Link from 'next/link';
import { notFound } from 'next/navigation';
import { locations, getLocationBySlug } from '@/lib/locationData';
import { MapPin, Phone, Star, ChevronDown, ChevronUp, ArrowRight, Truck, Shield, Clock, Recycle } from 'lucide-react';
import { Navbar } from '@/components/Navbar';
import { Footer } from '@/components/Footer';

// Generate static paths for all locations
export async function generateStaticParams() {
    return locations.map((loc) => ({ slug: loc.slug }));
}

// Generate dynamic metadata
export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> {
    const { slug } = await params;
    const location = getLocationBySlug(slug);
    if (!location) return { title: 'Location Not Found' };
    return {
        title: location.metaTitle,
        description: location.metaDescription,
    };
}

function StarRating({ rating }: { rating: number }) {
    return (
        <div className="flex text-brand-orange">
            {Array.from({ length: 5 }).map((_, i) => (
                <Star key={i} className={`w-4 h-4 ${i < rating ? 'fill-current' : 'opacity-30'}`} />
            ))}
        </div>
    );
}

function FAQItem({ question, answer }: { question: string; answer: string }) {
    return (
        <details className="group border border-slate-200 rounded-lg overflow-hidden">
            <summary className="flex items-center justify-between cursor-pointer px-6 py-4 bg-white hover:bg-slate-50 transition-colors">
                <span className="font-semibold text-slate-900">{question}</span>
                <ChevronDown className="w-5 h-5 text-slate-400 group-open:hidden" />
                <ChevronUp className="w-5 h-5 text-brand-orange hidden group-open:block" />
            </summary>
            <div className="px-6 py-4 bg-slate-50 text-slate-600 leading-relaxed border-t border-slate-200">
                {answer}
            </div>
        </details>
    );
}

export default async function LocationPage({ params }: { params: Promise<{ slug: string }> }) {
    const { slug } = await params;
    const location = getLocationBySlug(slug);
    if (!location) notFound();

    return (
        <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
            <Navbar />
            <main className="flex-grow">
                {/* Hero Section */}
                <section className="relative bg-slate-900 pt-36 pb-20 overflow-hidden">
                    {/* Location Hero Image */}
                    <img
                        src={`/images/locations/${location.slug}.png`}
                        alt={`${location.name}, Texas`}
                        className="absolute inset-0 w-full h-full object-cover"
                    />
                    {/* Dark gradient overlay for text readability */}
                    <div className="absolute inset-0 bg-gradient-to-r from-slate-900/90 via-slate-900/80 to-slate-900/50" />
                    <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                        <div className="max-w-3xl">
                            <div className="inline-flex items-center px-4 py-1.5 rounded-full bg-brand-orange/10 border border-brand-orange/30 mb-6">
                                <MapPin className="w-4 h-4 text-brand-orange mr-2" />
                                <span className="text-brand-orange font-bold text-xs uppercase tracking-widest">{location.heroBadge}</span>
                            </div>
                            <h1 className="text-4xl font-extrabold text-white sm:text-5xl lg:text-6xl uppercase tracking-tight mb-6">
                                Junk Removal in <span className="text-brand-orange">{location.name}, {location.state}</span>
                            </h1>
                            <p className="text-xl text-slate-300 max-w-2xl leading-relaxed mb-8">
                                {location.heroDescription}
                            </p>
                            <div className="flex flex-col sm:flex-row gap-6">
                                <Link
                                    href="/get-started"
                                    className="flex items-center justify-center bg-brand-orange hover:bg-orange-600 text-white px-10 py-5 rounded-full font-bold text-xl transition-all shadow-2xl shadow-orange-900/30 uppercase tracking-wide gap-3"
                                >
                                    <Truck className="w-6 h-6" />
                                    Get A Free Quote
                                </Link>
                                <Link
                                    href="tel:8327936566"
                                    className="flex items-center justify-center bg-transparent border-2 border-white text-white hover:bg-white hover:text-slate-900 px-10 py-5 rounded-full font-bold text-xl transition-all duration-300 gap-3"
                                >
                                    <Phone className="text-brand-orange w-6 h-6" />
                                    (832) 793-6566
                                </Link>
                            </div>
                        </div>
                    </div>
                </section>

                {/* Services Overview */}
                <section className="py-16 bg-white border-b border-slate-200">
                    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                        <div className="text-center mb-12">
                            <h2 className="text-3xl font-bold text-slate-900 uppercase tracking-tight">Our Services in {location.name}</h2>
                            <div className="w-20 h-1.5 bg-brand-orange mx-auto mt-4 rounded-full" />
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
                            {[
                                { icon: <Truck className="w-8 h-8" />, title: 'Residential Removal', desc: 'Furniture, appliances, yard debris, and full cleanouts for homes.' },
                                { icon: <Shield className="w-8 h-8" />, title: 'Commercial Cleanouts', desc: 'Office furniture, e-waste, warehouse clearing, and construction debris.' },
                                { icon: <Clock className="w-8 h-8" />, title: 'Same-Day Service', desc: 'Need it gone today? We offer same-day pickups for most jobs.' },
                                { icon: <Recycle className="w-8 h-8" />, title: 'Eco-Friendly Disposal', desc: 'We recycle and donate usable items. Never just a landfill run.' },
                            ].map((svc) => (
                                <div key={svc.title} className="group p-8 bg-slate-50 rounded-xl border border-slate-100 hover:border-brand-orange/30 transition-all hover:-translate-y-1 duration-300">
                                    <div className="w-14 h-14 bg-brand-orange/10 rounded-lg flex items-center justify-center mb-5 text-brand-orange group-hover:bg-brand-orange group-hover:text-white transition-colors duration-300">
                                        {svc.icon}
                                    </div>
                                    <h3 className="text-lg font-bold text-slate-900 mb-2 uppercase">{svc.title}</h3>
                                    <p className="text-sm text-slate-500">{svc.desc}</p>
                                </div>
                            ))}
                        </div>
                    </div>
                </section>

                {/* Neighborhoods */}
                <section className="py-16 bg-slate-50">
                    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                        <div className="text-center mb-12">
                            <h2 className="text-3xl font-bold text-slate-900 uppercase tracking-tight">Neighborhoods We Serve</h2>
                            <div className="w-20 h-1.5 bg-brand-orange mx-auto mt-4 rounded-full" />
                            <p className="mt-4 text-slate-500 max-w-xl mx-auto">{location.neighborhoodSubtitle}</p>
                        </div>
                        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4 max-w-5xl mx-auto">
                            {location.neighborhoods.map((hood) => (
                                <div
                                    key={hood}
                                    className="bg-white rounded-lg px-4 py-3 text-center shadow-sm border border-slate-100 hover:border-brand-orange/30 hover:shadow-md transition-all duration-200"
                                >
                                    <MapPin className="w-4 h-4 text-brand-orange mx-auto mb-1" />
                                    <p className="text-sm font-semibold text-slate-700">{hood}</p>
                                </div>
                            ))}
                        </div>
                    </div>
                </section>

                {/* Pricing Factors */}
                <section className="py-16 bg-white">
                    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                        <div className="text-center mb-12">
                            <h2 className="text-3xl font-bold text-slate-900 uppercase tracking-tight">Transparent Pricing for {location.name}</h2>
                            <div className="w-20 h-1.5 bg-brand-orange mx-auto mt-4 rounded-full" />
                            <p className="mt-4 text-slate-500 max-w-2xl mx-auto">{location.pricingIntro}</p>
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-5xl mx-auto">
                            {location.pricingFactors.map((factor) => (
                                <div key={factor.title} className="p-8 bg-slate-50 rounded-xl border border-slate-100">
                                    <div className="w-12 h-12 bg-brand-orange/10 rounded-lg flex items-center justify-center mb-5 text-brand-orange">
                                        <span className="material-icons text-2xl">{factor.icon}</span>
                                    </div>
                                    <h3 className="text-lg font-semibold text-slate-900 mb-3">{factor.title}</h3>
                                    <p className="text-sm text-slate-500 leading-relaxed">{factor.description}</p>
                                </div>
                            ))}
                        </div>
                    </div>
                </section>

                {/* Reviews */}
                <section className="py-16 bg-slate-50">
                    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                        <div className="text-center mb-12">
                            <h2 className="text-3xl font-bold text-slate-900 uppercase tracking-tight">What {location.name} Residents Say</h2>
                            <div className="w-20 h-1.5 bg-brand-orange mx-auto mt-4 rounded-full" />
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-5xl mx-auto">
                            {location.reviews.map((review) => (
                                <div key={review.name} className="bg-white rounded-xl p-8 shadow-sm border border-slate-100 flex flex-col">
                                    <StarRating rating={review.rating} />
                                    <blockquote className="flex-grow mt-4 mb-6 text-slate-600 leading-relaxed italic">
                                        &ldquo;{review.text}&rdquo;
                                    </blockquote>
                                    <div className="flex items-center border-t border-slate-100 pt-4 mt-auto">
                                        <div className="w-10 h-10 rounded-full bg-brand-orange/10 flex items-center justify-center text-brand-orange font-bold text-sm mr-3">
                                            {review.initials}
                                        </div>
                                        <div>
                                            <p className="text-sm font-bold text-slate-900">{review.name}</p>
                                            <p className="text-xs text-slate-400">{review.area}</p>
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                </section>

                {/* FAQ */}
                <section className="py-16 bg-white">
                    <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
                        <div className="text-center mb-12">
                            <h2 className="text-3xl font-bold text-slate-900 uppercase tracking-tight">Frequently Asked Questions</h2>
                            <div className="w-20 h-1.5 bg-brand-orange mx-auto mt-4 rounded-full" />
                        </div>
                        <div className="space-y-4">
                            {location.faqs.map((faq) => (
                                <FAQItem key={faq.question} question={faq.question} answer={faq.answer} />
                            ))}
                        </div>
                    </div>
                </section>

                {/* Bottom CTA */}
                <section className="relative bg-slate-900 py-20 overflow-hidden">
                    <div className="absolute inset-0 opacity-10" style={{ backgroundImage: 'linear-gradient(45deg, #f97316 1px, transparent 1px), linear-gradient(-45deg, #f97316 1px, transparent 1px)', backgroundSize: '20px 20px' }} />
                    <div className="max-w-4xl mx-auto px-4 relative z-10 text-center">
                        <h2 className="text-3xl sm:text-4xl font-extrabold text-white mb-6">
                            Ready to Clear Out Your Space in <span className="text-brand-orange">{location.name}</span>?
                        </h2>
                        <p className="text-slate-300 text-lg mb-10 max-w-2xl mx-auto">
                            Upload a photo of your junk and get a fast, guaranteed price — or call us for an instant estimate.
                        </p>
                        <div className="flex flex-col sm:flex-row items-center justify-center gap-6">
                            <Link
                                href="/get-started"
                                className="w-full sm:w-auto bg-brand-orange hover:bg-orange-600 text-white text-xl font-bold px-10 py-5 rounded-full shadow-2xl shadow-orange-900/30 transition-all flex items-center justify-center gap-3"
                            >
                                <Truck className="w-6 h-6" />
                                Get Instant Quote
                            </Link>
                            <Link
                                href="tel:8327936566"
                                className="w-full sm:w-auto bg-transparent border-2 border-white text-white hover:bg-white hover:text-slate-900 text-xl font-bold px-10 py-5 rounded-full transition-all duration-300 flex items-center justify-center gap-3"
                            >
                                <Phone className="text-brand-orange w-6 h-6" />
                                (832) 793-6566
                            </Link>
                        </div>
                    </div>
                </section>

                {/* Other Locations */}
                <section className="py-12 bg-white border-t border-slate-200">
                    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                        <h3 className="text-lg font-bold text-slate-900 mb-4 uppercase tracking-wide">Other Service Areas</h3>
                        <div className="flex flex-wrap gap-3">
                            {locations.filter((l) => l.slug !== location.slug).map((l) => (
                                <Link
                                    key={l.slug}
                                    href={`/locations/${l.slug}`}
                                    className="text-sm bg-slate-100 hover:bg-brand-orange/10 text-slate-600 hover:text-brand-orange px-4 py-2 rounded-full font-medium transition-colors flex items-center gap-1"
                                >
                                    {l.name}, {l.state}
                                    <ArrowRight className="w-3 h-3" />
                                </Link>
                            ))}
                        </div>
                    </div>
                </section>
            </main>
            <Footer />
        </div>
    );
}
