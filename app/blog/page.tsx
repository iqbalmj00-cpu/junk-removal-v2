import { Metadata } from 'next';
import { Navbar } from '@/components/Navbar';
import { Footer } from '@/components/Footer';
import { Button } from '@/components/ui/Button';
import Link from 'next/link';
import Image from 'next/image';
import { Search, Calendar, User, ArrowRight, ArrowLeft } from 'lucide-react';

export const metadata: Metadata = {
    title: 'Blog | Clean Sweep Junk Removal Houston',
    description: 'Tips, guides, and news about junk removal in Houston. Learn about recycling, decluttering, and eco-friendly disposal from the Clean Sweep team.',
};

// Reusable Blog Post Card
const BlogPostCard = ({
    image,
    category,
    date,
    author,
    title,
    excerpt
}: {
    image: string,
    category: string,
    date: string,
    author: string,
    title: string,
    excerpt: string
}) => (
    <div className="bg-white rounded-3xl shadow-sm border border-slate-100 overflow-hidden group hover:shadow-xl transition-all duration-300">
        <div className="relative h-64 overflow-hidden">
            <div className="absolute top-6 left-6 z-10">
                <span className="bg-brand-orange text-white text-xs font-bold px-4 py-1.5 rounded-full uppercase tracking-wider shadow-md">
                    {category}
                </span>
            </div>
            <Image
                src={image}
                alt={title}
                fill
                className="object-cover group-hover:scale-105 transition-transform duration-700"
                sizes="(max-width: 768px) 100vw, 700px"
            />
        </div>
        <div className="p-10">
            <div className="flex items-center gap-4 text-slate-400 text-xs font-bold mb-4 uppercase tracking-wide">
                <div className="flex items-center gap-1.5">
                    <Calendar size={14} /> {date}
                </div>
                <span className="text-slate-300">|</span>
                <div className="flex items-center gap-1.5">
                    <User size={14} /> {author}
                </div>
            </div>
            <h3 className="text-2xl font-bold text-slate-900 mb-4 group-hover:text-brand-orange transition-colors leading-tight">
                {title}
            </h3>
            <p className="text-slate-500 text-lg leading-relaxed mb-6">
                {excerpt}
            </p>
            <Link href="#" className="inline-flex items-center text-brand-orange text-sm font-bold hover:text-orange-600 transition-colors uppercase tracking-wide bg-orange-50 px-4 py-2 rounded-full group-hover:bg-brand-orange group-hover:text-white">
                READ MORE <ArrowRight size={18} className="ml-2" />
            </Link>
        </div>
    </div>
);

// Recent Post Mini Card
const RecentPostItem = ({ title, date }: { title: string, date: string }) => (
    <div className="flex gap-5 group cursor-pointer items-start">
        <div className="w-24 h-24 bg-slate-200 rounded-xl shrink-0 overflow-hidden">
            <Image src="https://placehold.co/150x150/e2e8f0/475569/png?text=Thumb" alt="Thumbnail" width={96} height={96} className="w-full h-full object-cover group-hover:scale-105 transition-transform" />
        </div>
        <div>
            <h4 className="text-lg font-bold text-slate-900 leading-snug mb-2 group-hover:text-brand-orange transition-colors">
                {title}
            </h4>
            <span className="text-sm text-slate-400 font-medium">{date}</span>
        </div>
    </div>
);

