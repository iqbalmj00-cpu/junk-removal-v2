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
        slug: 'appliance-removal',
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
        slug: 'e-waste-recycling',
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
        slug: 'construction-debris-removal',
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
        slug: 'yard-waste-removal',
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
        slug: 'estate-cleanout',
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
    {
        slug: 'mattress-disposal',
        title: 'Mattress Disposal',
        metaTitle: 'Mattress Disposal & Removal in Houston, TX | Same-Day Pickup',
        metaDescription: 'Professional mattress removal in Houston. King, queen, twin, box springs — we haul them all. Same-day pickup, donation when possible, eco-friendly disposal.',
        heroTitle: 'Mattress Disposal in',
        heroHighlight: 'Houston',
        heroDescription: 'Old mattress taking up space? We pick up mattresses and box springs of any size — with same-day service and responsible disposal.',
        content: [
            'Getting rid of a mattress in Houston is harder than it should be. Curbside pickup won\'t take them, they don\'t fit in your car, and donation centers have strict cleanliness requirements. Clean Sweep makes mattress disposal effortless.',
            'We pick up all mattress sizes — king, queen, full, twin, and California king — plus box springs, mattress toppers, and adjustable bed frames. Our crew handles all the heavy lifting, including navigating tight hallways and staircases.',
            'Mattresses in good condition are donated to local shelters and charities. Others are taken to certified recycling facilities where the steel springs, foam, cotton, and fabric are separated and repurposed.',
        ],
        items: ['King Mattresses', 'Queen Mattresses', 'Twin & Full Mattresses', 'Box Springs', 'Mattress Toppers', 'Adjustable Bed Frames', 'Futon Mattresses', 'Crib Mattresses'],
        faqs: [
            { question: 'Can you remove a mattress from upstairs?', answer: 'Yes. Our two-person crew handles staircases, narrow hallways, and tight turns — no extra charge for stairs.' },
            { question: 'Do you take the box spring too?', answer: 'Absolutely. We take mattresses and box springs together or separately.' },
            { question: 'How much does mattress removal cost?', answer: 'A single mattress starts around $75-$100. Upload a photo for an exact quote.' },
        ],
    },
    {
        slug: 'garage-cleanout',
        title: 'Garage Cleanout',
        metaTitle: 'Garage Cleanout Services in Houston, TX | Full Garage Clearing',
        metaDescription: 'Professional garage cleanout in Houston. We clear years of accumulated stuff — tools, furniture, boxes, and more. Take back your garage today.',
        heroTitle: 'Garage Cleanout in',
        heroHighlight: 'Houston',
        heroDescription: 'Can\'t park in your garage anymore? We clear decades of accumulated clutter so you can use your space again.',
        content: [
            'Houston garages have a way of becoming storage units. Over the years, holiday decorations, old furniture, broken tools, and forgotten boxes pile up until there\'s no room left for your car. Clean Sweep helps you reclaim that space.',
            'Our garage cleanout service is comprehensive — we remove everything you point to. Furniture, appliances, boxes, sporting goods, lawn equipment, paint cans (dried only), and general clutter. We sort on-site, donating usable items and recycling what we can.',
            'Most single-car garage cleanouts are completed in 2-3 hours. Double garages or heavily packed spaces may take half a day. Either way, our volume-based pricing means no surprises.',
        ],
        items: ['Old Furniture', 'Storage Boxes', 'Broken Tools & Equipment', 'Sporting Goods', 'Holiday Decorations', 'Lawn & Garden Equipment', 'Paint Cans (dried)', 'General Clutter'],
        faqs: [
            { question: 'How long does a garage cleanout take?', answer: 'A single-car garage typically takes 2-3 hours. Double garages or heavily packed spaces may take 4-6 hours.' },
            { question: 'Do I need to sort everything first?', answer: 'No. Just point to what stays and what goes. Our crew handles all the sorting, loading, and cleanup.' },
            { question: 'Can you take paint cans?', answer: 'We can take dried/empty paint cans. Liquid paint and hazardous chemicals require special disposal — contact your local HHW facility.' },
        ],
    },
    {
        slug: 'hoarder-cleanout',
        title: 'Hoarder Cleanout',
        metaTitle: 'Hoarder Cleanout Services in Houston, TX | Compassionate & Discreet',
        metaDescription: 'Compassionate hoarder cleanout services in Houston. Non-judgmental, discreet, and thorough. We help families and individuals reclaim their homes with respect.',
        heroTitle: 'Hoarder Cleanout in',
        heroHighlight: 'Houston',
        heroDescription: 'Overwhelmed by clutter? We provide respectful, non-judgmental cleanout services — helping you or your loved one reclaim their living space.',
        content: [
            'Hoarding situations require a different approach than standard cleanouts. Clean Sweep crews are trained to work with compassion, patience, and discretion. We understand this is deeply personal and often emotional work.',
            'We work at a pace that\'s comfortable for the homeowner or family. Items of sentimental value are carefully set aside. Usable goods are donated, and the rest is disposed of responsibly. Our goal is to restore safe, livable conditions.',
            'Our service is fully confidential. We use unmarked vehicles and work discreetly. Whether the situation involves one room or an entire property, we have the crew and truck capacity to handle it.',
        ],
        items: ['Accumulated Household Items', 'Old Newspapers & Magazines', 'Clothing & Textiles', 'Broken Furniture', 'Kitchen Clutter', 'Expired Goods', 'General Debris', 'Yard Accumulation'],
        faqs: [
            { question: 'Are your crews trained for hoarding situations?', answer: 'Yes. Our team approaches every hoarding cleanout with patience, empathy, and zero judgment. We work at the homeowner\'s pace.' },
            { question: 'Is the service confidential?', answer: 'Absolutely. We use unmarked vehicles and maintain full discretion throughout the process.' },
            { question: 'Can the homeowner be present?', answer: 'Yes, and we encourage it when possible. We\'ll sort items together so nothing important is accidentally removed.' },
        ],
    },
    {
        slug: 'foreclosure-cleanout',
        title: 'Foreclosure Cleanout',
        metaTitle: 'Foreclosure Cleanout Services in Houston, TX | Fast Property Clearing',
        metaDescription: 'Fast foreclosure cleanout services in Houston. We clear abandoned properties for banks, REO companies, and property managers. Same-day turnaround available.',
        heroTitle: 'Foreclosure Cleanout in',
        heroHighlight: 'Houston',
        heroDescription: 'Need a foreclosed property cleared fast? We handle full cleanouts for banks, REO managers, and investors — ready to list in 24 hours.',
        content: [
            'Foreclosed properties in Houston often come with a mess left behind by previous occupants — furniture, trash, personal belongings, and sometimes hazardous conditions. Banks, REO companies, and property managers need these spaces cleared quickly and completely before they can be listed or sold.',
            'Clean Sweep provides fast-turnaround foreclosure cleanouts across the Greater Houston area. We remove all contents, sweep and clean the property, and haul everything away in a single visit. Most properties are cleared and ready to list within 24 hours.',
            'We work with banks, real estate agents, property management companies, and individual investors. Volume pricing is available for portfolios of multiple properties. Full documentation and before/after photos provided upon request.',
        ],
        items: ['Abandoned Furniture', 'Trash & Debris', 'Personal Belongings', 'Appliances', 'Yard Waste', 'Carpet & Flooring', 'General Contents', 'Outdoor Structures'],
        faqs: [
            { question: 'How fast can you clear a foreclosed property?', answer: 'Most properties are fully cleared within 24 hours. Large homes or severely cluttered properties may take two days.' },
            { question: 'Do you provide before/after documentation?', answer: 'Yes. We photograph the property before and after the cleanout for your records.' },
            { question: 'Do you offer volume pricing for multiple properties?', answer: 'Yes. Banks and property managers with multiple foreclosures can contact us for portfolio pricing.' },
        ],
    },
    {
        slug: 'storage-unit-cleanout',
        title: 'Storage Unit Cleanout',
        metaTitle: 'Storage Unit Cleanout in Houston, TX | Fast Unit Clearing',
        metaDescription: 'Professional storage unit cleanout in Houston. We clear units of any size — stop paying rent on stuff you don\'t need. Same-day service available.',
        heroTitle: 'Storage Unit Cleanout in',
        heroHighlight: 'Houston',
        heroDescription: 'Tired of paying rent on a storage unit full of stuff you don\'t need? We clear it out so you can stop the monthly drain.',
        content: [
            'That storage unit you rented "temporarily" three years ago is costing you $100-$300 every month. Clean Sweep helps Houston-area residents and businesses finally clear out their storage units and stop the financial bleeding.',
            'We handle units of all sizes — from 5x5 lockers to 10x30 warehouse-style units. Our crew loads everything from the unit directly into our truck. Usable items are donated, recyclables are sorted, and the rest is disposed of properly.',
            'We coordinate directly with storage facility managers to ensure smooth access and scheduling. Most units are cleared in under 2 hours. You don\'t even need to be present if you authorize access.',
        ],
        items: ['Stored Furniture', 'Boxes & Bins', 'Seasonal Items', 'Old Electronics', 'Clothing & Textiles', 'Business Inventory', 'Sporting Equipment', 'Miscellaneous Items'],
        faqs: [
            { question: 'Do I need to be there during the cleanout?', answer: 'Not necessarily. If you authorize access with your facility manager, our crew can handle everything without you present.' },
            { question: 'How long does it take?', answer: 'Most units are cleared in 1-2 hours. Very large or tightly packed units may take longer.' },
            { question: 'Can you help me sort what to keep?', answer: 'Yes. If you\'d like to be present, we\'ll go through items with you and set aside anything you want to keep.' },
        ],
    },
    {
        slug: 'hot-tub-removal',
        title: 'Hot Tub Removal',
        metaTitle: 'Hot Tub Removal in Houston, TX | Safe Disconnection & Hauling',
        metaDescription: 'Professional hot tub and spa removal in Houston. We disconnect, disassemble, and haul away your old hot tub. Deck and patio safe. Same-day service.',
        heroTitle: 'Hot Tub Removal in',
        heroHighlight: 'Houston',
        heroDescription: 'Old hot tub taking up your patio? We safely disconnect, disassemble, and haul it away — leaving your outdoor space clean and clear.',
        content: [
            'Hot tubs are a luxury to own but a nightmare to remove. They\'re heavy, awkward, and require electrical and plumbing disconnection before they can be moved. Most Houston homeowners can\'t handle this on their own — and shouldn\'t try.',
            'Clean Sweep\'s hot tub removal service covers the full process: we disconnect electrical and water lines, drain the tub, disassemble it into manageable sections when needed, and haul everything away. The acrylic, wood, and metal components are recycled wherever possible.',
            'Whether your hot tub is on a deck, patio, or recessed into the ground, our experienced crew handles it safely without damaging your property. We serve the entire Greater Houston area with same-day availability.',
        ],
        items: ['Acrylic Hot Tubs', 'Wooden Hot Tubs', 'Portable Spas', 'Swim Spas', 'Hot Tub Covers', 'Hot Tub Steps', 'Associated Plumbing', 'Decking Around Tub'],
        faqs: [
            { question: 'Do you disconnect the electrical and plumbing?', answer: 'We handle standard disconnections. For hardwired 240V connections, we recommend having a licensed electrician disconnect the power before our arrival.' },
            { question: 'Can you remove a hot tub from a deck?', answer: 'Yes. Our crew is experienced with deck-mounted, patio, and recessed hot tubs. We take precautions to protect your deck surface.' },
            { question: 'How much does hot tub removal cost?', answer: 'Typical hot tub removal runs $300-$500 depending on size, location, and accessibility. Contact us for an exact quote.' },
        ],
    },
    {
        slug: 'shed-demolition',
        title: 'Shed Demolition & Removal',
        metaTitle: 'Shed Demolition & Removal in Houston, TX | Full Teardown & Hauling',
        metaDescription: 'Professional shed demolition and removal in Houston. We tear down and haul away old sheds, playsets, and outdoor structures. Clean site guaranteed.',
        heroTitle: 'Shed Demolition in',
        heroHighlight: 'Houston',
        heroDescription: 'Rotting shed in the backyard? We demolish it, haul away every piece, and leave your yard clean — all in one visit.',
        content: [
            'Old storage sheds, workshops, and outdoor structures eventually deteriorate past the point of repair. Houston\'s heat, humidity, and termites take their toll. When it\'s time to tear it down, Clean Sweep handles the full demolition and removal.',
            'We dismantle wood, metal, and vinyl sheds of all sizes. Everything is broken down, loaded into our trucks, and hauled to recycling or disposal facilities. We also remove the concrete pad or foundation blocks if needed.',
            'Beyond sheds, we handle playsets, pergolas, fencing, dog houses, and other yard structures. Our crew leaves your yard clean and ready for whatever comes next — landscaping, a new shed, or just open space.',
        ],
        items: ['Wood Sheds', 'Metal Sheds', 'Vinyl Storage Sheds', 'Playsets & Swing Sets', 'Pergolas & Gazebos', 'Old Fencing', 'Concrete Pads', 'Dog Houses'],
        faqs: [
            { question: 'Do you remove the foundation too?', answer: 'Yes. We can remove concrete blocks, pavers, and small concrete pads. Full slab removal may require additional equipment — contact us for a custom quote.' },
            { question: 'How long does shed demolition take?', answer: 'Most standard sheds are demolished and hauled away in 2-4 hours. Larger or heavily built structures may take a full day.' },
            { question: 'Can you remove a playset?', answer: 'Yes. We dismantle and remove wooden and metal playsets, swing sets, and trampolines.' },
        ],
    },
    {
        slug: 'deck-removal',
        title: 'Deck Removal',
        metaTitle: 'Deck Removal & Demolition in Houston, TX | Safe Teardown & Hauling',
        metaDescription: 'Professional deck removal in Houston. We demolish and haul away old wood and composite decks. Clean removal, responsible disposal, site left clean.',
        heroTitle: 'Deck Removal in',
        heroHighlight: 'Houston',
        heroDescription: 'Unsafe or ugly deck? We tear it down board by board and haul everything away — leaving a clean, level surface.',
        content: [
            'Houston\'s heat and humidity are brutal on outdoor decks. Wood rots, boards warp, and what was once a backyard oasis becomes an eyesore — or worse, a safety hazard. When repair isn\'t worth the cost, Clean Sweep handles the full demolition.',
            'We remove wood and composite decks of all sizes, from small back porches to large multi-level structures. Our crew carefully dismantles the deck boards, railing, stairs, and support posts. We also remove concrete footings when requested.',
            'All wood is sorted for recycling where possible. Nails and hardware are separated, and the site is left clean and level. Whether you\'re rebuilding or just reclaiming yard space, we leave you with a blank canvas.',
        ],
        items: ['Wood Deck Boards', 'Composite Decking', 'Deck Railings', 'Stairs & Steps', 'Support Posts', 'Concrete Footings', 'Attached Pergolas', 'Built-in Benches'],
        faqs: [
            { question: 'Can you remove a deck attached to my house?', answer: 'Yes. We carefully detach the ledger board and flashing from your home\'s exterior without causing damage to your siding.' },
            { question: 'Do you remove the concrete footings?', answer: 'Yes, we can dig out and remove concrete footings. This is included in most deck removal quotes.' },
            { question: 'How much does deck removal cost?', answer: 'Pricing depends on size and complexity. Small decks start around $500, large multi-level decks up to $2,000+. Contact us for an exact quote.' },
        ],
    },
    {
        slug: 'office-furniture-removal',
        title: 'Office Furniture Removal',
        metaTitle: 'Office Furniture Removal in Houston, TX | Commercial Cleanouts',
        metaDescription: 'Professional office furniture removal in Houston. Cubicles, desks, chairs, filing cabinets, and full office cleanouts. Flexible scheduling, minimal disruption.',
        heroTitle: 'Office Furniture Removal in',
        heroHighlight: 'Houston',
        heroDescription: 'Relocating, downsizing, or refreshing your office? We remove cubicles, desks, chairs, and everything else — with minimal disruption to your business.',
        content: [
            'Office moves, downsizes, and renovations generate mountains of bulky furniture that standard waste services won\'t handle. Cubicle panels, conference tables, filing cabinets, and dozens of office chairs can\'t just be left on the curb.',
            'Clean Sweep provides full-service office furniture removal for Houston businesses of all sizes. We work evenings and weekends to minimize disruption to your operations. Our crews disassemble cubicle systems, remove heavy conference tables, and clear entire floors if needed.',
            'Usable office furniture is donated to Houston nonprofits and schools. Metals are recycled, and e-waste is processed separately through certified facilities. We provide donation receipts and waste manifests for your records.',
        ],
        items: ['Office Desks', 'Cubicle Systems', 'Office Chairs', 'Conference Tables', 'Filing Cabinets', 'Bookshelves', 'Reception Furniture', 'Break Room Equipment'],
        faqs: [
            { question: 'Can you work after business hours?', answer: 'Yes. We offer evening and weekend scheduling to minimize disruption. Most office cleanouts are completed overnight or on weekends.' },
            { question: 'Do you disassemble cubicles?', answer: 'Yes. Our crew is experienced with all major cubicle systems and can disassemble them quickly and efficiently.' },
            { question: 'Can you clear an entire floor?', answer: 'Absolutely. We\'ve handled single-office removals to full multi-floor commercial cleanouts. Contact us for a walkthrough and quote.' },
        ],
    },
];

export function getServiceBySlug(slug: string): ServiceData | undefined {
    return services.find(s => s.slug === slug);
}
