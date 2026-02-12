import { Metadata } from 'next';

export const metadata: Metadata = {
    title: 'Get Started | Free Junk Removal Quote Houston',
    description: 'Get a free junk removal quote in Houston. Enter your details and we\'ll get back to you with an upfront price. Same-day service available.',
};

export default function GetStartedLayout({ children }: { children: React.ReactNode }) {
    return <>{children}</>;
}
