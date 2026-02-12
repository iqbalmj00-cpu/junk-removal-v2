import { Metadata } from 'next';

export const metadata: Metadata = {
    title: 'Booking Confirmed | Clean Sweep Junk Removal Houston',
    description: 'Your junk removal booking is confirmed! We\'ll see you at the scheduled time. Clean Sweep Junk Removal Houston.',
};

export default function BookingConfirmedLayout({ children }: { children: React.ReactNode }) {
    return <>{children}</>;
}
