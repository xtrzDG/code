/** Pure helpers of the Settings page's Audit tab: filters, action tones and actors. */

import type { Schema } from "@/api/types";
import type { BadgeTone } from "@/components/ui";

import { memberLabel, type BusinessMember } from "./team";

export type AuditLogEntry = Schema<"AuditLogEntryView">;
export type AuditAction = Schema<"AuditAction">;

export type AuditLogPage = Schema<"AuditLogPage">;

export const AUDIT_PAGE_SIZE = 50;

export interface AuditFilters {
  action: AuditAction | "";
  entity: string;
  actorId: string;
  /** Business-local days "YYYY-MM-DD" (inclusive), or "". */
  from: string;
  to: string;
}

export const EMPTY_AUDIT_FILTERS: AuditFilters = { action: "", entity: "", actorId: "", from: "", to: "" };

export function hasAuditFilters(filters: AuditFilters): boolean {
  return Object.values(filters).some((value) => value !== "");
}

/**
 * The query of GET …/audit-log for the filters: business-local days become
 * UTC microseconds, `until` is the start of the day after `to`.
 */
export function auditQuery(
  filters: AuditFilters,
  dayStartUs: (day: string) => number | null,
): { action?: AuditAction; entity?: string; actor_id?: string; since?: string; until?: string } {
  const since = filters.from ? dayStartUs(filters.from) : null;
  const until = filters.to ? dayStartUs(nextDay(filters.to)) : null;
  return {
    ...(filters.action ? { action: filters.action } : {}),
    ...(filters.entity ? { entity: filters.entity } : {}),
    ...(filters.actorId ? { actor_id: filters.actorId } : {}),
    ...(since !== null ? { since: String(since) } : {}),
    ...(until !== null ? { until: String(until) } : {}),
  };
}

/** "2026-02-28" -> "2026-03-01" (calendar arithmetic, no time zone). */
export function nextDay(day: string): string {
  const [year = 1970, month = 1, date = 1] = day.split("-").map(Number);
  const next = new Date(Date.UTC(year, month - 1, date + 1));
  return next.toISOString().slice(0, 10);
}

export const AUDIT_ACTION_TONES: Record<AuditAction, BadgeTone> = {
  view: "neutral",
  create: "success",
  update: "info",
  delete: "danger",
  export: "warning",
  admin_access: "accent",
  login: "neutral",
  retention_purge: "neutral",
  publish_untested: "warning",
  mfa_changed: "neutral",
  support_access_start: "accent",
  support_access_end: "neutral",
  session_revoked: "neutral",
  platform_admin_changed: "neutral",
};

/** Who did it: a team member's name, or null for the platform / unknown users. */
export function actorLabel(actorId: string | null | undefined, members: readonly BusinessMember[]): string | null {
  if (!actorId) {
    return null;
  }
  const member = members.find((item) => item.user_id === actorId);
  return member ? memberLabel(member) : null;
}
