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

/** How many leads each tab holds (the whole list is loaded once). */
export function countByStatus(leads: readonly Pick<LeadListItem, "status">[]): Record<LeadTab, number> {
  const counts: Record<LeadTab, number> = { all: leads.length, new: 0, in_progress: 0, won: 0, lost: 0 };
  for (const lead of leads) {
    counts[lead.status] += 1;
  }
  return counts;
}

export function leadsOfTab<T extends Pick<LeadListItem, "status">>(leads: readonly T[], tab: LeadTab): T[] {
  return tab === "all" ? [...leads] : leads.filter((lead) => lead.status === tab);
}

/** The list after a status change: only the status comes back from PATCH. */
export function withLeadStatus<T extends Pick<LeadListItem, "id" | "status">>(leads: readonly T[], id: string, status: LeadStatus): T[] {
  return leads.map((lead) => (lead.id === id ? { ...lead, status } : lead));
}
