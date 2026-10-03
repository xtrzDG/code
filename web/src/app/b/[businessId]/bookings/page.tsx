import { pageMetadata } from "@/components/business/pageMetadata";

import { parseBookingFilters } from "./_lib/bookingFilters";
import { BookingsScreen } from "./BookingsScreen";

export const generateMetadata = pageMetadata("bookings");

/** Bookings; filters come from the URL (`?range=week&status=pending&resource=…`). */
export default async function BookingsPage({ searchParams }: PageProps<"/b/[businessId]/bookings">) {
  return <BookingsScreen initialFilters={parseBookingFilters(await searchParams)} />;
}
