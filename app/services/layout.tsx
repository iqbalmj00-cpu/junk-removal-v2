import { Metadata } from 'next';

export const metadata: Metadata = {
    title: 'Our Services | Clean Sweep Junk Removal Houston',
    description: 'Full-service junk removal in Houston. Furniture, appliances, e-waste, yard waste, cleanouts, demolition, and commercial services. Book online today.',
};

export default function ServicesLayout({ children }: { children: React.ReactNode }) {
    return <>{children}</>;
}
