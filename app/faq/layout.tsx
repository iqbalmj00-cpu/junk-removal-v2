import { Metadata } from 'next';

export const metadata: Metadata = {
    title: 'FAQ | Clean Sweep Junk Removal Houston',
    description: 'Answers to common questions about junk removal in Houston. Pricing, scheduling, what we take, donation policy, and more.',
};

export default function FaqLayout({ children }: { children: React.ReactNode }) {
    return <>{children}</>;
}
