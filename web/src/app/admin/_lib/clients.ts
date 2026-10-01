/**
 * Pure helpers of the platform admin pages: health badges, filtering,
 * sorting and the summary of all clients.
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

const HEALTH_RANK: Record<ClientHealthStatus, number> = { critical: 0, attention: 1, healthy: 2 };

/** Issues that make a client critical: the assistant is limited or loses money (ClientHealthIssue in the API). */
const CRITICAL_ISSUES: ReadonlySet<ClientHealthIssue> = new Set(["leads_only_mode", "negative_margin"]);

export function isCriticalIssue(issue: ClientHealthIssue): boolean {
  return CRITICAL_ISSUES.has(issue);
}

export interface ClientFilters {
  query: string;
  health: ClientHealthStatus | "";
  status: BusinessStatus | "";
}

export const EMPTY_FILTERS: ClientFilters = { query: "", health: "", status: "" };

export function hasFilters(filters: ClientFilters): boolean {
  return filters.query.trim() !== "" || filters.health !== "" || filters.status !== "";
}

export function filterClients(clients: readonly AdminClientSummary[], filters: ClientFilters): AdminClientSummary[] {
  const needle = filters.query.trim().toLocaleLowerCase();
  return clients.filter(
    (client) =>
      (needle === "" ||
        client.name.toLocaleLowerCase().includes(needle) ||
        client.business_id.toLocaleLowerCase().includes(needle)) &&
      (filters.health === "" || client.health_status === filters.health) &&
      (filters.status === "" || client.business_status === filters.status),
  );
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

export const CLIENT_SORTS = ["health", "name", "usage", "margin", "cost", "revenue"] as const;
export type ClientSort = (typeof CLIENT_SORTS)[number];

function compareNullable(left: number | null | undefined, right: number | null | undefined, direction: 1 | -1): number {
  const leftMissing = left === null || left === undefined;
  const rightMissing = right === null || right === undefined;
  if (leftMissing || rightMissing) {
    // Unknown values always go last.
    return leftMissing === rightMissing ? 0 : leftMissing ? 1 : -1;
  }
  return (left - right) * direction;
}

/**
 * Sort a copy: health (critical first), name, usage (fullest first),
 * margin (lowest first), provider cost and revenue (largest first). Ties
 * keep health order, then name.
 */
export function sortClients(clients: readonly AdminClientSummary[], sort: ClientSort, locale: string): AdminClientSummary[] {
  const byName = (left: AdminClientSummary, right: AdminClientSummary) => left.name.localeCompare(right.name, locale);
  const byHealth = (left: AdminClientSummary, right: AdminClientSummary) =>
    HEALTH_RANK[left.health_status] - HEALTH_RANK[right.health_status] ||
    (right.health_issues ?? []).length - (left.health_issues ?? []).length;
  const comparators: Record<ClientSort, (left: AdminClientSummary, right: AdminClientSummary) => number> = {
    health: byHealth,
    name: byName,
    usage: (left, right) => compareNullable(clientUsagePercent(left), clientUsagePercent(right), -1),
    margin: (left, right) => compareNullable(left.cost.margin_percent, right.cost.margin_percent, 1),
    cost: (left, right) => compareNullable(left.cost.provider_cost_micro_usd, right.cost.provider_cost_micro_usd, -1),
    revenue: (left, right) =>
      left.cost.revenue.currency_code === right.cost.revenue.currency_code
        ? compareNullable(left.cost.revenue.amount_minor, right.cost.revenue.amount_minor, -1)
        : left.cost.revenue.currency_code.localeCompare(right.cost.revenue.currency_code),
  };
  return [...clients].sort((left, right) => comparators[sort](left, right) || byHealth(left, right) || byName(left, right));
}

export interface ClientsSummary {
  total: number;
  critical: number;
  attention: number;
  healthy: number;
  losingMoney: number;
}

export function summarizeClients(clients: readonly AdminClientSummary[]): ClientsSummary {
  return {
    total: clients.length,
    critical: clients.filter((client) => client.health_status === "critical").length,
    attention: clients.filter((client) => client.health_status === "attention").length,
    healthy: clients.filter((client) => client.health_status === "healthy").length,
    losingMoney: clients.filter((client) => (client.cost.margin?.amount_minor ?? 0) < 0).length,
  };
}

/** "/admin/clients/{id}" */
export function adminClientPath(businessId: string): string {
  return `/admin/clients/${encodeURIComponent(businessId)}`;
}
