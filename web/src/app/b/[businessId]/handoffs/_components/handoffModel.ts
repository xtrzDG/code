/** Pure rules of the handoffs page: tabs, counts and URL filters. */

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

/** The API's `is_open` filter of a tab (the API orders: urgent and long-waiting first). */
export function isOpenQuery(tab: HandoffTab): "true" | "false" | undefined {
  return tab === "open" ? "true" : tab === "resolved" ? "false" : undefined;
}

/** Tab counts from the page's totals (the status filters aside). */
export function handoffTabCounts(page: { open_count: number; resolved_count: number }): Record<HandoffTab, number> {
  return { open: page.open_count, resolved: page.resolved_count, all: page.open_count + page.resolved_count };
}

/** The shown list after a handoff was resolved: it leaves the "open" tab. */
export function afterResolve<T extends Pick<HandoffListItem, "id">>(handoffs: readonly T[], resolved: T, tab: HandoffTab): T[] {
  return handoffs
    .map((handoff) => (handoff.id === resolved.id ? resolved : handoff))
    .filter((handoff) => tab !== "open" || handoff.id !== resolved.id);
}

/** Totals after one open handoff was resolved. */
export function withResolvedCounts<Page extends { open_count: number; resolved_count: number }>(page: Page): Page {
  return { ...page, open_count: Math.max(0, page.open_count - 1), resolved_count: page.resolved_count + 1 };
}
