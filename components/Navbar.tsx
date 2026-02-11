"use client";

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Button } from './ui/Button';
import { Calendar, ChevronDown } from 'lucide-react';
import { useState, useRef, useEffect } from 'react';
import { Menu, X } from 'lucide-react';

const locationLinks = [
    { name: 'Houston', href: '/locations/houston' },
    { name: 'Sugar Land', href: '/locations/sugar-land' },
    { name: 'Katy', href: '/locations/katy' },
    { name: 'The Woodlands', href: '/locations/the-woodlands' },
    { name: 'Pearland', href: '/locations/pearland' },
    { name: 'Missouri City', href: '/locations/missouri-city' },
    { name: 'Cypress', href: '/locations/cypress' },
    { name: 'Spring', href: '/locations/spring' },
    { name: 'League City', href: '/locations/league-city' },
    { name: 'Pasadena', href: '/locations/pasadena' },
];

export function Navbar() {
    const pathname = usePathname();
    const [isMenuOpen, setIsMenuOpen] = useState(false);
    const [isLocationsOpen, setIsLocationsOpen] = useState(false);
    const [isMobileLocationsOpen, setIsMobileLocationsOpen] = useState(false);
    const dropdownRef = useRef<HTMLDivElement>(null);

    const navLinks = [
        { name: 'Home', href: '/' },
        { name: 'Services', href: '/services' },
        { name: 'Locations', href: '/locations', hasDropdown: true },
        { name: 'How It Works', href: '/how-it-works' },
        { name: 'Reviews', href: '/reviews' },
        { name: 'About Us', href: '/about' },
        { name: 'Contact', href: '/contact' },
    ];

    const isActive = (path: string) => pathname === path || (path === '/locations' && pathname.startsWith('/locations'));

    // Close dropdown when clicking outside
    useEffect(() => {
        function handleClickOutside(event: MouseEvent) {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
                setIsLocationsOpen(false);
            }
        }
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    return (
        <nav className="fixed top-0 left-0 right-0 z-50 bg-slate-900 border-b border-white/10 shadow-xl backdrop-blur-md">
            <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
                <div className="flex h-28 items-center justify-between">

                    {/* Logo — pushed left */}
                    <div className="flex-shrink-0 mr-auto">
                        <Link href="/" className="text-3xl font-black tracking-tighter text-white">
                            <span className="text-brand-orange">CLEAN</span>SWEEP
                        </Link>
                    </div>

                    {/* Desktop Navigation — centered */}
                    <div className="hidden lg:flex items-center justify-center flex-1">
                        <div className="flex items-center space-x-6">
                            {navLinks.map((link) => (
                                link.hasDropdown ? (
                                    <div key={link.name} className="relative" ref={dropdownRef}>
                                        <button
                                            onClick={() => setIsLocationsOpen(!isLocationsOpen)}
                                            className={`relative px-1 py-2 text-lg font-bold transition-colors duration-200 flex items-center gap-1
                                                ${isActive(link.href)
                                                    ? 'text-white border-b-4 border-brand-orange'
                                                    : 'text-slate-300 hover:text-white border-b-4 border-transparent'
                                                }`}
                                        >
                                            {link.name}
                                            <ChevronDown className={`w-4 h-4 transition-transform duration-200 ${isLocationsOpen ? 'rotate-180' : ''}`} />
                                        </button>

                                        {/* Dropdown Menu */}
                                        {isLocationsOpen && (
                                            <div className="absolute top-full left-1/2 -translate-x-1/2 mt-3 w-64 bg-slate-800 border border-slate-700 rounded-xl shadow-2xl overflow-hidden z-50">
                                                <div className="py-2">
                                                    <Link
                                                        href="/locations"
                                                        onClick={() => setIsLocationsOpen(false)}
                                                        className="block px-5 py-3 text-sm font-bold text-brand-orange hover:bg-slate-700 transition-colors border-b border-slate-700 uppercase tracking-wider"
                                                    >
                                                        All Locations
                                                    </Link>
                                                    {locationLinks.map((loc) => (
                                                        <Link
                                                            key={loc.href}
                                                            href={loc.href}
                                                            onClick={() => setIsLocationsOpen(false)}
                                                            className={`block px-5 py-2.5 text-sm font-medium transition-colors
                                                                ${pathname === loc.href
                                                                    ? 'text-brand-orange bg-slate-700/50'
                                                                    : 'text-slate-300 hover:text-white hover:bg-slate-700'
                                                                }`}
                                                        >
                                                            {loc.name}, TX
                                                        </Link>
                                                    ))}
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                ) : (
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
                                )
                            ))}
                        </div>
                    </div>

                    {/* Book Now Button — pushed right */}
                    <div className="hidden lg:block ml-auto">
                        <Link href="/get-started">
                            <Button data-track="book_now" className="bg-brand-orange hover:bg-orange-500 text-white rounded-full shadow-lg shadow-orange-900/20 font-bold px-8 py-3 text-lg">
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
                            link.hasDropdown ? (
                                <div key={link.name}>
                                    <button
                                        onClick={() => setIsMobileLocationsOpen(!isMobileLocationsOpen)}
                                        className={`w-full flex items-center justify-between rounded-md px-3 py-2 text-lg font-medium
                                            ${isActive(link.href)
                                                ? 'bg-slate-800 text-white'
                                                : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                                            }`}
                                    >
                                        {link.name}
                                        <ChevronDown className={`w-5 h-5 transition-transform duration-200 ${isMobileLocationsOpen ? 'rotate-180' : ''}`} />
                                    </button>
                                    {isMobileLocationsOpen && (
                                        <div className="ml-4 mt-1 space-y-1 border-l-2 border-brand-orange/30 pl-4">
                                            <Link
                                                href="/locations"
                                                onClick={() => { setIsMenuOpen(false); setIsMobileLocationsOpen(false); }}
                                                className="block rounded-md px-3 py-2 text-sm font-bold text-brand-orange uppercase tracking-wider"
                                            >
                                                All Locations
                                            </Link>
                                            {locationLinks.map((loc) => (
                                                <Link
                                                    key={loc.href}
                                                    href={loc.href}
                                                    onClick={() => { setIsMenuOpen(false); setIsMobileLocationsOpen(false); }}
                                                    className={`block rounded-md px-3 py-1.5 text-sm font-medium
                                                        ${pathname === loc.href
                                                            ? 'text-brand-orange'
                                                            : 'text-slate-400 hover:text-white'
                                                        }`}
                                                >
                                                    {loc.name}, TX
                                                </Link>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            ) : (
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
                            )
                        ))}
                        <div className="px-3 py-2">
                            <Link href="/get-started" onClick={() => setIsMenuOpen(false)}>
                                <Button data-track="book_now" className="w-full bg-brand-orange hover:bg-orange-500 text-white rounded-full font-bold py-3 text-lg">
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
