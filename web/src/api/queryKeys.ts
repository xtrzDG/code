/**
 * Every query key of the cabinet, in one place. A key starts with its
 * section and the business, so a prefix names a whole section:
 *
 *     useQuery(queryKeys.leads.list(businessId, tab, includeTest), ...);
 *     invalidate(queryKeys.leads.all(businessId));   // every leads list of the business
 *
 * Keys hold plain values only (strings, numbers, booleans, null): an
 * optional filter is `null` when unset, never `undefined`.
 */

import type { QueryKey } from "./queryKey";

type Id = string;
type Locale = string;
type Optional<T> = T | null;

const opt = <T>(value: T | null | undefined): T | null => value ?? null;

export const queryKeys = {
  business: {
    all: (businessId: Id) => ["business", businessId] as const,
    /** The business as stored (settings forms start from it). */
    detail: (businessId: Id) => ["business", businessId, "detail"] as const,
  },

  dashboard: {
    all: (businessId: Id) => ["dashboard", businessId] as const,
    stats: (businessId: Id, from: string, to: string) => ["dashboard", businessId, "stats", from, to] as const,
  },

  conversations: {
    all: (businessId: Id) => ["conversations", businessId] as const,
    list: (businessId: Id, filters: string, today: string) =>
      ["conversations", businessId, "list", filters, today] as const,
    detail: (businessId: Id, conversationId: Id) => ["conversations", businessId, "detail", conversationId] as const,
  },

  bookings: {
    all: (businessId: Id) => ["bookings", businessId] as const,
    list: (
      businessId: Id,
      filters: { from: Optional<string>; to: Optional<string>; range: string; status: Optional<string>; resourceId: Optional<string>; includeTest: boolean },
    ) =>
      [
        "bookings",
        businessId,
        "list",
        filters.range,
        opt(filters.from),
        opt(filters.to),
        opt(filters.status),
        opt(filters.resourceId),
        filters.includeTest,
      ] as const,
    availability: (businessId: Id, request: string) => ["bookings", businessId, "availability", request] as const,
  },

  leads: {
    all: (businessId: Id) => ["leads", businessId] as const,
    list: (businessId: Id, tab: string, includeTest: boolean) => ["leads", businessId, "list", tab, includeTest] as const,
  },

  handoffs: {
    all: (businessId: Id) => ["handoffs", businessId] as const,
    list: (businessId: Id, tab: string, includeTest: boolean) =>
      ["handoffs", businessId, "list", tab, includeTest] as const,
  },

  inbox: {
    all: (businessId: Id) => ["inbox", businessId] as const,
    /** Open handoffs and new requests: the badges on Messages (counts only, not audited). */
    counts: (businessId: Id) => ["inbox", businessId, "counts"] as const,
  },

  knowledge: {
    all: (businessId: Id) => ["knowledge", businessId] as const,
    items: (businessId: Id, locale: Locale, kind: string, status: string) =>
      ["knowledge", businessId, "items", locale, kind, status] as const,
    /** The whole list for the profile wizard's offer and FAQ steps. */
    wizardItems: (businessId: Id, locale: Locale) => ["knowledge", businessId, "wizardItems", locale] as const,
    questions: (businessId: Id, includeResolved: boolean, includeSandbox: boolean) =>
      ["knowledge", businessId, "questions", includeResolved, includeSandbox] as const,
    /** The open questions counted for the items page's warning. */
    questionsAlert: (businessId: Id) => ["knowledge", businessId, "questionsAlert"] as const,
  },

  resources: {
    all: (businessId: Id) => ["resources", businessId] as const,
    list: (businessId: Id) => ["resources", businessId, "list"] as const,
    exceptions: (businessId: Id) => ["resources", businessId, "exceptions"] as const,
  },

  profile: {
    all: (businessId: Id) => ["profile", businessId] as const,
    stored: (businessId: Id) => ["profile", businessId, "stored"] as const,
    wizard: (businessId: Id, locale: Locale) => ["profile", businessId, "wizard", locale] as const,
    gaps: (businessId: Id, locale: Locale) => ["profile", businessId, "gaps", locale] as const,
  },

  assistant: {
    all: (businessId: Id) => ["assistant", businessId] as const,
    versions: (businessId: Id) => ["assistant", businessId, "versions"] as const,
    version: (businessId: Id, versionId: Id) => ["assistant", businessId, "version", versionId] as const,
    autotestRun: (businessId: Id, versionId: Id) => ["assistant", businessId, "version", versionId, "run"] as const,
    readiness: (businessId: Id, versionId: Id) => ["assistant", businessId, "version", versionId, "readiness"] as const,
  },

  channels: {
    all: (businessId: Id) => ["channels", businessId] as const,
    list: (businessId: Id) => ["channels", businessId, "list"] as const,
    snippet: (businessId: Id) => ["channels", businessId, "snippet"] as const,
    callForwarding: (businessId: Id, locale: Locale) => ["channels", businessId, "callForwarding", locale] as const,
    calendar: (businessId: Id) => ["channels", businessId, "calendar"] as const,
    /** Share links of every tag (`share(id, "")` is the untagged set). */
    shareAll: (businessId: Id) => ["channels", businessId, "share"] as const,
    share: (businessId: Id, source: string) => ["channels", businessId, "share", source] as const,
  },

  billing: {
    all: (businessId: Id) => ["billing", businessId] as const,
    overview: (businessId: Id, locale: Locale) => ["billing", businessId, "overview", locale] as const,
  },

  settings: {
    dpa: (businessId: Id) => ["settings", businessId, "dpa"] as const,
    contacts: (businessId: Id, search: Optional<string>) => ["settings", businessId, "contacts", search] as const,
    audit: (businessId: Id, filters: string) => ["settings", businessId, "audit", filters] as const,
  },

  calls: {
    all: (businessId: Id) => ["calls", businessId] as const,
    /** Settings → Calls: summaries, text-backs, the template texts. */
    settings: (businessId: Id) => ["calls", businessId, "settings"] as const,
    /** The latest callers who did not get through (audited as a view). */
    textBacks: (businessId: Id) => ["calls", businessId, "textBacks"] as const,
  },

  notifications: {
    all: (businessId: Id) => ["notifications", businessId] as const,
    /** Staff contacts with their delivery state. */
    contacts: (businessId: Id) => ["notifications", businessId, "contacts"] as const,
    /** My events, quiet hours and devices. */
    mine: (businessId: Id) => ["notifications", businessId, "mine"] as const,
  },

  catalog: {
    countries: (locale: Locale) => ["catalog", "countries", locale] as const,
    country: (countryCode: string, locale: Locale) => ["catalog", "country", countryCode, locale] as const,
    niches: (locale: Locale) => ["catalog", "niches", locale] as const,
    niche: (nicheKey: string, locale: Locale) => ["catalog", "niche", nicheKey, locale] as const,
    languages: (locale: Locale) => ["catalog", "languages", locale] as const,
    plans: (countryCode: string, locale: Locale) => ["catalog", "plans", countryCode, locale] as const,
    dpa: (version: string, locale: Locale) => ["catalog", "dpa", version, locale] as const,
  },

  auth: {
    loginOptions: (countryCode: Optional<string>) => ["auth", "loginOptions", countryCode] as const,
  },

  admin: {
    all: () => ["admin"] as const,
    clients: (filters: string) => ["admin", "clients", filters] as const,
    client: (businessId: Id) => ["admin", "client", businessId] as const,
  },
} satisfies Record<string, Record<string, (...args: never[]) => QueryKey>>;
