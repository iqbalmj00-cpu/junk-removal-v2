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

const serviceCategories = [
    {
        title: "Residential Items",
        links: [
            { name: "Furniture Removal", href: "/services/furniture-removal" },
            { name: "Appliance Disposal", href: "/services/appliance-removal" },
            { name: "Mattress Disposal", href: "/services/mattress-disposal" },
            { name: "Yard Waste", href: "/services/yard-waste-removal" },
            { name: "E-Waste", href: "/services/e-waste-recycling" }
        ]
    },
    {
        title: "Cleanouts",
        links: [
            { name: "Estate Cleanouts", href: "/services/estate-cleanout" },
            { name: "Garage Cleanouts", href: "/services/garage-cleanout" },
            { name: "Hoarding Cleanouts", href: "/services/hoarder-cleanout" },
            { name: "Foreclosure", href: "/services/foreclosure-cleanout" },
            { name: "Storage Units", href: "/services/storage-unit-cleanout" }
        ]
    },
    {
        title: "Demolition",
        links: [
            { name: "Hot Tub Removal", href: "/services/hot-tub-removal" },
            { name: "Shed Demolition", href: "/services/shed-demolition" },
            { name: "Deck Removal", href: "/services/deck-removal" }
        ]
    },
    {
        title: "Commercial",
        links: [
            { name: "Office Furniture", href: "/services/office-furniture-removal" },
            { name: "Construction Debris", href: "/services/construction-debris-removal" },
            { name: "Property Management", href: "/commercial" }
        ]
    }
];

