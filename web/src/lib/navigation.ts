/**
 * Routes of the cabinet. Business pages live under /b/{businessId}/{page},
 * where a page is one of BUSINESS_PAGES ("overview", "inbox",
 * "assistant/knowledge", …); which of them a person sees, and how they are
 * grouped into the five sections of the sidebar, is in lib/sections.ts.
 * Addresses of earlier versions are redirected by lib/legacyRoutes.ts.
 *
 * The team inbox is one page with views (`?view=needs_person|requests|
 * mine|unassigned|all`) and its conversations under it
 * (/b/{id}/inbox/{conversationId}): `inboxPath` and `conversationPath`.
 */

import type { BusinessSection } from "./sections";

/** Every page of a business, as its path under /b/{businessId}/. */
export const BUSINESS_PAGES = [
  "overview",
  "overview/reports",
  "inbox",
  "bookings",
  "assistant",
  "assistant/knowledge",
  "assistant/profile",
  "assistant/channels",
  "assistant/versions",
  "settings",
  "settings/team",
  "settings/notifications",
  "settings/quick-replies",
  "settings/calls",
  "settings/reviews",
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
/** The platform admin's key ring and re-encryption of stored tokens. */
export const ADMIN_SECURITY_PATH = "/admin/security";
/** The founder's growth metrics: funnel, MRR, cohorts, Web Vitals. */
export const ADMIN_METRICS_PATH = "/admin/metrics";
/** The platform's health: alerts, workers, queues, dead letters, channels, storage, incidents. */
export const ADMIN_SYSTEM_PATH = "/admin/system";
/** Account → Security: the authenticator app and recovery codes. */
export const ACCOUNT_SECURITY_PATH = "/account/security";
/** Shown by the service worker (public/sw.js) when a page cannot be loaded. */
export const OFFLINE_PATH = "/offline";

/** Where a notification link (`{cabinet}/n/{token}`) lands; see lib/notificationLinks.ts. */
export const NOTIFICATION_LINK_PREFIX = "/n/";

/** Pages that need a session (the proxy sends visitors to /login). */
const PROTECTED_PREFIXES = [HOME_PATH, CREATE_PATH, "/b/", ADMIN_PATH, "/account/", "/integrations/", NOTIFICATION_LINK_PREFIX] as const;

export function isProtectedPath(pathname: string): boolean {
  return PROTECTED_PREFIXES.some(
    (prefix) => pathname === prefix || pathname.startsWith(prefix.endsWith("/") ? prefix : `${prefix}/`),
  );
}

/** `/b/{id}/{page}`; `businessPath(id)` is the overview. */
export function businessPath(businessId: string, page: BusinessPage = "overview"): string {
  return `/b/${encodeURIComponent(businessId)}/${page}`;
}

/** The views of the team inbox, in the order of its tabs (the API's `InboxView`). */
export const INBOX_VIEWS = ["needs_person", "requests", "mine", "unassigned", "all"] as const;

export type InboxView = (typeof INBOX_VIEWS)[number];

/** What the inbox opens on: the conversations waiting for a person. */
export const DEFAULT_INBOX_VIEW: InboxView = "needs_person";

export function isInboxView(value: string | null | undefined): value is InboxView {
  return value !== null && value !== undefined && (INBOX_VIEWS as readonly string[]).includes(value);
}

/** The inbox on one of its views: `/b/{id}/inbox?view=requests` (the default view has no query). */
export function inboxPath(businessId: string, view: InboxView = DEFAULT_INBOX_VIEW): string {
  const path = businessPath(businessId, "inbox");
  return view === DEFAULT_INBOX_VIEW ? path : `${path}?view=${view}`;
}

/** One conversation of the inbox: `/b/{id}/inbox/{conversationId}`. */
export function conversationPath(businessId: string, conversationId: string): string {
  return `${businessPath(businessId, "inbox")}/${encodeURIComponent(conversationId)}`;
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
  /** The page the path is in ("/b/x/inbox/conv_1" is in "inbox"); null outside them. */
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

/** An open conversation ("/b/x/inbox/conv_1"): on phones it takes the whole screen. */
export function isConversationPath(pathname: string): boolean {
  const location = businessLocation(pathname);
  return location?.page === "inbox" && pathname.split("/").filter(Boolean).length > 3;
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

/** Why Account → Security was opened for the person (a place that needs an authenticator app). */
export type SecurityReason = "business" | "admin";

/** Account → Security, telling why it opened and where to go back once done. */
export function securityPath(options: { reason?: SecurityReason; next?: string | null } = {}): string {
  const search = new URLSearchParams();
  if (options.reason) {
    search.set("reason", options.reason);
  }
  const next = options.next ? safeNextPath(options.next, "") : "";
  if (next) {
    search.set("next", next);
  }
  const query = search.toString();
  return query ? `${ACCOUNT_SECURITY_PATH}?${query}` : ACCOUNT_SECURITY_PATH;
}

export function isSecurityReason(value: string | null | undefined): value is SecurityReason {
  return value === "business" || value === "admin";
}
