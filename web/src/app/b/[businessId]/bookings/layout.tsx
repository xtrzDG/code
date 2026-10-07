import { SectionFrame } from "@/components/shell/SectionFrame";

/** Bookings: the list (with today's agenda on a phone), the waitlist and (owners) the return visits, under one heading with tabs. */
export default function BookingsLayout({ children }: LayoutProps<"/b/[businessId]/bookings">) {
  return <SectionFrame section="bookings">{children}</SectionFrame>;
}
