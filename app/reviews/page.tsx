import { Metadata } from 'next';
import Link from 'next/link';
import { Star, CheckCircle, ThumbsUp, Phone, Camera } from 'lucide-react';
import { Navbar } from '@/components/Navbar';
import { Footer } from '@/components/Footer';

export const metadata: Metadata = {
    title: 'Customer Reviews & Testimonials | Clean Sweep Junk Removal',
    description: 'Read 500+ verified reviews from Houston-area residents. 4.9/5 stars. See why 98% of customers recommend Clean Sweep Junk Removal.',
};

const reviews = [
    {
        name: 'Michael R.',
        initials: 'MR',
        service: 'Garage Removal',
        date: 'Recent',
        text: 'Incredible service! They cleared out my entire basement in under two hours. The crew was polite, wore uniforms, and actually swept the floor after they loaded the truck. Worth every penny.',
        rating: 5,
        hasImage: true,
        imageUrl: 'https://lh3.googleusercontent.com/aida-public/AB6AXuCvSdP8CrXMboMEPhBs_me7IzuV27BcpcRiqy8J5JxcNssgvs_KkI2AA7vj8IUB4HSu9sRu-HSMzidRcLCyhKEYnT5qhOIIScuY7zdBgGsE60taQpqubTAOAMbCSEgunPTjLfO0C4AVPlG14yNZ5g-M1PCFGSY6h4AWZxtong7HO8tMuVVhHDs4q7yIyghnnq-Llwaw2-3c89pJ2LwlakK3A7fxswPSmIVDItGGJKpL5_Gnf-OuiIxDZCMCqCpQ3dEkLYOQqkYn_bk',
    },
    {
        name: 'Sarah Jenkins',
        initials: 'SJ',
        service: 'Hot Tub Removal',
        date: '1 week ago',
        text: "I needed an old hot tub removed ASAP before selling my house. Clean-Sweep gave me a quote over the phone based on photos and stuck to it. No bait and switch. Highly recommended.",
        rating: 5,
        hasImage: true,
        imageUrl: 'https://lh3.googleusercontent.com/aida-public/AB6AXuB2-Q2vZzPz5yJ6MWJvFp5RyAosTvKqUnAzSrvmIPejd5nX0mFcieuRpQ2tGm1SgUOrPbqCQG4vKixMS2GHJ7Up6sKlyQBOacBFoQr5FN_hfOfdPSKxymEBVVTT3qFGJJ2-w1HeluC3otzEu4gQFM4ULwF5af1NYmxlcl_E0Hte-jT4rjh8wz-Z1IiNu__0jJZEdKKmo0N961XCv8pTgU8JY0N0G09TDq6BNeWdcZVAKBczYLTd2bXkSpIZMstzlggSNpdrtAQgxTc',
    },
    {
        name: 'David K.',
        initials: 'DK',
        service: 'Yard Cleanup',
        date: '2 weeks ago',
        text: "Great work on the yard waste pickup. They were a little early which caught me off guard, but they waited patiently for me to open the gate. The yard looks massive now!",
        rating: 4.5,
        hasImage: false,
    },
    {
        name: 'James Wilson',
        initials: 'JW',
        service: 'Commercial Service',
        date: '3 weeks ago',
        text: "Our office renovation left a huge pile of debris. These guys brought a massive truck and cleared it in one go. Very professional operation, invoices were clear for our accounting.",
        rating: 5,
        hasImage: true,
        imageUrl: 'https://lh3.googleusercontent.com/aida-public/AB6AXuCSJLUjYFUa5IlGrjgUfbPC6RU6YcHGB9yt6TRi9e6A_gQluRfmaSvG9LuJlVEjp4_XhofAjElswRpP6hpFMeUb8r7jJTTFpTFmTdpxI6rScdGTzWccaNJx3ANIeIRyNMJuDGf_NSl6T7yuHFX5F7DtoQGUM6gF61LcfTbwIRSrxpRXIqNv3XZKlV5oIvNCN4Obx4H-saIzLVip_XgOeQny8eO9EW6_6BFWbY2NJUlISYP-_ocZWG3v_GomjaKuas-rqsyvqs5ZghI',
    },
    {
        name: 'Emily Chen',
        initials: 'EC',
        service: 'Estate Cleanout',
        date: '1 month ago',
        text: "Honestly the easiest part of my move. I pointed at the pile of boxes and old furniture, and it vanished. The team was super friendly and careful not to scratch my walls.",
        rating: 5,
        hasImage: true,
        imageUrl: 'https://lh3.googleusercontent.com/aida-public/AB6AXuABUZbjqyHn-is2AWBp0_OZ2hwuYiF8JPQmYXcxpjHkPejwm-lNWEEZwi1eM0rIXVg-yIi0xqgESGRsfTTAbFeJmFl2lpFHVqKU9zHrAQP5G-FiamfxkLuNgRMq7D7yu3NPsc-qU-lvXJBAtyZcpvxWSSdm5UX7pxY8dche3nvP4KdG0fjIJWVVL4tFoEbHcc-1aAGhdFOL99uWmhqgXAWSgnahQVmSOZ6x91YQtLH59bbeaJSLl2mBSYqTUIhuADPOvvv-uWY3YKU',
    },
    {
        name: 'Robert P.',
        initials: 'RP',
        service: 'Appliance Removal',
        date: '1 month ago',
        text: "They recycle! That was a big deal for me. I didn't want my old appliances just sitting in a landfill. Knowing they sort and donate what they can makes me feel much better.",
        rating: 5,
        hasImage: false,
    },
];

