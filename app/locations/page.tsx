import { Metadata } from 'next';
import Link from 'next/link';
import { locations } from '@/lib/locationData';
import { MapPin, ArrowRight, Phone, Truck, Shield, Clock } from 'lucide-react';
import { Navbar } from '@/components/Navbar';
import { Footer } from '@/components/Footer';

export const metadata: Metadata = {
    title: 'Service Locations | Clean Sweep Junk Removal',
    description: 'Clean Sweep serves the greater Houston metro area. Find junk removal services in Houston, Katy, Sugar Land, The Woodlands, Pearland, Cypress, Spring, and more.',
};

export default function LocationsPage() {
    return (
        <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
            <Navbar />
            <main className="flex-grow">
                {/* Hero Section */}
                <section className="relative bg-slate-900 pt-36 pb-20 overflow-hidden">
                    <div className="absolute inset-0 opacity-5" style={{ backgroundImage: 'radial-gradient(#f97316 1px, transparent 1px)', backgroundSize: '20px 20px' }} />
                    <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
                        <div className="inline-flex items-center px-4 py-1.5 rounded-full bg-brand-orange/10 border border-brand-orange/30 mb-6">
                            <MapPin className="w-4 h-4 text-brand-orange mr-2" />
                            <span className="text-brand-orange font-bold text-xs uppercase tracking-widest">Serving Greater Houston</span>
                        </div>
                        <h1 className="text-4xl font-extrabold text-white sm:text-5xl lg:text-6xl uppercase tracking-tight mb-6">
                            Service <span className="text-brand-orange">Locations</span>
                        </h1>
                        <p className="max-w-2xl mx-auto text-xl text-slate-300 leading-relaxed">
                            We proudly serve the Houston metropolitan area and surrounding communities. Find your neighborhood below and book a fast, reliable junk removal service today.
                        </p>
                    </div>
                </section>

                {/* Trust Metrics */}
                <section className="bg-white border-b border-slate-200">
                    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
                            <div className="flex flex-col items-center">
                                <Truck className="w-8 h-8 text-brand-orange mb-2" />
                                <span className="text-2xl font-black text-slate-900">10+</span>
                                <span className="text-sm text-slate-500 font-medium">Cities Covered</span>
                            </div>
                            <div className="flex flex-col items-center">
                                <Clock className="w-8 h-8 text-brand-orange mb-2" />
                                <span className="text-2xl font-black text-slate-900">Same Day</span>
                                <span className="text-sm text-slate-500 font-medium">Service Available</span>
                            </div>
                            <div className="flex flex-col items-center">
                                <Shield className="w-8 h-8 text-brand-orange mb-2" />
                                <span className="text-2xl font-black text-slate-900">Licensed</span>
                                <span className="text-sm text-slate-500 font-medium">& Fully Insured</span>
                            </div>
                            <div className="flex flex-col items-center">
                                <Phone className="w-8 h-8 text-brand-orange mb-2" />
                                <span className="text-2xl font-black text-slate-900">Free</span>
                                <span className="text-sm text-slate-500 font-medium">Estimates</span>
                            </div>
                        </div>
                    </div>
                </section>

                {/* Location Cards Grid */}
                <section className="py-16 bg-slate-50">
                    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                        <div className="text-center mb-12">
                            <h2 className="text-3xl font-bold text-slate-900 uppercase tracking-tight">Choose Your Area</h2>
                            <div className="w-20 h-1.5 bg-brand-orange mx-auto mt-4 rounded-full" />
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
                            {locations.map((location) => (
                                <Link
                                    key={location.slug}
                                    href={`/locations/${location.slug}`}
                                    className="group bg-white rounded-xl shadow-sm hover:shadow-xl transition-all duration-300 border border-slate-100 hover:border-brand-orange/30 overflow-hidden hover:-translate-y-1"
                                >
                                    <div className="p-8">
                                        <div className="flex items-center justify-between mb-4">
                                            <div className="w-12 h-12 bg-brand-orange/10 rounded-lg flex items-center justify-center group-hover:bg-brand-orange transition-colors duration-300">
                                                <MapPin className="w-6 h-6 text-brand-orange group-hover:text-white transition-colors duration-300" />
                                            </div>
                                            <ArrowRight className="w-5 h-5 text-slate-300 group-hover:text-brand-orange transition-colors transform group-hover:translate-x-1 duration-300" />
                                        </div>
                                        <h3 className="text-xl font-bold text-slate-900 mb-2 uppercase">{location.name}, {location.state}</h3>
                                        <p className="text-sm text-slate-500 mb-4 line-clamp-2">{location.heroDescription}</p>
                                        <div className="flex flex-wrap gap-2">
                                            {location.neighborhoods.slice(0, 4).map((hood) => (
                                                <span key={hood} className="text-xs bg-slate-100 text-slate-600 px-2 py-1 rounded-full font-medium">
                                                    {hood}
                                                </span>
                                            ))}
                                            {location.neighborhoods.length > 4 && (
                                                <span className="text-xs bg-brand-orange/10 text-brand-orange px-2 py-1 rounded-full font-medium">
                                                    +{location.neighborhoods.length - 4} more
                                                </span>
                                            )}
                                        </div>
                                    </div>
                                </Link>
                            ))}
                        </div>
                    </div>
                </section>

                {/* Bottom CTA */}
                <section className="bg-slate-900 py-16">
                    <div className="max-w-4xl mx-auto px-4 text-center">
                        <h2 className="text-3xl font-bold text-white mb-4">Don&apos;t See Your Exact Neighborhood?</h2>
                        <p className="text-slate-300 text-lg mb-8 max-w-2xl mx-auto">
                            We cover more areas than we can list. Give us a call and chances are we&apos;re already serving your community.
                        </p>
                        <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                            <Link
                                href="/get-started"
                                className="w-full sm:w-auto bg-brand-orange hover:bg-orange-500 text-white text-lg font-bold px-8 py-4 rounded-lg shadow-lg transition-all flex items-center justify-center gap-2"
                            >
                                <Truck className="w-5 h-5" />
                                Book Your Pickup
                            </Link>
                            <a
                                href="tel:+18327936566"
                                className="w-full sm:w-auto bg-transparent border-2 border-slate-500 hover:border-white text-white font-semibold px-8 py-4 rounded-lg transition-colors flex items-center justify-center gap-2"
                            >
                                <Phone className="w-5 h-5" />
                                (832) 793-6566
                            </a>
                        </div>
                    </div>
                </section>
            </main>
            <Footer />
        </div>
    );
}
