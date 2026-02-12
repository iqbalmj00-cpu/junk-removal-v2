import { Metadata } from 'next';
import Link from 'next/link';
import { notFound } from 'next/navigation';
import { services, getServiceBySlug } from '@/lib/serviceData';
import { Truck, Phone, ArrowRight, ChevronDown, ChevronUp, CheckCircle, Camera } from 'lucide-react';
import { Navbar } from '@/components/Navbar';
import { Footer } from '@/components/Footer';

// Slugs with dedicated /services/<name>/page.tsx files — exclude from static generation
const DEDICATED_PAGES = new Set([
    'furniture-removal', 'appliance-removal', 'e-waste-recycling',
    'estate-cleanout', 'foreclosure-cleanout', 'garage-cleanout',
    'hoarder-cleanout', 'mattress-disposal', 'storage-unit-cleanout',
    'yard-waste-removal',
]);

export async function generateStaticParams() {
    return services
        .filter((svc) => !DEDICATED_PAGES.has(svc.slug))
        .map((svc) => ({ slug: svc.slug }));
}

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> {
    const { slug } = await params;
    const service = getServiceBySlug(slug);
    if (!service) return { title: 'Service Not Found' };
    return {
        title: service.metaTitle,
        description: service.metaDescription,
    };
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

export default async function ServicePage({ params }: { params: Promise<{ slug: string }> }) {
    const { slug } = await params;
    const service = getServiceBySlug(slug);
    if (!service) notFound();

    // JSON-LD Schema for service page
    const serviceSchema = {
        '@context': 'https://schema.org',
        '@type': 'Service',
        'name': service.title,
        'description': service.metaDescription,
        'provider': {
            '@type': 'LocalBusiness',
            'name': 'Clean Sweep Junk Removal',
            'telephone': '(832) 793-6566',
            'areaServed': 'Houston, TX',
        },
        'areaServed': {
            '@type': 'City',
            'name': 'Houston',
            'containedInPlace': { '@type': 'State', 'name': 'Texas' },
        },
    };

    return (
        <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
            <script
                type="application/ld+json"
                dangerouslySetInnerHTML={{ __html: JSON.stringify(serviceSchema) }}
            />
            <Navbar />
            <main className="flex-grow">
                {/* Hero */}
                <section className="relative bg-slate-900 pt-36 pb-20 overflow-hidden">
                    <div className="absolute inset-0 z-0 opacity-5 pointer-events-none" style={{ backgroundImage: 'radial-gradient(#f97316 1px, transparent 1px)', backgroundSize: '24px 24px' }} />
                    <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                        <div className="max-w-3xl">
                            <div className="inline-flex items-center px-4 py-1.5 rounded-full bg-brand-orange/10 border border-brand-orange/30 mb-6">
                                <Truck className="w-4 h-4 text-brand-orange mr-2" />
                                <span className="text-brand-orange font-bold text-xs uppercase tracking-widest">Professional Service</span>
                            </div>
                            <h1 className="text-4xl font-extrabold text-white sm:text-5xl lg:text-6xl uppercase tracking-tight mb-6">
                                {service.heroTitle} <span className="text-brand-orange">{service.heroHighlight}</span>
                            </h1>
                            <p className="text-xl text-slate-300 max-w-2xl leading-relaxed mb-8">
                                {service.heroDescription}
                            </p>
                            <div className="flex flex-col sm:flex-row gap-6">
                                <Link
                                    href="/get-started"
                                    className="flex items-center justify-center bg-brand-orange hover:bg-orange-600 text-white px-10 py-5 rounded-full font-bold text-xl transition-all shadow-2xl shadow-orange-900/30 uppercase tracking-wide gap-3"
                                >
                                    <Camera className="w-6 h-6" />
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

                {/* Content */}
                <section className="py-16 bg-white border-b border-slate-200">
                    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
                        <div className="prose prose-lg prose-slate max-w-none">
                            {service.content.map((paragraph, i) => (
                                <p key={i} className="text-slate-600 leading-relaxed mb-6 text-lg">
                                    {paragraph}
                                </p>
                            ))}
                        </div>
                    </div>
                </section>

                {/* What We Remove */}
                <section className="py-16 bg-slate-50">
                    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                        <div className="text-center mb-12">
                            <h2 className="text-3xl font-bold text-slate-900 uppercase tracking-tight">What We Remove</h2>
                            <div className="w-20 h-1.5 bg-brand-orange mx-auto mt-4 rounded-full" />
                        </div>
                        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4 max-w-4xl mx-auto">
                            {service.items.map((item) => (
                                <div key={item} className="flex items-center gap-3 bg-white rounded-lg px-5 py-4 shadow-sm border border-slate-100">
                                    <CheckCircle className="w-5 h-5 text-brand-orange flex-shrink-0" />
                                    <span className="text-sm font-semibold text-slate-700">{item}</span>
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
                            {service.faqs.map((faq) => (
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
                            Ready for <span className="text-brand-orange">{service.title}</span>?
                        </h2>
                        <p className="text-slate-300 text-lg mb-10 max-w-2xl mx-auto">
                            Upload a photo of your junk and get a fast, guaranteed price — or call us for an instant estimate.
                        </p>
                        <div className="flex flex-col sm:flex-row items-center justify-center gap-6">
                            <Link
                                href="/get-started"
                                className="w-full sm:w-auto bg-brand-orange hover:bg-orange-600 text-white text-xl font-bold px-10 py-5 rounded-full shadow-2xl shadow-orange-900/30 transition-all flex items-center justify-center gap-3"
                            >
                                <Camera className="w-6 h-6" />
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

                {/* Other Services */}
                <section className="py-12 bg-white border-t border-slate-200">
                    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                        <h3 className="text-lg font-bold text-slate-900 mb-4 uppercase tracking-wide">Other Services</h3>
                        <div className="flex flex-wrap gap-3">
                            {services.filter((s) => s.slug !== service.slug).map((s) => (
                                <Link
                                    key={s.slug}
                                    href={`/services/${s.slug}`}
                                    className="text-sm bg-slate-100 hover:bg-brand-orange/10 text-slate-600 hover:text-brand-orange px-4 py-2 rounded-full font-medium transition-colors flex items-center gap-1"
                                >
                                    {s.title}
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
