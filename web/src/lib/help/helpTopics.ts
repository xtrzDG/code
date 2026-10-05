/**
 * Which help article a page of the cabinet opens (the "?" beside its
 * title), the article links an article may hold, and where a cabinet link
 * of an article leads. The articles themselves are Markdown files of the
 * API (docs/help/{language}/{slug}.md); helpTopics.test.ts reads them and
 * fails when a link names an article or a page that does not exist.
 */

import { BUSINESS_PAGES, businessPath, type BusinessPage } from "@/lib/navigation";

/** Every article of the help center, by its slug (the same in every language). */
export const HELP_ARTICLES = [
  "getting-started",
  "teach-your-assistant",
  "channels",
  "telegram",
  "whatsapp",
  "instagram-messenger",
  "widget-install",
  "call-forwarding",
  "inbox",
  "bookings",
  "billing",
  "privacy",
] as const;

export type HelpArticleSlug = (typeof HELP_ARTICLES)[number];

/** The article that explains each page; pages without one of their own open "getting started". */
export const PAGE_HELP: Readonly<Record<BusinessPage, HelpArticleSlug>> = {
  overview: "getting-started",
  "overview/reports": "getting-started",
  inbox: "inbox",
  bookings: "bookings",
  customers: "privacy",
  "customers/segments": "privacy",
  assistant: "teach-your-assistant",
  "assistant/knowledge": "teach-your-assistant",
  "assistant/profile": "teach-your-assistant",
  "assistant/channels": "channels",
  "assistant/versions": "teach-your-assistant",
  "assistant/checks": "teach-your-assistant",
  settings: "getting-started",
  "settings/team": "getting-started",
  "settings/notifications": "inbox",
  "settings/quick-replies": "inbox",
  "settings/calls": "call-forwarding",
  "settings/reviews": "bookings",
  "settings/billing": "billing",
  "settings/privacy": "privacy",
  "settings/audit": "privacy",
};

/** The one-time tips: the page each shows on, and the article its "Read the guide" opens. */
export const COACH_MARKS = [
  { key: "inbox", page: "inbox", article: "inbox" },
  { key: "assistant", page: "assistant", article: "teach-your-assistant" },
  { key: "channels", page: "assistant/channels", article: "channels" },
] as const satisfies readonly { key: string; page: BusinessPage; article: HelpArticleSlug }[];

export type CoachMark = (typeof COACH_MARKS)[number];

/** The tip of a page, if it has one. */
export function coachMarkFor(page: BusinessPage | null): CoachMark | null {
  return COACH_MARKS.find((mark) => mark.page === page) ?? null;
}

export function isHelpArticleSlug(value: string): value is HelpArticleSlug {
  return (HELP_ARTICLES as readonly string[]).includes(value);
}

/** The article for a page of a business; null outside the business pages. */
export function helpSlugForPage(page: BusinessPage | null): HelpArticleSlug | null {
  return page ? PAGE_HELP[page] : null;
}

/** "cabinet:assistant/channels" in an article -> the page, when it is one of the cabinet's. */
export function cabinetPage(path: string): BusinessPage | null {
  return (BUSINESS_PAGES as readonly string[]).includes(path) ? (path as BusinessPage) : null;
}

/** Where a cabinet link leads in the business the person is in; null outside a business. */
export function cabinetHref(page: BusinessPage, businessId: string | null): string | null {
  return businessId ? businessPath(businessId, page) : null;
}

/** The help center's page of an article (public, in the interface language). */
export function helpArticlePath(slug: string): string {
  return `${HELP_PATH}/${encodeURIComponent(slug)}`;
}

/** The help center: articles by topic and the search. */
export const HELP_PATH = "/help";
/** "What's new": the cabinet's changelog. */
export const WHATS_NEW_PATH = "/help/whats-new";
/** The public status page of the platform. */
export const STATUS_PATH = "/status";
