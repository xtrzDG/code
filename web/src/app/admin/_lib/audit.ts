/** Pure helpers of the platform admin's Audit page (/admin/audit). */

import type { Schema } from "@/api/types";
import type { BadgeTone } from "@/components/ui";

export type PlatformAuditEntry = Schema<"PlatformAuditEntryView">;
export type PlatformAuditLogPage = Schema<"PlatformAuditLogPage">;
export type AuditSecurityEvent = Schema<"AuditSecurityEvent">;
export type AuditChainOverview = Schema<"AuditChainOverview">;
export type BrokenAuditChain = Schema<"BrokenAuditChainView">;

export const PLATFORM_AUDIT_PAGE_SIZE = 50;

/** The events of the filter, in the order a sign-in meets them. */
export const SECURITY_EVENTS: readonly AuditSecurityEvent[] = ["login_failed", "otp_locked", "mfa_locked", "logout", "key_rotation"];

/** Lockouts stand out; a wrong code or a sign-out is routine. */
export const SECURITY_EVENT_TONES: Readonly<Record<AuditSecurityEvent, BadgeTone>> = {
  login_failed: "warning",
  otp_locked: "danger",
  mfa_locked: "danger",
  logout: "neutral",
  key_rotation: "accent",
};

/** The query of GET /v1/admin/audit-log for one page and the event filter. */
export function platformAuditQuery(
  event: AuditSecurityEvent | "",
  page: { cursor?: string | null; limit: number },
): { limit: string; cursor?: string; security_event?: AuditSecurityEvent } {
  return {
    limit: String(page.limit),
    ...(page.cursor ? { cursor: page.cursor } : {}),
    ...(event ? { security_event: event } : {}),
  };
}

/**
 * The message key of an entity's name on the admin page: the platform's
 * own entities first ("adminAudit.entities.user_session"), then the names
 * the owners' Audit tab uses; a dotted name reads as one key.
 */
export function platformEntityKeys(entity: string): readonly [string, string] {
  const key = entity.replaceAll(".", "_");
  return [`adminAudit.entities.${key}`, `settings.audit.entities.${key}`];
}

/** "a1b2c3d4": the start of a long id (a digest keeps its "dest_" prefix). */
export function shortReference(reference: string): string {
  if (reference.startsWith("dest_")) {
    return reference.slice(0, 13);
  }
  const bare = reference.includes("_") ? reference.slice(reference.indexOf("_") + 1) : reference;
  return bare.slice(0, 8);
}