export default function BlogPage() {
    return (
        <div className="min-h-screen bg-gray-50 flex flex-col font-sans">
            <Navbar />

            <main className="flex-grow pt-28">

                {/* 1. HERO SECTION */}
                <section className="bg-slate-900 py-32 px-4 text-center relative overflow-hidden">
                    <div className="max-w-5xl mx-auto relative z-10">
                        <span className="inline-block bg-brand-orange text-white text-sm font-bold px-4 py-1.5 rounded-full mb-8 uppercase tracking-widest shadow-lg shadow-orange-900/20">
                            Expert Advice & Updates
                        </span>
                        <h1 className="text-5xl md:text-7xl font-extrabold text-white mb-8 tracking-tight">
                            JUNK REMOVAL TIPS & NEWS
                        </h1>
                        <p className="text-2xl text-slate-300 max-w-3xl mx-auto font-light leading-relaxed">
                            Practical guides, eco-friendly tips, and company updates to help you reclaim your space.
                        </p>
                    </div>
                    {/* Abstract background detail */}
                    <div className="absolute top-0 left-0 w-full h-full bg-[url('https://www.transparenttextures.com/patterns/cubes.png')] opacity-10 pointer-events-none"></div>
                </section>

                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24">
                    <div className="grid grid-cols-1 lg:grid-cols-12 gap-16">

                        {/* LEFT COLUMN: Main Content (8 cols) */}
                        <div className="lg:col-span-8">
                            <div className="grid grid-cols-1 gap-12 mb-20">
                                {/* Post 1 */}
                                <BlogPostCard
                                    image="https://placehold.co/800x500/e2e8f0/475569/png?text=Eco+Tip"
                                    category="Eco-Friendly"
                                    date="Jan 12, 2026"
                                    author="Sarah Jenkins"
                                    title="5 Ways to Recycle Old Electronics Responsibly"
                                    excerpt="Don't throw those old cords in the trash! Learn the proper way to dispose of e-waste in your local community. We break down the do's and don'ts of battery, monitor, and phone disposal."
                                />
                                {/* Post 2 */}
                                <BlogPostCard
                                    image="https://placehold.co/800x500/e2e8f0/475569/png?text=Moving"
                                    category="Tips & Tricks"
                                    date="Jan 08, 2026"
                                    author="Mike Ross"
                                    title="The Ultimate Pre-Move Decluttering Checklist"
                                    excerpt="Moving soon? Save time and money by getting rid of these 10 common household items before the movers arrive. A lighter load means a cheaper move."
                                />
                                {/* Post 3 */}
                                <BlogPostCard
                                    image="https://placehold.co/800x500/e2e8f0/475569/png?text=Community"
                                    category="Company News"
                                    date="Jan 02, 2026"
                                    author="Clean Sweep Team"
                                    title="Recap: Our Annual Community Park Cleanup"
                                    excerpt="Last week, our team volunteered to clear over 500lbs of debris from Central Park. Here are the highlights and photos from a day of giving back."
                                />
                                {/* Post 4 */}
                                <BlogPostCard
                                    image="https://placehold.co/800x500/e2e8f0/475569/png?text=Garage"
                                    category="Organization"
                                    date="Dec 28, 2025"
                                    author="David Chen"
                                    title="How to Maximize Your Garage Storage Space"
                                    excerpt="Reclaim your parking spot! We break down the best shelving and storage systems for a clutter-free garage that actually fits your car."
                                />
                            </div>

                            {/* Pagination */}
                            <div className="flex justify-center items-center gap-3">
                                <Button variant="outline" className="w-12 h-12 p-0 flex items-center justify-center border-slate-300 text-slate-500 hover:text-slate-900 rounded-full">
                                    <ArrowLeft size={20} />
                                </Button>
                                <Button className="w-12 h-12 p-0 flex items-center justify-center bg-brand-orange text-white font-bold hover:bg-orange-600 rounded-full text-lg shadow-lg shadow-orange-900/20">1</Button>
                                <Button variant="outline" className="w-12 h-12 p-0 flex items-center justify-center border-slate-300 text-slate-500 hover:text-slate-900 font-bold hover:bg-slate-100 rounded-full text-lg">2</Button>
                                <Button variant="outline" className="w-12 h-12 p-0 flex items-center justify-center border-slate-300 text-slate-500 hover:text-slate-900 font-bold hover:bg-slate-100 rounded-full text-lg">3</Button>
                                <Button variant="outline" className="w-12 h-12 p-0 flex items-center justify-center border-slate-300 text-slate-500 hover:text-slate-900 rounded-full">
                                    <ArrowRight size={20} />
                                </Button>
                            </div>
                        </div>

                        {/* RIGHT COLUMN: Sidebar (4 cols) */}
                        <div className="lg:col-span-4 space-y-12">

                            {/* Search Widget */}
                            <div className="bg-white p-8 rounded-3xl shadow-sm border border-slate-100">
                                <h3 className="font-bold text-slate-900 mb-6 text-xl">Search</h3>
                                <div className="relative">
                                    <input
                                        type="text"
                                        placeholder="Search articles..."
                                        className="w-full h-14 pl-14 pr-6 bg-slate-50 rounded-xl border border-slate-200 focus:border-brand-orange focus:ring-brand-orange outline-none text-base font-medium transition-colors"
                                    />
                                    <Search className="absolute left-5 top-1/2 -translate-y-1/2 text-slate-400" size={24} />
                                </div>
                            </div>

                            {/* Categories Widget */}
                            <div className="bg-white p-8 rounded-3xl shadow-sm border border-slate-100">
                                <h3 className="font-bold text-slate-900 mb-6 text-xl">Categories</h3>
                                <ul className="space-y-4">
                                    {[
                                        { name: 'Tips & Tricks', count: 12 },
                                        { name: 'Eco-Friendly', count: 8 },
                                        { name: 'Case Studies', count: 5 },
                                        { name: 'Company News', count: 3 },
                                        { name: 'Uncategorized', count: 1 },
                                    ].map((cat) => (
                                        <li key={cat.name} className="flex items-center justify-between text-slate-500 hover:text-brand-orange cursor-pointer transition-colors group p-2 rounded-lg hover:bg-slate-50">
                                            <span className="font-medium text-lg">{cat.name}</span>
                                            <span className="bg-slate-100 text-slate-500 px-3 py-1 rounded-full text-sm font-bold group-hover:bg-brand-orange group-hover:text-white transition-colors">{cat.count}</span>
                                        </li>
                                    ))}
                                </ul>
                            </div>

                            {/* Recent Posts Widget */}
                            <div className="bg-white p-8 rounded-3xl shadow-sm border border-slate-100">
                                <h3 className="font-bold text-slate-900 mb-8 text-xl">Recent Posts</h3>
                                <div className="space-y-8">
                                    <RecentPostItem title="Why We Don't Take Paint Cans" date="Jan 10, 2026" />
                                    <RecentPostItem title="Hoarding Cleanup: A Guide" date="Dec 15, 2025" />
                                    <RecentPostItem title="Office Cleanout Checklist" date="Nov 22, 2025" />
                                </div>
                            </div>

                            {/* Sticky CTA Widget */}
                            <div className="bg-slate-900 p-10 rounded-3xl shadow-xl text-center text-white sticky top-32">
                                <h3 className="text-3xl font-extrabold mb-4 leading-tight">NEED JUNK GONE?</h3>
                                <p className="text-slate-400 mb-8 leading-relaxed text-lg">
                                    Don't let clutter take over your life. Expert removal is just a click away.
                                </p>
                                <Link href="/get-started">
                                    <Button data-track="book_now" className="w-full bg-brand-orange hover:bg-orange-600 text-white font-bold h-14 rounded-full text-lg shadow-xl shadow-orange-900/40">
                                        GET A FREE QUOTE
                                    </Button>
                                </Link>
                            </div>

                        </div>

                    </div>
                </div>
            </main>
            <Footer />
        </div>
    );
}
