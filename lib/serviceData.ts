export interface ServiceFAQ {
    question: string;
    answer: string;
}

export interface ServiceData {
    slug: string;
    title: string;
    metaTitle: string;
    metaDescription: string;
    heroTitle: string;
    heroHighlight: string;
    heroDescription: string;
    content: string[];
    items: string[];
    faqs: ServiceFAQ[];
}

export const services: ServiceData[] = [
    {
        slug: 'furniture-removal',
        title: 'Furniture Removal',
        metaTitle: 'Furniture Removal in Houston, TX | Same-Day Pickup',
        metaDescription: 'Professional furniture removal in Houston. We haul sofas, tables, dressers, mattresses, and more. Same-day service, upfront pricing, eco-friendly disposal.',
        heroTitle: 'Furniture Removal in',
        heroHighlight: 'Houston',
        heroDescription: 'Heavy couch? Oversized dresser? We handle it all — from walkups to tight hallways. No item is too bulky for our trained two-person crews.',
        content: [
            'Whether you\'re upgrading your living room or clearing out a rental property, old furniture is one of the hardest things to get rid of on your own. Most curbside programs won\'t take it, and hauling a sofa to the dump requires a truck you probably don\'t own.',
            'Clean Sweep specializes in full-service furniture removal across the Greater Houston area. Our crews arrive on time, do all the heavy lifting, and carefully navigate tight doorways, staircases, and elevators — without scratching your walls or floors.',
            'We remove sofas, loveseats, dining sets, dressers, bookshelves, desks, bed frames, and more. Items in good condition are donated to local Houston charities like the Salvation Army and Habitat for Humanity ReStore. Everything else is recycled or disposed of responsibly.',
            'Our volume-based pricing means you only pay for the truck space your furniture uses. No hidden fees, no surprises. Get a guaranteed price before we start — snap a photo and we\'ll quote you instantly.',
        ],
        items: ['Sofas & Loveseats', 'Dining Tables & Chairs', 'Dressers & Wardrobes', 'Bookshelves & Cabinets', 'Office Desks & Chairs', 'Bed Frames & Headboards', 'Entertainment Centers', 'Patio Furniture'],
        faqs: [
            { question: 'Do you disassemble furniture?', answer: 'Yes, if needed. Our crew will break down bed frames, large shelving units, and sectional sofas to safely remove them from your home.' },
            { question: 'Will you donate my furniture?', answer: 'Absolutely. Items in good condition are donated to local Houston-area charities. We provide donation receipts when available.' },
            { question: 'Can you remove furniture from upstairs?', answer: 'Yes. Our two-person crews are trained to safely navigate staircases, tight hallways, and elevators without damaging your property.' },
        ],
    },
    {
        slug: 'appliance-recycling',
        title: 'Appliance Recycling',
        metaTitle: 'Appliance Removal & Recycling in Houston, TX',
        metaDescription: 'Safe, eco-friendly appliance removal in Houston. We haul refrigerators, washers, dryers, ovens, and more. Proper freon extraction and certified recycling.',
        heroTitle: 'Appliance Recycling in',
        heroHighlight: 'Houston',
        heroDescription: 'Old fridge taking up space? We handle safe removal, freon extraction, and certified recycling — so you don\'t have to worry about hazardous materials.',
        content: [
            'Disposing of old appliances isn\'t as simple as rolling them to the curb. Refrigerators contain freon, washers have heavy motors, and dryers have gas connections that require proper disconnection. Houston waste management won\'t pick them up without an appointment — and even then, you\'re responsible for getting them to the curb.',
            'Clean Sweep handles the entire process. We disconnect, remove, and transport your old appliances to certified recycling facilities in the Houston area. Hazardous refrigerants like freon are extracted by EPA-certified technicians before the metal is scrapped and recycled.',
            'We remove refrigerators, freezers, washers, dryers, dishwashers, stoves, ovens, microwaves, window AC units, and water heaters. Whether you\'re upgrading to new appliances or clearing out a property, we make the old ones vanish.',
            'Our crews handle all the heavy lifting — including navigating narrow Houston laundry rooms, garages, and basement stairs. Same-day service is available for most appliance pickups.',
        ],
        items: ['Refrigerators & Freezers', 'Washers & Dryers', 'Stoves & Ovens', 'Dishwashers', 'Microwaves', 'Window AC Units', 'Water Heaters', 'Commercial Kitchen Equipment'],
        faqs: [
            { question: 'Do you handle freon removal?', answer: 'Yes. All refrigerants are extracted by EPA-certified technicians at our partner recycling facilities before appliances are scrapped.' },
            { question: 'Can you disconnect my old appliance?', answer: 'We can disconnect standard electric and water connections. For gas appliances, we recommend having your gas company disconnect the line before our arrival.' },
            { question: 'How much does appliance removal cost?', answer: 'Our pricing is volume-based. A single appliance typically costs between $75-$150 depending on size and location. Upload a photo for an instant quote.' },
        ],
    },
    {
        slug: 'e-waste-disposal',
        title: 'E-Waste Disposal',
        metaTitle: 'E-Waste Disposal & Electronics Recycling in Houston, TX',
        metaDescription: 'Secure, eco-friendly e-waste disposal in Houston. Computers, monitors, TVs, printers, and more. Data privacy respected, certified recycling partners.',
        heroTitle: 'E-Waste Disposal in',
        heroHighlight: 'Houston',
        heroDescription: 'From old monitors to entire server rooms — we handle secure, certified electronic waste disposal with full data privacy protection.',
        content: [
            'Electronic waste is one of the fastest-growing waste streams in the world, and Houston generates its fair share. Old computers, monitors, TVs, printers, and cables can\'t go in the trash — they contain lead, mercury, and other hazardous materials that require specialized handling.',
            'Clean Sweep partners with R2-certified e-waste recycling facilities in the Houston area to ensure your electronics are processed responsibly. Valuable materials like copper, gold, and rare earth metals are recovered, while toxic components are safely contained.',
            'We understand data privacy matters. Hard drives and storage devices are handled with care and can be physically destroyed upon request. Whether you\'re upgrading your home office or decommissioning a corporate IT setup, we provide secure chain-of-custody documentation.',
            'Our service covers everything from a box of old cables to a full office of workstations. We serve residential customers in neighborhoods like The Heights and River Oaks, as well as commercial clients across the Houston metro.',
        ],
        items: ['Desktop Computers & Laptops', 'Monitors & TVs (all sizes)', 'Printers & Scanners', 'Servers & Networking Equipment', 'Cables & Peripherals', 'Stereos & Speakers', 'Gaming Consoles', 'Phones & Tablets'],
        faqs: [
            { question: 'Is my data safe?', answer: 'Yes. We partner with certified facilities that follow NIST data destruction guidelines. Physical drive destruction is available on request.' },
            { question: 'Do you take old TVs?', answer: 'Yes, we accept all TV types including CRT, LCD, LED, and plasma. CRT TVs contain lead and require special recycling — we handle that.' },
            { question: 'Can you clear out an entire office?', answer: 'Absolutely. We handle commercial e-waste cleanouts of any size, from a few desks to full server rooms. Contact us for bulk pricing.' },
        ],
    },
    {
        slug: 'construction-debris',
        title: 'Construction Debris Removal',
        metaTitle: 'Construction Debris Removal in Houston, TX | Job Site Cleanup',
        metaDescription: 'Fast construction debris removal in Houston. Drywall, lumber, tile, roofing, and renovation waste. Same-day cleanup for contractors and homeowners.',
        heroTitle: 'Construction Debris Removal in',
        heroHighlight: 'Houston',
        heroDescription: 'Renovation mess? Job site overflowing? We clear drywall, lumber, tile, and roofing materials fast — so your project stays on schedule.',
        content: [
            'Houston\'s booming construction and renovation market generates mountains of debris. Whether you\'re a DIY homeowner remodeling a bathroom in Katy or a general contractor managing a multi-unit build in Midtown, construction waste piles up fast and slows everything down.',
            'Clean Sweep provides fast, reliable construction debris removal across the Greater Houston area. We handle drywall, plaster, wood scraps, lumber, tile, ceramics, roofing shingles, windows, glass, concrete, and general renovation waste. We arrive with trucks large enough to clear your site in a single trip.',
            'For contractors, we offer recurring pickup schedules that align with your project timeline. Keep your job site clean and OSHA-compliant without dedicating your crew to waste management. We work around your schedule — early morning, evening, and weekend pickups available.',
            'All construction debris is sorted at certified facilities. Wood and metal are recycled, concrete is crushed for reuse, and only non-recyclable material goes to the landfill. We help Houston builders meet green building requirements and waste diversion goals.',
        ],
        items: ['Drywall & Plaster', 'Wood Scraps & Lumber', 'Tile & Ceramics', 'Roofing Shingles', 'Windows & Glass', 'Concrete & Brick', 'Flooring Materials', 'General Renovation Waste'],
        faqs: [
            { question: 'Do you offer recurring pickups for job sites?', answer: 'Yes. We work with contractors across Houston to set up weekly or bi-weekly pickups that align with your project schedule.' },
            { question: 'Can you handle a full renovation cleanout?', answer: 'Absolutely. We\'ve cleared everything from single-bathroom remodels to full commercial gut-outs. One trip, one team, one price.' },
            { question: 'Do you take concrete and brick?', answer: 'Yes, in reasonable quantities. Very heavy loads (e.g., full driveways) may require special equipment — contact us for a custom quote.' },
        ],
    },
    {
        slug: 'yard-waste',
        title: 'Yard Waste Removal',
        metaTitle: 'Yard Waste Removal in Houston, TX | Storm Debris & Landscaping',
        metaDescription: 'Professional yard waste removal in Houston. Branches, leaves, stumps, fencing, and storm debris. Fast seasonal cleanup and eco-friendly composting.',
        heroTitle: 'Yard Waste Removal in',
        heroHighlight: 'Houston',
        heroDescription: 'Branches piling up? Storm debris everywhere? We clear yards of all sizes — and compost the majority of what we collect.',
        content: [
            'Houston\'s subtropical climate means yards grow fast and storms hit hard. Between hurricane season debris, summer landscaping projects, and the never-ending battle with overgrown trees, yard waste is a year-round challenge for Houston homeowners.',
            'Clean Sweep handles all types of organic yard waste: branches, tree limbs, leaves, grass clippings, mulch, soil, sod, small tree stumps, fencing material, and storm debris. We arrive with tarps and rakes to ensure a clean pickup — not just the big stuff.',
            'After major storms, Houston neighborhoods from The Woodlands to Pearland are often buried in fallen branches and debris. Our crews mobilize quickly with extended hours to help communities recover. We prioritize accessibility — clearing driveways and walkways first.',
            'We compost the vast majority of the yard waste we collect, turning your old branches and clippings into nutrient-rich soil used by local parks, gardens, and farms. It\'s the most environmentally responsible way to handle green waste in the Houston area.',
        ],
        items: ['Tree Branches & Limbs', 'Leaves & Grass Clippings', 'Landscaping Trimmings', 'Mulch & Soil (bagged)', 'Fencing Material', 'Small Tree Stumps', 'Storm Debris', 'Old Garden Structures'],
        faqs: [
            { question: 'Do you handle storm cleanup?', answer: 'Yes. After major Houston storms, we mobilize additional crews with extended hours. Call us for emergency debris removal — we prioritize clearing driveways and walkways.' },
            { question: 'Can you remove tree stumps?', answer: 'We can remove small stumps (under 12 inches). Larger stumps require grinding equipment — we can recommend a local tree service for those.' },
            { question: 'Is yard waste composted?', answer: 'Yes, the vast majority. We deliver green waste to composting facilities rather than landfills wherever possible.' },
        ],
    },
    {
        slug: 'cleanouts',
        title: 'Full Property Cleanouts',
        metaTitle: 'Estate & Property Cleanouts in Houston, TX | Garages, Attics, Basements',
        metaDescription: 'Complete property cleanouts in Houston. Estates, foreclosures, garages, attics, basements, and storage units. Compassionate, efficient, full-service removal.',
        heroTitle: 'Full Property Cleanouts in',
        heroHighlight: 'Houston',
        heroDescription: 'Garage, attic, basement, or entire property — we clear it all. Compassionate, efficient service for estates, moves, and fresh starts.',
        content: [
            'Sometimes you don\'t need a single item removed — you need an entire property cleared. Whether it\'s a parent\'s estate in Memorial, a foreclosure cleanup in Missouri City, or a hoarder situation in Spring, Clean Sweep handles full-scale cleanouts with professionalism and compassion.',
            'Our cleanout service covers every room: garages, attics, basements, bedrooms, kitchens, storage sheds, and outdoor spaces. We sort everything on-site — items in good condition are donated to Houston-area charities, recyclables are separated, and only true waste goes to the landfill.',
            'For estate cleanouts, we understand the emotional weight of the work. Our crews are trained to be patient, respectful, and discreet. We work at your pace and can accommodate family members who want to be present during the process.',
            'We also handle commercial cleanouts for landlords between tenants, storage unit liquidations, and office relocations. From Katy to League City, our trucks cover the entire Houston metro. Most cleanouts are completed in a single day — large properties may require two visits.',
        ],
        items: ['Estate Cleanouts', 'Foreclosure Cleanouts', 'Garage Cleanouts', 'Attic Cleanouts', 'Basement Cleanouts', 'Storage Unit Cleanouts', 'Office Cleanouts', 'Hoarding Situations'],
        faqs: [
            { question: 'How long does a full cleanout take?', answer: 'Most residential cleanouts are completed in 4-8 hours. Larger properties or heavy hoarding situations may require two visits.' },
            { question: 'Do you donate usable items?', answer: 'Yes. We sort on-site and donate furniture, clothing, and household goods to local Houston charities including Goodwill, Salvation Army, and Habitat for Humanity ReStore.' },
            { question: 'Can you handle hoarding situations?', answer: 'Yes, with sensitivity and discretion. Our crews are experienced with hoarding cleanouts and work at a pace that\'s comfortable for the homeowner or family.' },
        ],
    },
];

export function getServiceBySlug(slug: string): ServiceData | undefined {
    return services.find(s => s.slug === slug);
}
