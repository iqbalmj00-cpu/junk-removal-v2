import Link from 'next/link';
import { Navbar } from '@/components/Navbar';
import { Footer } from '@/components/Footer';
import { Button } from '@/components/ui/Button';
import { Calendar, Truck, Sparkles, Phone, ArrowRight, Star, Sofa, Tv, Shovel, Hammer, Recycle, Trash2, ShieldCheck, Clock, Wallet } from 'lucide-react';

export default function Home() {
  return (
    <div className="min-h-screen bg-slate-50 flex flex-col pt-28 font-sans">
      <Navbar />

      <main className="flex-grow">

        {/* SECTION 1: HERO */}
        <section className="bg-slate-900 relative overflow-hidden">
          <div className="max-w-7xl mx-auto">
            <div className="grid grid-cols-1 lg:grid-cols-2 min-h-[700px] items-center">

              {/* Left Column: Text */}
              <div className="px-6 py-20 lg:py-32 lg:pr-12 relative z-10 text-center lg:text-left">
                <div className="inline-block bg-slate-800 border border-slate-700 rounded-full px-6 py-2 mb-10">
                  <span className="text-slate-300 text-sm font-bold tracking-wider uppercase">Available for Same-Day Pickup</span>
                </div>

                <h1 className="text-6xl lg:text-8xl font-extrabold text-white leading-[1.1] mb-8 tracking-tight">
                  WE MAKE JUNK <span className="text-brand-orange">DISAPPEAR</span>
                </h1>

                <p className="text-xl text-slate-400 mb-14 max-w-lg mx-auto lg:mx-0 leading-relaxed font-light">
                  Professional, full-service removal for homes and businesses. We handle the heavy lifting so you don't have to.
                </p>

                <div className="flex flex-col sm:flex-row gap-6 mb-10 justify-center lg:justify-start">
                  <Link href="/book" passHref>
                    <Button className="bg-brand-orange hover:bg-orange-600 text-white px-10 py-6 rounded-full text-xl font-bold shadow-2xl shadow-orange-900/30 w-full sm:w-auto">
                      GET PRICE NOW <ArrowRight className="ml-3" size={24} />
                    </Button>
                  </Link>

                  <Link href="/contact" passHref>
                    {/* Visual Impact Update: White Outline Button */}
                    <Button className="bg-transparent border-2 border-slate-600 text-white hover:bg-white hover:text-slate-900 hover:border-white px-10 py-6 rounded-full text-xl font-bold w-full sm:w-auto transition-all duration-300 flex items-center justify-center gap-3">
                      <Phone className="text-brand-orange" size={24} /> (555) 123-4567
                    </Button>
                  </Link>
                </div>

                <p className="text-slate-500 text-base font-medium flex items-center justify-center lg:justify-start gap-6">
                  <span>✓ Upfront Pricing</span>
                  <span>✓ Fully Insured</span>
                </p>
              </div>

              {/* Right Column: Image */}
              <div className="relative h-full min-h-[500px] lg:min-h-full bg-slate-800 w-full">
                <img
                  src="https://placehold.co/800x800/png?text=Truck+And+Team"
                  alt="CleanSweep Team and Truck"
                  className="w-full h-full object-cover"
                />
              </div>
            </div>
          </div>
        </section>

        {/* SECTION 2: THE PROCESS */}
        <section className="py-32 px-4 sm:px-6 lg:px-8 bg-white">
          <div className="max-w-7xl mx-auto">
            <div className="text-center mb-20">
              <h2 className="text-4xl lg:text-5xl font-extrabold text-slate-900 mb-6">SIMPLE 3-STEP PROCESS</h2>
              <p className="text-xl text-slate-500 max-w-3xl mx-auto">No stress, no mess. Here is how we get the job done efficiently.</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-16 text-center">
              <div className="flex flex-col items-center group">
                <div className="w-24 h-24 bg-orange-50 rounded-3xl flex items-center justify-center text-brand-orange mb-8 group-hover:scale-110 transition-transform duration-300">
                  <Calendar size={56} />
                </div>
                <h3 className="text-2xl font-bold text-slate-900 mb-4">Book Online</h3>
                <p className="text-lg text-slate-500 leading-relaxed max-w-sm">Schedule a no-obligation onsite estimate in seconds.</p>
              </div>

              <div className="flex flex-col items-center group">
                <div className="w-24 h-24 bg-orange-50 rounded-3xl flex items-center justify-center text-brand-orange mb-8 group-hover:scale-110 transition-transform duration-300">
                  <Truck size={56} />
                </div>
                <h3 className="text-2xl font-bold text-slate-900 mb-4">We Load It</h3>
                <p className="text-lg text-slate-500 leading-relaxed max-w-sm">Our friendly, uniformed team arrives and does the heavy lifting.</p>
              </div>

              <div className="flex flex-col items-center group">
                <div className="w-24 h-24 bg-orange-50 rounded-3xl flex items-center justify-center text-brand-orange mb-8 group-hover:scale-110 transition-transform duration-300">
                  <Sparkles size={56} />
                </div>
                <h3 className="text-2xl font-bold text-slate-900 mb-4">It's Gone!</h3>
                <p className="text-lg text-slate-500 leading-relaxed max-w-sm">We haul it away to be responsibly disposed of and recycled.</p>
              </div>
            </div>
          </div>
        </section>

        {/* SECTION 3: OUR SERVICES */}
        <section className="py-32 px-4 sm:px-6 lg:px-8 bg-slate-50 border-t border-slate-200">
          <div className="max-w-7xl mx-auto">
            {/* Centered Services Header */}
            <div className="text-center mb-20">
              <h2 className="text-4xl lg:text-5xl font-extrabold text-slate-900 mb-6">OUR SERVICES</h2>
              <Link href="/services" className="text-brand-orange font-bold text-xl inline-flex items-center hover:text-orange-600 transition-colors">
                View full item list <ArrowRight size={24} className="ml-2" />
              </Link>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
              {/* Service Cards - Increased icon size and padding */}
              {[
                { icon: Sofa, title: "Furniture Removal", desc: "Sofas, mattresses, tables, chairs, and more." },
                { icon: Tv, title: "Appliance Disposal", desc: "Fridges, washers, dryers, and old electronics." },
                { icon: Shovel, title: "Yard Waste", desc: "Branches, clippings, stumps, and landscaping debris." },
                { icon: Hammer, title: "Construction Debris", desc: "Drywall, lumber, tile, and renovation waste." },
                { icon: Trash2, title: "Cleanouts", desc: "Garages, basements, attics, and whole-house cleanouts." },
                { icon: Recycle, title: "E-Waste Recycling", desc: "Computers, printers, monitors, and tvs." },
              ].map((service, idx) => (
                <div key={idx} className="bg-white p-10 rounded-2xl shadow-sm hover:shadow-lg transition-all flex flex-col items-center text-center gap-6 group hover:-translate-y-1">
                  <div className="text-brand-orange p-4 bg-orange-50 rounded-full group-hover:bg-brand-orange group-hover:text-white transition-colors">
                    <service.icon size={40} />
                  </div>
                  <div>
                    <h3 className="text-2xl font-bold text-slate-900 mb-3">{service.title}</h3>
                    <p className="text-lg text-slate-500">{service.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* SECTION 4: FEATURES BANNER */}
        <section className="py-24 px-4 bg-white border-y border-slate-100">
          <div className="max-w-7xl mx-auto">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-12">
              {[
                { icon: Wallet, title: "Upfront Pricing", desc: "No hidden fees. Firm quote." },
                { icon: Clock, title: "Fast Service", desc: "Same-day/Next-day available." },
                { icon: ShieldCheck, title: "Fully Insured", desc: "Your property is protected." },
                { icon: Recycle, title: "Eco-Friendly", desc: "We recycle up to 60%." },
              ].map((feature, idx) => (
                <div key={idx} className="flex flex-col items-center text-center gap-4">
                  <div className="w-20 h-20 rounded-full bg-slate-900 flex items-center justify-center text-white flex-shrink-0 shadow-lg">
                    <feature.icon size={40} />
                  </div>
                  <div>
                    <h4 className="text-xl font-bold text-slate-900 mb-1">{feature.title}</h4>
                    <p className="text-base text-slate-500">{feature.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* SECTION 5: TESTIMONIALS */}
        <section className="py-32 px-4 sm:px-6 lg:px-8 bg-slate-900">
          <div className="max-w-7xl mx-auto">
            <h2 className="text-4xl lg:text-5xl font-extrabold text-white text-center mb-20 uppercase tracking-wide">What Our Neighbors Say</h2>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-10">
              {/* Testimonial 1 */}
              <div className="bg-slate-800 p-10 rounded-3xl border border-slate-700">
                <div className="flex text-brand-orange mb-8">
                  {[1, 2, 3, 4, 5].map(i => <Star key={i} size={24} fill="currentColor" className="mr-1" />)}
                </div>
                <p className="text-slate-300 mb-8 italic leading-relaxed text-xl">"The crew was incredibly polite and fast. They cleared out my entire garage in less than an hour. Price was exactly what they quoted."</p>
                <div>
                  <p className="text-white font-bold text-lg">Sarah Jenkins</p>
                  <p className="text-slate-500">Homeowner</p>
                </div>
              </div>

              {/* Testimonial 2 */}
              <div className="bg-slate-800 p-10 rounded-3xl border border-slate-700">
                <div className="flex text-brand-orange mb-8">
                  {[1, 2, 3, 4, 5].map(i => <Star key={i} size={24} fill="currentColor" className="mr-1" />)}
                </div>
                <p className="text-slate-300 mb-8 italic leading-relaxed text-xl">"Best experience I've had with a service company. The online booking was easy, and the AI quote was surprisingly accurate."</p>
                <div>
                  <p className="text-white font-bold text-lg">Mike Ross</p>
                  <p className="text-slate-500">Small Business Owner</p>
                </div>
              </div>

              {/* Testimonial 3 */}
              <div className="bg-slate-800 p-10 rounded-3xl border border-slate-700">
                <div className="flex text-brand-orange mb-8">
                  {[1, 2, 3, 4, 5].map(i => <Star key={i} size={24} fill="currentColor" className="mr-1" />)}
                </div>
                <p className="text-slate-300 mb-8 italic leading-relaxed text-xl">"I love that they recycle. It felt good knowing my old furniture wasn't just going straight to a landfill. Highly recommend!"</p>
                <div>
                  <p className="text-white font-bold text-lg">Emily Chen</p>
                  <p className="text-slate-500">Homeowner</p>
                </div>
              </div>
            </div>
          </div>
        </section>

      </main>
      <Footer />
    </div>
  );
}