const beforeAfter = [
    {
        before: 'https://lh3.googleusercontent.com/aida-public/AB6AXuCXOgF99XzbAYJDKGsk7Mu7n4ZFwjAdbe4CUQPfmCWpYpKjbNwRLzhb_kmWxtkS13fBj8L0mRfjH19XI3KgRbuJN3TsNSixS7a7ivQ6WkHKb18iEkEcwve6was2Aoo_5M2JDR8a5m1O_8Trt5I660EpfMw3fbPZyNkxEPUASqvqjLEMjiU1SYwgC2JWztDHrWChGQNHIt93t9wEg-uRnyrlhHEZ3ZzEk_-xs472HTnoLQ71SxTFEA0j3WknBB5QM7C3Tmxh5plNf1w',
        after: 'https://lh3.googleusercontent.com/aida-public/AB6AXuDOScmoqDxkGK_G-aQxP6kTvjeDATiueAU7kbvNiAMpn3rsE04KPx7h4ehKBlWZKX2NZfi2PJqm0FgrMIRbFPfYGuBeqE7xhkryDzR1tq484bIT6n3a7gau417O4c5RXQQZIEaXl1BDOo6aRQj-OI2EswlV-pyWLqqnbDdrS5zG_BcJ78nsoXIC3BIKYZH4CpnP1QZsAsMoCE_nbRyP7lsEuc8fX8RdWOR92npdOGbRfZlcPROJHmAvzbJPwRi657zqEMDlTHwbApw',
        beforeAlt: 'Cluttered garage filled with boxes',
        afterAlt: 'Empty clean garage with concrete floor',
        quote: 'My garage was a disaster zone for 5 years. Clean-Sweep handled it in one afternoon. I can finally park my car inside!',
        author: 'The Thompson Family, Garage Cleanout',
    },
    {
        before: 'https://lh3.googleusercontent.com/aida-public/AB6AXuCRBv0F2XRdQgJwJAvQtBR_SCEGMslFHXylDFFJBVtmxf5cICNlfDjkapazCiL0cLz2dqQKjvafDAkaXo0YhNbv15jJTFRy_zS_MWGRU0vxQnqEYeOKQCd-J5TbA3wXa1Xpr8x9b-Bk2h194pZHM4sqtg3K54MjP524G74arMgfLLAOnaiJ--E3NY_BdSK9r7KW8ka0-h8Qr5bGaiJqot3oYNWdtYnq6Dn2F5oJP2hkidGZu9AyAjPhvgi301BWCOIeXNd-J87Jfjw',
        after: 'https://lh3.googleusercontent.com/aida-public/AB6AXuAlGuRWX3idp3a3W6mpsbsbkHTXdkRj877DgHExW8_ENDWHzYGTwHJIETbihWvNkzY4El3NsKQSeSvAZUI4PiggYg3_Ow72fIQpxqAxs6kMLJ8K6x37DGnJa4Y0GXYbXJuuIG6SJnrtg0mB8qbSlDAzA-Ud8G3ZfzWJnbVPY_7i3VRrn3msGocU3Oaqf2BxvP4xx3te0Zo7Mm636LDibk_MrOkYPbPzm74YifaN6g_Y1Om-tOq4AwlaYxHYuSSQ_qSlXWmygtjC554',
        beforeAlt: 'Construction debris pile in yard',
        afterAlt: 'Green manicured lawn with trees',
        quote: "We just finished a re-roofing project and had shingles everywhere. The team swept the lawn with magnets for nails. Super safe.",
        author: 'Greg M., Renovation Debris',
    },
];

