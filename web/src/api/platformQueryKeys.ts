/**
 * The query keys of the platform's own data, outside any business: the
 * catalog, sign-in, the admin pages, help, the status page and the
 * signed-in person's account. Spread into `queryKeys`, which documents the
 * key rules.
 */

import type { QueryKey } from "./queryKey";

type Id = string;
type Locale = string;
type Optional<T> = T | null;

export const platformQueryKeys = {
  catalog: {
    countries: (locale: Locale) => ["catalog", "countries", locale] as const,
    country: (countryCode: string, locale: Locale) => ["catalog", "country", countryCode, locale] as const,
    niches: (locale: Locale) => ["catalog", "niches", locale] as const,
    niche: (nicheKey: string, locale: Locale) => ["catalog", "niche", nicheKey, locale] as const,
    languages: (locale: Locale) => ["catalog", "languages", locale] as const,
    plans: (countryCode: string, locale: Locale) => ["catalog", "plans", countryCode, locale] as const,
    dpa: (version: string, locale: Locale) => ["catalog", "dpa", version, locale] as const,
    legal: (document: string, version: string, locale: Locale) =>
      ["catalog", "legal", document, version, locale] as const,
  },

  auth: {
    loginOptions: (countryCode: Optional<string>) => ["auth", "loginOptions", countryCode] as const,
  },

  admin: {
    all: () => ["admin"] as const,
    clients: (filters: string) => ["admin", "clients", filters] as const,
    client: (businessId: Id) => ["admin", "client", businessId] as const,
    clientQuality: (businessId: Id) => ["admin", "client", businessId, "quality"] as const,
    /** The platform team's notes about one client (under the client: an account action reloads them). */
    clientNotes: (businessId: Id) => ["admin", "client", businessId, "notes"] as const,
    /** One client's timeline, newest first. */
    clientTimeline: (businessId: Id) => ["admin", "client", businessId, "timeline"] as const,
    /** The key ring and the latest re-encryption run. */
    encryptionKeys: () => ["admin", "encryptionKeys"] as const,
    /** The founder's growth metrics for one set of filters. */
    metrics: (filters: string) => ["admin", "metrics", filters] as const,
    /** The platform's health (GET /v1/admin/system). */
    system: () => ["admin", "system"] as const,
    /** The providers' spend of the UTC day (GET /v1/admin/spend). */
    spend: () => ["admin", "spend"] as const,
    /** The dead letters of the background queue. */
    deadJobs: () => ["admin", "jobs", "dead"] as const,
    /** The recorded incidents, newest first. */
    incidents: () => ["admin", "incidents"] as const,
    /** The platform admin team. */
    team: () => ["admin", "team"] as const,
    /** The status page's announcements, newest first. */
    announcements: () => ["admin", "announcements"] as const,
    /** The partners, their codes and totals. */
    partners: () => ["admin", "partners"] as const,
    /** One month's payout report (YYYY-MM). */
    payouts: (month: string) => ["admin", "partners", "payouts", month] as const,
  },

  help: {
    /** The help center's topics and articles in one language. */
    center: (locale: Locale) => ["help", "center", locale] as const,
    article: (locale: Locale, slug: string) => ["help", "article", locale, slug] as const,
    search: (locale: Locale, text: string) => ["help", "search", locale, text] as const,
    /** The signed-in person's seen tips and the newest "What's new" entry read. */
    progress: () => ["help", "progress"] as const,
    /** How to reach the platform's support. */
    support: () => ["help", "support"] as const,
  },

  platformStatus: {
    /** The public status page in one language. */
    status: (locale: Locale) => ["platformStatus", locale] as const,
  },

  partner: {
    /** The signed-in partner's codes, rate and totals. */
    portal: () => ["partner", "portal"] as const,
    referrals: () => ["partner", "referrals"] as const,
    commissions: () => ["partner", "commissions"] as const,
  },

  account: {
    /** The signed-in person's devices (Account → Security). */
    sessions: () => ["account", "sessions"] as const,
  },
} satisfies Record<string, Record<string, (...args: never[]) => QueryKey>>;
