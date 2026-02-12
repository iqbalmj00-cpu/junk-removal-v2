import Link from 'next/link';
import { Navbar } from '@/components/Navbar';
import { Footer } from '@/components/Footer';
import { Home, ArrowRight, Search, Phone } from 'lucide-react';

export default function NotFound() {
    return (
        <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
            <Navbar />
            <main className="flex-grow flex items-center justify-center">
                <div className="max-w-2xl mx-auto px-4 text-center py-32">
                    {/* 404 Badge */}
                    <div className="inline-flex items-center px-4 py-1.5 rounded-full bg-brand-orange/10 border border-brand-orange/30 mb-8">
                        <Search className="w-4 h-4 text-brand-orange mr-2" />
                        <span className="text-brand-orange font-bold text-xs uppercase tracking-widest">Page Not Found</span>
                    </div>

                    {/* Big 404 */}
                    <h1 className="text-8xl sm:text-9xl font-black text-slate-200 mb-4 tracking-tighter">404</h1>

                    <h2 className="text-3xl sm:text-4xl font-extrabold text-slate-900 mb-4 uppercase tracking-tight">
                        Oops! This Page is <span className="text-brand-orange">Gone</span>
                    </h2>

                    <p className="text-lg text-slate-500 mb-10 max-w-md mx-auto leading-relaxed">
                        Looks like this page has already been hauled away. Don&apos;t worry — we can help you find what you need.
                    </p>

                    {/* CTA Buttons */}
                    <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                        <Link
                            href="/"
                            className="flex items-center justify-center bg-brand-orange hover:bg-orange-600 text-white px-8 py-4 rounded-full font-bold text-lg transition-all shadow-xl shadow-orange-900/20 gap-2"
                        >
                            <Home className="w-5 h-5" />
                            Go Home
                        </Link>
                        <Link
                            href="/services"
                            className="flex items-center justify-center bg-slate-900 hover:bg-slate-800 text-white px-8 py-4 rounded-full font-bold text-lg transition-all gap-2"
                        >
                            View Services
                            <ArrowRight className="w-5 h-5" />
                        </Link>
                    </div>

                    {/* Phone fallback */}
                    <div className="mt-10 pt-8 border-t border-slate-200">
                        <p className="text-slate-400 text-sm mb-2">Need help right now?</p>
                        <a
                            href="tel:8327936566"
                            className="inline-flex items-center gap-2 text-brand-orange font-bold text-lg hover:text-orange-600 transition-colors"
                        >
                            <Phone className="w-5 h-5" />
                            (832) 793-6566
                        </a>
                    </div>
                </div>
            </main>
            <Footer />
        </div>
    );
}
