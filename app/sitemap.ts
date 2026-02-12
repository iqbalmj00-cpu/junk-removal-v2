import { MetadataRoute } from 'next';
import { services } from '@/lib/serviceData';
import { locations } from '@/lib/locationData';

export default function sitemap(): MetadataRoute.Sitemap {
    const base = 'https://jamals-junk-v2.vercel.app';

    const staticPages = [
        '',
        '/services',
        '/locations',
        '/about',
        '/contact',
        '/how-it-works',
        '/reviews',
        '/faq',
        '/blog',
        '/get-started',
        '/items-we-take',
        '/items-we-dont-take',
        '/commercial',
        '/legal',
    ];

    const servicePages = services.map((s) => `/services/${s.slug}`);
    const locationPages = locations.map((l) => `/locations/${l.slug}`);

    const allPaths = [...staticPages, ...servicePages, ...locationPages];

    return allPaths.map((path) => ({
        url: `${base}${path}`,
        lastModified: new Date(),
        changeFrequency: path === '' ? 'daily' as const : 'weekly' as const,
        priority: path === '' ? 1 : path.startsWith('/services') ? 0.9 : 0.8,
    }));
}
