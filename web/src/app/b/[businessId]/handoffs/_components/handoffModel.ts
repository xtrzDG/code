/** Pure rules of the handoffs page: tabs, counts and URL filters. */

import { isOpenHandoff, sortHandoffs } from "@/components/insights/handoffs";
import type { HandoffListItem } from "@/components/insights/types";

export const HANDOFF_TABS = ["open", "resolved", "all"] as const;
export type HandoffTab = (typeof HANDOFF_TABS)[number];

export interface HandoffFilters {
  tab: HandoffTab;
  includeTest: boolean;
}

type SearchParams = Record<string, string | string[] | undefined>;

export function parseHandoffFilters(params: SearchParams): HandoffFilters {
  const tab = params.tab;
  return {
    tab: typeof tab === "string" && (HANDOFF_TABS as readonly string[]).includes(tab) ? (tab as HandoffTab) : "open",
    includeTest: params.test === "1",
  };
}

export function handoffFiltersQuery(filters: HandoffFilters): string {
  const params = new URLSearchParams();
  if (filters.tab !== "open") params.set("tab", filters.tab);
  if (filters.includeTest) params.set("test", "1");
  return params.toString();
}

export function countHandoffTabs(handoffs: readonly Pick<HandoffListItem, "status">[]): Record<HandoffTab, number> {
  const open = handoffs.filter(isOpenHandoff).length;
  return { open, resolved: handoffs.length - open, all: handoffs.length };
}

/** The handoffs of a tab, open and urgent ones first. */
export function handoffsOfTab<T extends Pick<HandoffListItem, "status" | "urgency" | "created_at" | "resolved_at">>(
  handoffs: readonly T[],
  tab: HandoffTab,
): T[] {
  const selected =
    tab === "all" ? handoffs : handoffs.filter((handoff) => (tab === "open" ? isOpenHandoff(handoff) : !isOpenHandoff(handoff)));
  return sortHandoffs(selected);
}
