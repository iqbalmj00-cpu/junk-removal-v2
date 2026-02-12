import { Metadata } from 'next';

export const metadata: Metadata = {
    title: 'Legal & Policies | Clean Sweep Junk Removal Houston',
    description: 'Terms of service, privacy policy, and SMS communications policy for Clean Sweep Junk Removal in Houston, TX.',
};

export default function LegalLayout({ children }: { children: React.ReactNode }) {
    return <>{children}</>;
}
