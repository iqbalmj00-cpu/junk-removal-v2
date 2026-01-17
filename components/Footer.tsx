import Link from 'next/link';

export function Footer() {
    return (
        <footer className="bg-brand-navy text-white pt-16 pb-8 border-t border-slate-800">
            <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-12">
                    {/* Column 1: Brand */}
                    <div className="space-y-4">
                        <h3 className="text-2xl font-bold tracking-tighter">
                            <span className="text-brand-orange">CLEAN</span>SWEEP
                        </h3>
                        <p className="text-slate-400 max-w-xs">
                            Professional junk removal services. We clean up your community, one haul at a time. Establish 2024.
                        </p>
                    </div>

                    {/* Column 2: Links */}
                    <div>
                        <h4 className="text-lg font-semibold mb-6 text-brand-orange">Quick Links</h4>
                        <ul className="space-y-4">
                            <li><Link href="/" className="text-slate-300 hover:text-white transition-colors">Home</Link></li>
                            <li><Link href="/book" className="text-slate-300 hover:text-white transition-colors">Book Online</Link></li>
                            <li><Link href="/services" className="text-slate-300 hover:text-white transition-colors">Our Services</Link></li>
                            <li><Link href="/faq" className="text-slate-300 hover:text-white transition-colors">FAQ</Link></li>
                            <li><Link href="/contact" className="text-slate-300 hover:text-white transition-colors">Contact Support</Link></li>
                        </ul>
                    </div>

                    {/* Column 3: Contact/Area */}
                    <div>
                        <h4 className="text-lg font-semibold mb-6 text-brand-orange">Service Area</h4>
                        <div className="space-y-4 text-slate-300">
                            <p>Greater Community Area</p>
                            <p>Mon - Sat: 7am - 7pm</p>
                            <p className="pt-2 font-semibold text-white">1-800-CLN-SWP</p>
                        </div>
                    </div>
                </div>

                <div className="mt-16 pt-8 border-t border-slate-800 text-center text-slate-500 text-sm">
                    &copy; {new Date().getFullYear()} Clean Sweep Junk Removal. All rights reserved.
                </div>
            </div>
        </footer>
    );
}