export function Navbar() {
    const pathname = usePathname();
    const [isMenuOpen, setIsMenuOpen] = useState(false);
    const [activeDropdown, setActiveDropdown] = useState<string | null>(null);
    const servicesDropdownRef = useRef<HTMLDivElement>(null);
    const locationsDropdownRef = useRef<HTMLDivElement>(null);

    const navLinks = [
        { name: 'Home', href: '/' },
        { name: 'Services', href: '/services', hasDropdown: true, isMegaMenu: true },
        { name: 'Locations', href: '/locations', hasDropdown: true },
        { name: 'How It Works', href: '/how-it-works' },
        { name: 'Reviews', href: '/reviews' },
        { name: 'About Us', href: '/about' },
        { name: 'Contact', href: '/contact' },
    ];

    const isActive = (path: string) => pathname === path || (path === '/locations' && pathname.startsWith('/locations'));
    const isServiceActive = () => pathname.startsWith('/services') || pathname.startsWith('/commercial');

    // Close dropdown when clicking outside
    useEffect(() => {
        function handleClickOutside(event: MouseEvent) {
            const target = event.target as Node;
            const insideServices = servicesDropdownRef.current?.contains(target);
            const insideLocations = locationsDropdownRef.current?.contains(target);
            if (!insideServices && !insideLocations) {
                setActiveDropdown(null);
            }
        }
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    const toggleDropdown = (name: string) => {
        if (activeDropdown === name) {
            setActiveDropdown(null);
        } else {
            setActiveDropdown(name);
        }
    };

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
                                    <div key={link.name} className="relative" ref={link.name === 'Services' ? servicesDropdownRef : locationsDropdownRef}>
                                        <button
                                            onClick={() => toggleDropdown(link.name)}
                                            className={`relative px-1 py-2 text-lg font-bold transition-colors duration-200 flex items-center gap-1
                                                ${(link.name === 'Locations' && isActive(link.href)) || (link.name === 'Services' && isServiceActive())
                                                    ? 'text-white border-b-4 border-brand-orange'
                                                    : 'text-slate-300 hover:text-white border-b-4 border-transparent'
                                                }`}
                                        >
                                            {link.name}
                                            <ChevronDown className={`w-4 h-4 transition-transform duration-200 ${activeDropdown === link.name ? 'rotate-180' : ''}`} />
                                        </button>

                                        {/* Locations Dropdown */}
                                        {activeDropdown === 'Locations' && link.name === 'Locations' && (
                                            <div className="absolute top-full left-1/2 -translate-x-1/2 mt-3 w-64 bg-slate-800 border border-slate-700 rounded-xl shadow-2xl overflow-hidden z-50">
                                                <div className="py-2">
                                                    <Link
                                                        href="/locations"
                                                        onClick={() => setActiveDropdown(null)}
                                                        className="block px-5 py-3 text-sm font-bold text-brand-orange hover:bg-slate-700 transition-colors border-b border-slate-700 uppercase tracking-wider"
                                                    >
                                                        All Locations
                                                    </Link>
                                                    {locationLinks.map((loc) => (
                                                        <Link
                                                            key={loc.href}
                                                            href={loc.href}
                                                            onClick={() => setActiveDropdown(null)}
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

                                        {/* Services Mega Menu */}
                                        {activeDropdown === 'Services' && link.name === 'Services' && (
                                            <div className="absolute top-full left-1/2 -translate-x-1/2 mt-3 w-[800px] bg-slate-800 border border-slate-700 rounded-xl shadow-2xl overflow-hidden z-50 p-6">
                                                <div className="grid grid-cols-4 gap-6">
                                                    {serviceCategories.map((category) => (
                                                        <div key={category.title}>
                                                            <h4 className="text-brand-orange font-bold uppercase tracking-wider text-sm mb-3 border-b border-slate-700 pb-2">
                                                                {category.title}
                                                            </h4>
                                                            <ul className="space-y-2">
                                                                {category.links.map((sublink) => (
                                                                    <li key={sublink.name}>
                                                                        <Link
                                                                            href={sublink.href}
                                                                            onClick={() => setActiveDropdown(null)}
                                                                            className="text-slate-300 hover:text-white text-sm font-medium transition-colors hover:translate-x-1 inline-block"
                                                                        >
                                                                            {sublink.name}
                                                                        </Link>
                                                                    </li>
                                                                ))}
                                                            </ul>
                                                        </div>
                                                    ))}
                                                </div>
                                                <div className="mt-6 pt-4 border-t border-slate-700 text-center">
                                                    <Link
                                                        href="/services"
                                                        onClick={() => setActiveDropdown(null)}
                                                        className="text-white hover:text-brand-orange font-bold text-sm uppercase tracking-wide transition-colors"
                                                    >
                                                        View All Services →
                                                    </Link>
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
                <div className="lg:hidden bg-slate-900 border-t border-slate-800 max-h-[calc(100vh-112px)] overflow-y-auto">
                    <div className="space-y-1 px-2 pb-3 pt-2">
                        {navLinks.map((link) => (
                            link.hasDropdown ? (
                                <div key={link.name}>
                                    <button
                                        onClick={() => toggleDropdown(link.name)}
                                        className={`w-full flex items-center justify-between rounded-md px-3 py-2 text-lg font-medium
                                            ${(link.name === 'Locations' && isActive(link.href)) || (link.name === 'Services' && isServiceActive())
                                                ? 'bg-slate-800 text-white'
                                                : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                                            }`}
                                    >
                                        {link.name}
                                        <ChevronDown className={`w-5 h-5 transition-transform duration-200 ${activeDropdown === link.name ? 'rotate-180' : ''}`} />
                                    </button>

                                    {/* Mobile Locations Dropdown */}
                                    {activeDropdown === 'Locations' && link.name === 'Locations' && (
                                        <div className="ml-4 mt-1 space-y-1 border-l-2 border-brand-orange/30 pl-4">
                                            <Link
                                                href="/locations"
                                                onClick={() => { setIsMenuOpen(false); setActiveDropdown(null); }}
                                                className="block rounded-md px-3 py-2 text-sm font-bold text-brand-orange uppercase tracking-wider"
                                            >
                                                All Locations
                                            </Link>
                                            {locationLinks.map((loc) => (
                                                <Link
                                                    key={loc.href}
                                                    href={loc.href}
                                                    onClick={() => { setIsMenuOpen(false); setActiveDropdown(null); }}
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

                                    {/* Mobile Services Dropdown */}
                                    {activeDropdown === 'Services' && link.name === 'Services' && (
                                        <div className="ml-4 mt-1 space-y-4 border-l-2 border-brand-orange/30 pl-4 py-2">
                                            {serviceCategories.map((category) => (
                                                <div key={category.title}>
                                                    <h5 className="text-brand-orange font-bold uppercase text-xs mb-2 tracking-wider">{category.title}</h5>
                                                    <ul className="space-y-1">
                                                        {category.links.map((sublink) => (
                                                            <li key={sublink.name}>
                                                                <Link
                                                                    href={sublink.href}
                                                                    onClick={() => { setIsMenuOpen(false); setActiveDropdown(null); }}
                                                                    className="block text-slate-300 hover:text-white text-sm py-1"
                                                                >
                                                                    {sublink.name}
                                                                </Link>
                                                            </li>
                                                        ))}
                                                    </ul>
                                                </div>
                                            ))}
                                            <Link
                                                href="/services"
                                                onClick={() => { setIsMenuOpen(false); setActiveDropdown(null); }}
                                                className="block text-white font-bold text-sm uppercase tracking-wide pt-2"
                                            >
                                                View All Services →
                                            </Link>
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
