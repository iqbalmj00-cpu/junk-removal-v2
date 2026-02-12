import { Metadata } from 'next';

export const metadata: Metadata = {
    title: 'Booking Details | Clean Sweep Junk Removal Houston',
    description: 'Review your junk removal booking details and confirm your pickup with Clean Sweep Houston.',
};

export default function BookingDetailsLayout({ children }: { children: React.ReactNode }) {
    return <>{children}</>;
}