function StarRating({ rating }: { rating: number }) {
    return (
        <div className="flex text-brand-orange">
            {Array.from({ length: 5 }).map((_, i) => (
                <Star key={i} className={`w-5 h-5 ${i < Math.floor(rating) ? 'fill-current' : i < rating ? 'fill-current opacity-50' : 'opacity-30'}`} />
            ))}
        </div>
    );
}

export default function ReviewsPage() {
    return (
        <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
            <Navbar />
            <main className="flex-grow">
                {/* Hero */}
                <section className="relative bg-slate-50 pt-36 pb-12 overflow-hidden">
                    <div className="absolute inset-0 z-0 opacity-5" style={{ backgroundImage: 'radial-gradient(#f97316 1px, transparent 1px)', backgroundSize: '16px 16px' }} />
                    <div className="relative z-10 max-w-4xl mx-auto px-4 text-center sm:px-6 lg:px-8">
                        <h1 className="text-4xl sm:text-5xl md:text-6xl font-extrabold text-slate-900 tracking-tight mb-6">
                            Customer <span className="relative inline-block">Reviews<span className="absolute -bottom-2 left-0 w-full h-2 bg-brand-orange/20 -skew-x-12" /></span>
                        </h1>
                        <div className="w-24 h-1.5 bg-brand-orange mx-auto mb-8 rounded-full" />
                        <p className="text-xl text-slate-500 max-w-2xl mx-auto leading-relaxed">
                            People choose us because we show up on time, quote honestly, and clean up when we&apos;re done. No hidden fees, no leftover mess.
                        </p>
                    </div>
                </section>

                {/* Trust Metrics Bar */}
                <div className="bg-white shadow-sm border-y border-slate-200">
                    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
                        <div className="flex flex-col sm:flex-row items-center justify-center gap-4 sm:gap-12">
                            <div className="flex items-center gap-3">
                                <span className="text-3xl font-bold text-slate-900">4.9/5</span>
                                <div className="flex text-brand-orange">
                                    {[...Array(5)].map((_, i) => <Star key={i} className="w-5 h-5 fill-current" />)}
                                </div>
                            </div>
                            <div className="hidden sm:block h-8 w-px bg-slate-300" />
                            <div className="flex items-center gap-2">
                                <CheckCircle className="w-5 h-5 text-green-500" />
                                <p className="text-slate-600 font-medium">Based on <strong className="text-slate-900">500+ Verified Reviews</strong></p>
                            </div>
                            <div className="hidden sm:block h-8 w-px bg-slate-300" />
                            <div className="flex items-center gap-2">
                                <ThumbsUp className="w-5 h-5 text-slate-400" />
                                <p className="text-slate-600 text-sm">98% would recommend</p>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Review Grid */}
                <section className="py-16 bg-slate-50">
                    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
                            {reviews.map((review) => (
                                <div key={review.name} className="bg-white rounded-xl p-8 shadow-sm hover:shadow-lg transition-shadow duration-300 border border-slate-100 flex flex-col h-full">
                                    <StarRating rating={review.rating} />
                                    <blockquote className="flex-grow mt-4 mb-6 text-slate-600 leading-relaxed italic">
                                        &ldquo;{review.text}&rdquo;
                                    </blockquote>
                                    <div className="flex items-center border-t border-slate-100 pt-4 mt-auto">
                                        {review.hasImage ? (
                                            /* eslint-disable-next-line @next/next/no-img-element */
                                            <img className="w-10 h-10 rounded-full object-cover ring-2 ring-brand-orange/20 mr-3" src={review.imageUrl} alt={review.name} />
                                        ) : (
                                            <div className="w-10 h-10 rounded-full bg-brand-orange/10 flex items-center justify-center text-brand-orange font-bold text-sm mr-3">
                                                {review.initials}
                                            </div>
                                        )}
                                        <div>
                                            <p className="text-sm font-bold text-slate-900">{review.name}</p>
                                            <p className="text-xs text-slate-400">{review.service} • {review.date}</p>
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                </section>

                {/* Before & After */}
                <section className="py-16 bg-white border-t border-slate-200">
                    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                        <div className="text-center mb-12">
                            <h2 className="text-3xl font-bold text-slate-900 mb-4">See the Difference</h2>
                            <p className="text-slate-500 max-w-2xl mx-auto">We don&apos;t just remove junk; we reclaim your space. Check out these transformations.</p>
                        </div>
                        <div className="grid lg:grid-cols-2 gap-12 items-start">
                            {beforeAfter.map((item, idx) => (
                                <div key={idx} className="group">
                                    <div className="relative h-64 sm:h-80 rounded-xl overflow-hidden shadow-md flex">
                                        <div className="w-1/2 relative border-r-2 border-white">
                                            {/* eslint-disable-next-line @next/next/no-img-element */}
                                            <img className="absolute inset-0 w-full h-full object-cover" src={item.before} alt={item.beforeAlt} />
                                            <div className="absolute top-4 left-4 bg-slate-900/80 text-white text-xs font-bold px-3 py-1 rounded backdrop-blur-sm">BEFORE</div>
                                        </div>
                                        <div className="w-1/2 relative">
                                            {/* eslint-disable-next-line @next/next/no-img-element */}
                                            <img className="absolute inset-0 w-full h-full object-cover" src={item.after} alt={item.afterAlt} />
                                            <div className="absolute top-4 right-4 bg-brand-orange text-white text-xs font-bold px-3 py-1 rounded shadow-sm">AFTER</div>
                                        </div>
                                    </div>
                                    <div className="mt-6 bg-slate-50 p-6 rounded-xl border-l-4 border-brand-orange">
                                        <p className="text-slate-700 italic mb-2">&ldquo;{item.quote}&rdquo;</p>
                                        <p className="text-sm font-bold text-slate-900">— {item.author}</p>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                </section>

                {/* CTA */}
                <section className="bg-slate-900 py-20 relative overflow-hidden">
                    <div className="absolute inset-0 opacity-10" style={{ backgroundImage: 'linear-gradient(45deg, #f97316 1px, transparent 1px), linear-gradient(-45deg, #f97316 1px, transparent 1px)', backgroundSize: '20px 20px' }} />
                    <div className="max-w-4xl mx-auto px-4 relative z-10 text-center">
                        <h2 className="text-3xl sm:text-4xl font-extrabold text-white mb-6">
                            Want the fastest quote? <span className="text-brand-orange">Upload a photo.</span>
                        </h2>
                        <p className="text-slate-300 text-lg mb-10 max-w-2xl mx-auto">
                            Skip the on-site visit. Snap a picture of your junk pile, upload it, and we&apos;ll send you a guaranteed price within 15 minutes.
                        </p>
                        <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                            <Link
                                href="/get-started"
                                className="w-full sm:w-auto bg-brand-orange hover:bg-orange-500 text-white text-lg font-bold px-8 py-4 rounded-lg shadow-lg transition-all flex items-center justify-center gap-3"
                            >
                                <Camera className="w-5 h-5" />
                                GET INSTANT QUOTE
                            </Link>
                            <a
                                href="tel:+18327936566"
                                className="w-full sm:w-auto bg-transparent border-2 border-slate-500 hover:border-white text-white font-semibold px-8 py-4 rounded-lg transition-colors flex items-center justify-center gap-2"
                            >
                                <Phone className="w-5 h-5" />
                                Call (832) 793-6566
                            </a>
                        </div>
                    </div>
                </section>
            </main>
            <Footer />
        </div>
    );
}
