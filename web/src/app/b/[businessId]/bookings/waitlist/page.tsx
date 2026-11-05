import { pageMetadata } from "@/components/business/pageMetadata";

import { isWaitlistFilter } from "./_lib/waitlistModel";
import { WaitlistScreen } from "./WaitlistScreen";

export const generateMetadata = pageMetadata("bookings/waitlist");

/** Bookings → Waitlist; `?filter=booked|ended` opens another list than the waiting customers. */
export default async function WaitlistPage({ searchParams }: PageProps<"/b/[businessId]/bookings/waitlist">) {
  const { filter } = await searchParams;
  return <WaitlistScreen initialFilter={typeof filter === "string" && isWaitlistFilter(filter) ? filter : "active"} />;
}
