import { pageMetadata } from "@/components/business/pageMetadata";

import { ChannelsScreen } from "./ChannelsScreen";
import { readCalendarReturn } from "./_lib/calendarReturn";

export const generateMetadata = pageMetadata("assistant/channels");

export default async function ChannelsPage({ searchParams }: PageProps<"/b/[businessId]/assistant/channels">) {
  const { calendar, reason } = await searchParams;
  const query = new URLSearchParams();
  if (typeof calendar === "string") {
    query.set("calendar", calendar);
  }
  if (typeof reason === "string") {
    query.set("reason", reason);
  }
  // Google's consent page sends the owner back with ?calendar=…; the screen shows it once.
  return <ChannelsScreen calendarReturn={readCalendarReturn(query.toString())} />;
}
