/**
 * Routes of the cabinet. Business pages live under /b/{businessId}/{page},
 * where a page is one of BUSINESS_PAGES ("overview", "messages/handoffs",
 * "assistant/knowledge", …); which of them a person sees, and how they are
 * grouped into the five sections of the sidebar, is in lib/sections.ts.
 * Addresses of earlier versions are redirected by lib/legacyRoutes.ts.
 */

import type { BusinessSection } from "./sections";

/** Every page of a business, as its path under /b/{businessId}/. */
export const BUSINESS_PAGES = [
  "overview",
  "messages",
  "messages/handoffs",
  "messages/leads",
  "bookings",
  "assistant",
  "assistant/knowledge",
  "assistant/profile",
  "assistant/channels",
  "assistant/versions",
  "settings",
  "settings/team",
  "settings/notifications",
  "settings/calls",
  "settings/billing",
  "settings/privacy",
  "settings/audit",
] as const;

export type BusinessPage = (typeof BUSINESS_PAGES)[number];

export const HOME_PATH = "/businesses";
export const LOGIN_PATH = "/login";
/** "Create an AI assistant" for a business that does not exist yet (the tunnel's first two steps). */
export const CREATE_PATH = "/create";
export const ADMIN_PATH = "/admin";
/** Shown by the service worker (public/sw.js) when a page cannot be loaded. */
export const OFFLINE_PATH = "/offline";

/** Where a notification link (`{cabinet}/n/{token}`) lands; see lib/notificationLinks.ts. */
export const NOTIFICATION_LINK_PREFIX = "/n/";

/** Pages that need a session (the proxy sends visitors to /login). */
const PROTECTED_PREFIXES = [HOME_PATH, CREATE_PATH, "/b/", ADMIN_PATH, "/integrations/", NOTIFICATION_LINK_PREFIX] as const;

export function isProtectedPath(pathname: string): boolean {
  return PROTECTED_PREFIXES.some(
    (prefix) => pathname === prefix || pathname.startsWith(prefix.endsWith("/") ? prefix : `${prefix}/`),
  );
}

/** `/b/{id}/{page}`; `businessPath(id)` is the overview. */
export function businessPath(businessId: string, page: BusinessPage = "overview"): string {
  return `/b/${encodeURIComponent(businessId)}/${page}`;
}

/**
 * The setup flow of a business ("Create an AI assistant", full screen),
 * where an owner continues; `step` opens one of its steps (`?step=hours`).
 */
export function setupPath(businessId: string, step?: string): string {
  const path = `/b/${encodeURIComponent(businessId)}/setup`;
  return step ? `${path}?step=${encodeURIComponent(step)}` : path;
}

export function isBusinessPage(value: string | undefined): value is BusinessPage {
  return value !== undefined && (BUSINESS_PAGES as readonly string[]).includes(value);
}

/** Pages ordered longest first, so the most specific one matches a path. */
const PAGES_BY_DEPTH: readonly BusinessPage[] = [...BUSINESS_PAGES].sort(
  (left, right) => right.split("/").length - left.split("/").length,
);

export interface BusinessLocation {
  businessId: string;
  /** The page the path is in ("/b/x/messages/conv_1" is in "messages"); null outside them. */
  page: BusinessPage | null;
  /** True for the setup flow (/b/{id}/setup; the old /b/{id}/onboarding redirects there). */
  isSetup: boolean;
}

/** Where a path is in the cabinet: "/b/biz_1/assistant/knowledge/import" -> assistant/knowledge. */
export function businessLocation(pathname: string): BusinessLocation | null {
  const [, root, rawId, ...rest] = pathname.split("/");
  if (root !== "b" || !rawId) {
    return null;
  }
  let businessId: string;
  try {
    businessId = decodeURIComponent(rawId);
  } catch {
    return null;
  }
  const segments = rest.filter(Boolean);
  const page =
    PAGES_BY_DEPTH.find((candidate) => {
      const parts = candidate.split("/");
      return parts.every((part, index) => segments[index] === part);
    }) ?? null;
  return { businessId, page, isSetup: segments[0] === "setup" || segments[0] === "onboarding" };
}

/** The section of a business page path: "/b/biz_1/bookings/x" -> "bookings". */
export function sectionFromPathname(pathname: string): BusinessSection | null {
  const page = businessLocation(pathname)?.page;
  return page ? (page.split("/")[0] as BusinessSection) : null;
}

/** An open conversation ("/b/x/messages/conv_1"): on phones it takes the whole screen. */
export function isConversationPath(pathname: string): boolean {
  const location = businessLocation(pathname);
  return location?.page === "messages" && pathname.split("/").filter(Boolean).length > 3;
}

/** The same place in another business (the business switcher keeps the section). */
export function samePageIn(businessId: string, pathname: string): string {
  return businessPath(businessId, businessLocation(pathname)?.page ?? "overview");
}

/** Base used only to check that a path cannot leave the site. */
const SAME_SITE_PROBE = "https://same-site.invalid";

/** Control characters: the URL parser silently drops tab, LF and CR ("/\t/evil" is "//evil"). */
const CONTROL_CHARACTERS = /[\u0000-\u001F\u007F]/;

/**
 * A same-site path to return to after signing in. Anything else (absolute
 * URLs, protocol-relative "//evil", backslashes, control characters, or a
 * path the URL parser resolves to another origin) falls back to the home page.
 */
export function safeNextPath(value: string | null | undefined, fallback: string = HOME_PATH): string {
  if (
    !value ||
    !value.startsWith("/") ||
    value.startsWith("//") ||
    value.includes("\\") ||
    CONTROL_CHARACTERS.test(value)
  ) {
    return fallback;
  }
  if (new URL(value, SAME_SITE_PROBE).origin !== SAME_SITE_PROBE) {
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
