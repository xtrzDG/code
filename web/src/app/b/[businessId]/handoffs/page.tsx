import { sectionMetadata } from "@/components/business/SectionPlaceholder";

import { parseHandoffFilters } from "./_components/handoffModel";
import { HandoffsScreen } from "./HandoffsScreen";

export const generateMetadata = sectionMetadata("handoffs");

/** Handoffs; open ones by default, `?tab=resolved|all`, `&test=1` for test activity. */
export default async function HandoffsPage({ searchParams }: PageProps<"/b/[businessId]/handoffs">) {
  return <HandoffsScreen initialFilters={parseHandoffFilters(await searchParams)} />;
}
