import Link from 'next/link';

export function Footer() {
    return (
        <footer className="bg-brand-navy text-white pt-16 pb-8 border-t border-slate-800">
            <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
                <div className="grid grid-cols-1 md:grid-cols-4 gap-12">
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
                            <li><Link href="/get-started" className="text-slate-300 hover:text-white transition-colors">Book Online</Link></li>
                            <li><Link href="/services" className="text-slate-300 hover:text-white transition-colors">All Services</Link></li>
                            <li><Link href="/locations" className="text-slate-300 hover:text-white transition-colors">Locations</Link></li>
                            <li><Link href="/about" className="text-slate-300 hover:text-white transition-colors">About Us</Link></li>
                            <li><Link href="/contact" className="text-slate-300 hover:text-white transition-colors">Contact</Link></li>
                        </ul>
                    </div>

                    {/* Column 3: Popular Services */}
                    <div>
                        <h4 className="text-lg font-semibold mb-6 text-brand-orange">Popular Services</h4>
                        <ul className="space-y-4">
                            <li><Link href="/services/furniture-removal" className="text-slate-300 hover:text-white transition-colors">Furniture Removal</Link></li>
                            <li><Link href="/services/hot-tub-removal" className="text-slate-300 hover:text-white transition-colors">Hot Tub Removal</Link></li>
                            <li><Link href="/services/garage-cleanout" className="text-slate-300 hover:text-white transition-colors">Garage Cleanouts</Link></li>
                            <li><Link href="/services/appliance-removal" className="text-slate-300 hover:text-white transition-colors">Appliance Disposal</Link></li>
                            <li><Link href="/services/shed-demolition" className="text-slate-300 hover:text-white transition-colors">Shed Demolition</Link></li>
                            <li><Link href="/services/storage-unit-cleanout" className="text-slate-300 hover:text-white transition-colors">Storage Unit Cleanout</Link></li>
                        </ul>
                    </div>

                    {/* Column 4: Contact/Area */}
                    <div>
                        <h4 className="text-lg font-semibold mb-6 text-brand-orange">Service Area</h4>
                        <div className="space-y-4 text-slate-300">
                            <p>Greater Houston Area</p>
                            <p>Mon - Sat: 7am - 7pm</p>
                            <a href="tel:+18327936566" className="block pt-2 font-semibold text-white hover:text-brand-orange transition-colors">(832) 793-6566</a>
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
