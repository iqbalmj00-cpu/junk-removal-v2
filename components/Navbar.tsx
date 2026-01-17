"use client";

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Button } from './ui/Button';
import { Calendar } from 'lucide-react';
import { useState } from 'react';
import { Menu, X } from 'lucide-react';

export function Navbar() {
    const pathname = usePathname();
    const [isMenuOpen, setIsMenuOpen] = useState(false);

    const navLinks = [
        { name: 'Home', href: '/' },
        { name: 'Services', href: '/services' },
        { name: 'How It Works', href: '/how-it-works' },
        { name: 'About Us', href: '/about' },
        { name: 'Blog', href: '/blog' },
        { name: 'Contact', href: '/contact' },
    ];

    const isActive = (path: string) => pathname === path;

    return (
        <nav className="fixed top-0 left-0 right-0 z-50 bg-slate-900 border-b border-white/10 shadow-xl backdrop-blur-md">
            <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
                {/* Increased height to h-28 for visual impact */}
                <div className="flex h-28 items-center justify-between">

                    {/* Logo: Increased to text-3xl */}
                    <div className="flex-shrink-0">
                        <Link href="/" className="text-3xl font-black tracking-tighter text-white">
                            <span className="text-brand-orange">CLEAN</span>SWEEP
                        </Link>
                    </div>

                    {/* Desktop Navigation: Increased spacing and font size */}
                    <div className="hidden lg:block">
                        <div className="ml-10 flex items-center space-x-12">
                            {navLinks.map((link) => (
                                <Link
                                    key={link.name}
                                    href={link.href}
                                    className={`relative px-1 py-2 text-lg font-bold transition-colors duration-200
                                        ${isActive(link.href)
                                            ? 'text-white border-b-4 border-brand-orange'
                                            : 'text-slate-300 hover:text-white border-b-4 border-transparent'
                                        }`}
                                >
                                    {link.name}
                                </Link>
                            ))}
                        </div>
                    </div>

                    {/* Book Now Button: Increased padding and text size */}
                    <div className="hidden lg:block">
                        <Link href="/book">
                            <Button className="bg-brand-orange hover:bg-orange-500 text-white rounded-lg shadow-lg shadow-orange-900/20 font-bold px-8 py-3 text-lg">
                                <Calendar className="mr-2 h-5 w-5" /> Book Now
                            </Button>
                        </Link>
                    </div>

                    {/* Mobile Menu Button */}
                    <div className="lg:hidden">
                        <button
                            onClick={() => setIsMenuOpen(!isMenuOpen)}
                            className="text-slate-300 hover:text-white p-2"
                        >
                            {isMenuOpen ? <X size={32} /> : <Menu size={32} />}
                        </button>
                    </div>
                </div>
            </div>

            {/* Mobile Menu */}
            {isMenuOpen && (
                <div className="lg:hidden bg-slate-900 border-t border-slate-800">
                    <div className="space-y-1 px-2 pb-3 pt-2">
                        {navLinks.map((link) => (
                            <Link
                                key={link.name}
                                href={link.href}
                                onClick={() => setIsMenuOpen(false)}
                                className={`block rounded-md px-3 py-2 text-lg font-medium
                                    ${isActive(link.href)
                                        ? 'bg-slate-800 text-white'
                                        : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                                    }`}
                            >
                                {link.name}
                            </Link>
                        ))}
                        <div className="px-3 py-2">
                            <Link href="/book" onClick={() => setIsMenuOpen(false)}>
                                <Button className="w-full bg-brand-orange hover:bg-orange-500 text-white rounded-lg font-bold py-3 text-lg">
                                    <Calendar className="mr-2 h-5 w-5" /> Book Now
                                </Button>
                            </Link>
                        </div>
                    </div>
                </div>
            )}
        </nav>
    );
}
