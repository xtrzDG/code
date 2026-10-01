/** Pure rules of the leads page: tabs with counts and URL filters. */

import { LEAD_STATUSES } from "@/components/insights/labels";
import type { LeadListItem, LeadStatus } from "@/components/insights/types";

export type LeadTab = LeadStatus | "all";

export interface LeadFilters {
  tab: LeadTab;
  includeTest: boolean;
}

type SearchParams = Record<string, string | string[] | undefined>;

export function parseLeadFilters(params: SearchParams): LeadFilters {
  const status = params.status;
  return {
    tab: typeof status === "string" && (LEAD_STATUSES as readonly string[]).includes(status) ? (status as LeadStatus) : "all",
    includeTest: params.test === "1",
  };
}

export function leadFiltersQuery(filters: LeadFilters): string {
  const params = new URLSearchParams();
  if (filters.tab !== "all") params.set("status", filters.tab);
  if (filters.includeTest) params.set("test", "1");
  return params.toString();
}

/** How many leads each tab holds, from the API's counts (the status filter aside). */
export function countsByTab(statusCounts: readonly { status: LeadStatus; count: number }[]): Record<LeadTab, number> {
  const counts: Record<LeadTab, number> = { all: 0, new: 0, in_progress: 0, won: 0, lost: 0 };
  for (const entry of statusCounts) {
    counts[entry.status] = entry.count;
    counts.all += entry.count;
  }
  return counts;
}

/** The counts after one lead moved from one status to another. */
export function withStatusCounts<Page extends { status_counts?: { status: LeadStatus; count: number }[] }>(
  page: Page,
  from: LeadStatus,
  to: LeadStatus,
): Page {
  if (from === to) {
    return page;
  }
  return {
    ...page,
    status_counts: (page.status_counts ?? []).map((entry) =>
      entry.status === from
        ? { ...entry, count: Math.max(0, entry.count - 1) }
        : entry.status === to
          ? { ...entry, count: entry.count + 1 }
          : entry,
    ),
  };
}

/**
 * The shown list after a status change (only the status comes back from
 * PATCH): the lead leaves a tab of another status.
 */
export function afterStatusChange<T extends Pick<LeadListItem, "id" | "status">>(
  leads: readonly T[],
  id: string,
  status: LeadStatus,
  tab: LeadTab,
): T[] {
  return leads
    .map((lead) => (lead.id === id ? { ...lead, status } : lead))
    .filter((lead) => lead.id !== id || tab === "all" || lead.status === tab);
}
