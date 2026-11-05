import { pageMetadata } from "@/components/business/pageMetadata";

import { ReturnVisitsScreen } from "./ReturnVisitsScreen";

export const generateMetadata = pageMetadata("bookings/return-visits");

/** Bookings → Return visits (owners): the message that brings customers back. */
export default function ReturnVisitsPage() {
  return <ReturnVisitsScreen />;
}
