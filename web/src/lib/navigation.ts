/**
 * Routes of the cabinet. Business pages live under /b/{businessId}/{section};
 * each section here appears in the sidebar (see components/shell/BusinessNav).
 */

import type { MessageKey } from "@/i18n/translate";

export const BUSINESS_SECTIONS = [
  "onboarding",
  "dashboard",
  "conversations",
  "bookings",
  "leads",
  "handoffs",
  "knowledge",
  "assistant",
  "channels",
  "billing",
  "settings",
] as const;

export type BusinessSection = (typeof BUSINESS_SECTIONS)[number];

export const BUSINESS_SECTION_LABELS: Record<BusinessSection, MessageKey> = {
  onboarding: "nav.onboarding",
  dashboard: "nav.dashboard",
  conversations: "nav.conversations",
  bookings: "nav.bookings",
  leads: "nav.leads",
  handoffs: "nav.handoffs",
  knowledge: "nav.knowledge",
  assistant: "nav.assistant",
  channels: "nav.channels",
  billing: "nav.billing",
  settings: "nav.settings",
};

export const HOME_PATH = "/businesses";
export const LOGIN_PATH = "/login";
export const ADMIN_PATH = "/admin";

/** Pages that need a session (the proxy sends visitors to /login). */
const PROTECTED_PREFIXES = [HOME_PATH, "/b/", ADMIN_PATH] as const;

export function isProtectedPath(pathname: string): boolean {
  return PROTECTED_PREFIXES.some(
    (prefix) => pathname === prefix || pathname.startsWith(prefix.endsWith("/") ? prefix : `${prefix}/`),
  );
}

/** `/b/{id}/{section}`; `businessPath(id)` is the dashboard. */
export function businessPath(businessId: string, section: BusinessSection = "dashboard"): string {
  return `/b/${encodeURIComponent(businessId)}/${section}`;
}

export function isBusinessSection(value: string | undefined): value is BusinessSection {
  return value !== undefined && (BUSINESS_SECTIONS as readonly string[]).includes(value);
}

/** The section of a business page path: "/b/biz_1/bookings/x" -> "bookings". */
export function sectionFromPathname(pathname: string): BusinessSection | null {
  const [, root, , section] = pathname.split("/");
  return root === "b" && isBusinessSection(section) ? section : null;
}

/**
 * A same-site path to return to after signing in. Anything else (absolute
 * URLs, protocol-relative "//evil", backslashes) falls back to the home page.
 */
export function safeNextPath(value: string | null | undefined, fallback: string = HOME_PATH): string {
  if (!value || !value.startsWith("/") || value.startsWith("//") || value.includes("\\")) {
    return fallback;
  }
  if (value === LOGIN_PATH || value.startsWith(`${LOGIN_PATH}?`) || value.startsWith("/api/")) {
    return fallback;
  }
  return value;
}

export type LoginReason = "expired";

export function loginPath(options: { next?: string | null; reason?: LoginReason } = {}): string {
  const search = new URLSearchParams();
  const next = options.next ? safeNextPath(options.next, "") : "";
  if (next && next !== HOME_PATH) {
    search.set("next", next);
  }
  if (options.reason) {
    search.set("reason", options.reason);
  }
  const query = search.toString();
  return query ? `${LOGIN_PATH}?${query}` : LOGIN_PATH;
}
