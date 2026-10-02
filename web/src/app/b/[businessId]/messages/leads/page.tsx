import { pageMetadata } from "@/components/business/pageMetadata";

import { parseLeadFilters } from "./_components/leadModel";
import { LeadsScreen } from "./LeadsScreen";

export const generateMetadata = pageMetadata("messages/leads");

/** Leads; `?status=new` opens a tab, `&test=1` includes test activity. */
export default async function LeadsPage({ searchParams }: PageProps<"/b/[businessId]/messages/leads">) {
  return <LeadsScreen initialFilters={parseLeadFilters(await searchParams)} />;
}
