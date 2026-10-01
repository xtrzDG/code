/**
 * Pure helpers of the platform admin pages: health badges, the list query
 * (filters and sorting run on the server) and links.
 */

import type { Schema } from "@/api/types";
import type { BadgeTone } from "@/components/ui";
import { usagePercent } from "@/components/workspace/helpers";

export type AdminClientSummary = Schema<"AdminClientSummary">;
export type ClientHealthStatus = Schema<"ClientHealthStatus">;
export type ClientHealthIssue = Schema<"ClientHealthIssue">;
export type BusinessStatus = Schema<"BusinessStatus">;

export const HEALTH_TONES: Record<ClientHealthStatus, BadgeTone> = {
  healthy: "success",
  attention: "warning",
  critical: "danger",
};

/** Issues that make a client critical: the assistant is limited or loses money (ClientHealthIssue in the API). */
const CRITICAL_ISSUES: ReadonlySet<ClientHealthIssue> = new Set(["leads_only_mode", "negative_margin"]);

export function isCriticalIssue(issue: ClientHealthIssue): boolean {
  return CRITICAL_ISSUES.has(issue);
}

export type AdminClientPage = Schema<"AdminClientPage">;
export type NicheKey = Schema<"NicheKey">;

export interface ClientFilters {
  query: string;
  health: ClientHealthStatus | "";
  status: BusinessStatus | "";
  country: string;
  niche: NicheKey | "";
}

export const EMPTY_FILTERS: ClientFilters = { query: "", health: "", status: "", country: "", niche: "" };

export const ADMIN_PAGE_SIZE = 25;

export function hasFilters(filters: ClientFilters): boolean {
  return (
    filters.query.trim() !== "" || filters.health !== "" || filters.status !== "" || filters.country !== "" || filters.niche !== ""
  );
}

/** The query of GET /v1/admin/clients: only the filters that are set. */
export function clientsQuery(
  filters: ClientFilters,
  search: string | undefined,
  sort: ClientSort,
): {
  search?: string;
  health?: ClientHealthStatus;
  status?: BusinessStatus;
  country?: string;
  niche?: NicheKey;
  sort: ClientSort;
} {
  return {
    ...(search ? { search } : {}),
    ...(filters.health ? { health: filters.health } : {}),
    ...(filters.status ? { status: filters.status } : {}),
    ...(filters.country ? { country: filters.country } : {}),
    ...(filters.niche ? { niche: filters.niche } : {}),
    sort,
  };
}

/** The fuller of the two packages (voice minutes, dialogs) in whole percent, or null. */
export function clientUsagePercent(client: AdminClientSummary): number | null {
  const voice = usagePercent(client.used_voice_minutes, client.included_voice_minutes);
  const dialogs = usagePercent(client.used_dialogs, client.included_dialogs);
  if (voice === null && dialogs === null) {
    return null;
  }
  return Math.max(voice ?? 0, dialogs ?? 0);
}

/** Orders of GET /v1/admin/clients?sort= (AdminClientSort in the API). */
export const CLIENT_SORTS = ["health", "name", "usage", "margin", "cost", "revenue"] as const;
export type ClientSort = (typeof CLIENT_SORTS)[number];

/** "/admin/clients/{id}" */
export function adminClientPath(businessId: string): string {
  return `/admin/clients/${encodeURIComponent(businessId)}`;
}
