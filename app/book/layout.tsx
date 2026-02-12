import { Metadata } from 'next';

export const metadata: Metadata = {
    title: 'Book Your Junk Removal | Clean Sweep Houston',
    description: 'Upload a photo of your junk and get an instant quote. Book your pickup in minutes with Clean Sweep Junk Removal Houston.',
};

export default function BookLayout({ children }: { children: React.ReactNode }) {
    return <>{children}</>;
}
