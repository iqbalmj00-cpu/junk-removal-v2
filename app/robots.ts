import { MetadataRoute } from 'next';

export default function robots(): MetadataRoute.Robots {
    return {
        rules: {
            userAgent: '*',
            allow: '/',
            disallow: ['/api/', '/booking-details', '/booking-confirmed'],
        },
        sitemap: 'https://jamals-junk-v2.vercel.app/sitemap.xml',
    };
}
