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

import { platformQueryKeys } from "./platformQueryKeys";
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
    /** What the assistant is worth in local dates `from` to `to`, against the days before. */
    value: (businessId: Id, from: string, to: string) => ["dashboard", businessId, "value", from, to] as const,
    /** The same for a named period ("this_month"). */
    valuePeriod: (businessId: Id, period: string) => ["dashboard", businessId, "value", period] as const,
    /** Today's bookings (counts only) and the inbox views of the signed-in member. */
    todayQueue: (businessId: Id, today: string) => ["dashboard", businessId, "todayQueue", today] as const,
    inboxViews: (businessId: Id) => ["dashboard", businessId, "inboxViews"] as const,
    /** What customers asked about, as the nightly grouping last stored it. */
    /** What customers ask about, labelled in the cabinet's language. */
    topics: (businessId: Id, language: string) => ["dashboard", businessId, "topics", language] as const,
    /** Bad ratings nobody acted on and questions without an answer (the Overview's list). */
    answersToImprove: (businessId: Id) => ["dashboard", businessId, "answersToImprove"] as const,
  },

  referrals: {
    /** The business's own invitation: code, link, counts and the "Powered by" choice. */
    program: (businessId: Id) => ["referrals", businessId, "program"] as const,
  },

  reports: {
    all: (businessId: Id) => ["reports", businessId] as const,
    /** Stored reports of one kind, newest first. */
    list: (businessId: Id, kind: string) => ["reports", businessId, "list", kind] as const,
    detail: (businessId: Id, reportId: Id) => ["reports", businessId, "detail", reportId] as const,
    /** The signed-in owner's summaries. */
    digests: (businessId: Id) => ["reports", businessId, "digests"] as const,
    /** Where customers came from in a named period ("30d"). */
    sources: (businessId: Id, period: string) => ["reports", businessId, "sources", period] as const,
  },

  conversations: {
    all: (businessId: Id) => ["conversations", businessId] as const,
    list: (businessId: Id, filters: string, today: string) =>
      ["conversations", businessId, "list", filters, today] as const,
    detail: (businessId: Id, conversationId: Id) => ["conversations", businessId, "detail", conversationId] as const,
    /** "Fix this answer": the draft of one assistant answer (each read is audited). */
    correction: (businessId: Id, conversationId: Id, messageId: Id) =>
      ["conversations", businessId, "correction", conversationId, messageId] as const,
    /** Every view of the team inbox (each load is audited, like the feed). */
    inboxAll: (businessId: Id) => ["conversations", businessId, "inbox"] as const,
    inbox: (businessId: Id, view: string, channel: Optional<string>) =>
      ["conversations", businessId, "inbox", view, opt(channel)] as const,
    /** The team's internal notes on a conversation (audited reads). */
    notes: (businessId: Id, conversationId: Id) => ["conversations", businessId, "notes", conversationId] as const,
    /** Quick replies filled in for one conversation (audited reads). */
    quickReplies: (businessId: Id, conversationId: Id) =>
      ["conversations", businessId, "quickReplies", conversationId] as const,
    /** The nightly judge's score of one conversation (most have none). */
    quality: (businessId: Id, conversationId: Id) => ["conversations", businessId, "quality", conversationId] as const,
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
    /** Open handoffs and new requests: the badges on the Inbox (counts only, not audited). */
    counts: (businessId: Id) => ["inbox", businessId, "counts"] as const,
    /** How many conversations each view of the inbox holds for me (counts only, not audited). */
    views: (businessId: Id) => ["inbox", businessId, "views"] as const,
    /** The members to assign conversations to, with their workload (no contact details). */
    assignees: (businessId: Id) => ["inbox", businessId, "assignees"] as const,
  },

  quickReplies: {
    all: (businessId: Id) => ["quickReplies", businessId] as const,
    /** The business's quick replies as stored (Settings → Quick replies). */
    list: (businessId: Id) => ["quickReplies", businessId, "list"] as const,
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
    /** The business's current import from its website (progress and drafts). */
    websiteImport: (businessId: Id) => ["knowledge", businessId, "websiteImport"] as const,
    /** The active services, packages and room types (bookings, resources). */
    offers: (businessId: Id) => ["knowledge", businessId, "offers"] as const,
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
    /** What customers do not get yet: the changes since the live version. */
    pending: (businessId: Id, locale: Locale) => ["assistant", businessId, "pending", locale] as const,
    /** The same in every language: what the assistant knows changed. */
    pendingAll: (businessId: Id) => ["assistant", businessId, "pending"] as const,
    /** The owner's own checks ("My checks") with their latest results. */
    checks: (businessId: Id) => ["assistant", businessId, "checks"] as const,
  },

  setup: {
    all: (businessId: Id) => ["setup", businessId] as const,
    /** The guided setup: steps, progress, links, milestones and the launch. */
    progress: (businessId: Id, locale: Locale) => ["setup", businessId, "progress", locale] as const,
    /** The guided setup in every language (live events: a booking or a channel moves the guide on). */
    progressAll: (businessId: Id) => ["setup", businessId, "progress"] as const,
    /** Whether the owner gets the setup reminders (Settings → Notifications). */
    reminders: (businessId: Id) => ["setup", businessId, "reminders"] as const,
    /** The niche's starter answers (hours, booking rules, examples). */
    starters: (businessId: Id, locale: Locale) => ["setup", businessId, "starters", locale] as const,
    /** "Apply changes" (the launch) and its progress. */
    apply: (businessId: Id, locale: Locale) => ["setup", businessId, "apply", locale] as const,
    /** "Apply changes" in every language (its progress moved on). */
    applyAll: (businessId: Id) => ["setup", businessId, "apply"] as const,
  },

  channels: {
    all: (businessId: Id) => ["channels", businessId] as const,
    list: (businessId: Id) => ["channels", businessId, "list"] as const,
    snippet: (businessId: Id) => ["channels", businessId, "snippet"] as const,
    /** The websites allowed to show the website chat. */
    allowedOrigins: (businessId: Id) => ["channels", businessId, "allowedOrigins"] as const,
    callForwarding: (businessId: Id, locale: Locale) => ["channels", businessId, "callForwarding", locale] as const,
    calendar: (businessId: Id) => ["channels", businessId, "calendar"] as const,
    /** Share links of every tag (`share(id, "")` is the untagged set). */
    shareAll: (businessId: Id) => ["channels", businessId, "share"] as const,
    share: (businessId: Id, source: string) => ["channels", businessId, "share", source] as const,
  },

  billing: {
    all: (businessId: Id) => ["billing", businessId] as const,
    overview: (businessId: Id, locale: Locale) => ["billing", businessId, "overview", locale] as const,
    /** The billing details invoices name the business with. */
    profile: (businessId: Id) => ["billing", businessId, "profile"] as const,
  },

  settings: {
    dpa: (businessId: Id) => ["settings", businessId, "dpa"] as const,
    audit: (businessId: Id, filters: string) => ["settings", businessId, "audit", filters] as const,
    /** Settings → Team: whether the team must sign in with two factors. */
    security: (businessId: Id) => ["settings", businessId, "security"] as const,
    /** Settings → Privacy: the latest full exports of the business. */
    businessExports: (businessId: Id) => ["settings", businessId, "businessExports"] as const,
    /** Settings → Privacy: how long data is kept, the latest cleanup. */
    privacy: (businessId: Id) => ["settings", businessId, "privacy"] as const,
  },

  customers: {
    all: (businessId: Id) => ["customers", businessId] as const,
    /** The list with its search, tag and VIP/blocked filter (serialized). */
    list: (businessId: Id, filters: string) => ["customers", businessId, "list", filters] as const,
    /** One customer's page (audited as a view by the API). */
    detail: (businessId: Id, contactId: Id) => ["customers", businessId, "detail", contactId] as const,
    /** "Regular customer · 4 visits" over a conversation. */
    standing: (businessId: Id, contactId: Id) => ["customers", businessId, "standing", contactId] as const,
    /** Whether staff see phones; the business's tags. */
    settings: (businessId: Id) => ["customers", businessId, "settings"] as const,
    segments: (businessId: Id) => ["customers", businessId, "segments"] as const,
    members: (businessId: Id, segmentId: Id) => ["customers", businessId, "members", segmentId] as const,
    /** How many customers rules hold (serialized rules). */
    preview: (businessId: Id, rules: string) => ["customers", businessId, "preview", rules] as const,
    /** The command palette's search. */
    search: (businessId: Id, text: string) => ["customers", businessId, "search", text] as const,
  },

  calls: {
    all: (businessId: Id) => ["calls", businessId] as const,
    /** Settings → Calls: summaries, text-backs, the template texts. */
    settings: (businessId: Id) => ["calls", businessId, "settings"] as const,
    /** The latest callers who did not get through (audited as a view). */
    textBacks: (businessId: Id) => ["calls", businessId, "textBacks"] as const,
  },

  reviews: {
    all: (businessId: Id) => ["reviews", businessId] as const,
    /** Settings → Reviews: feedback after visits, the review link, the template texts. */
    settings: (businessId: Id) => ["reviews", businessId, "settings"] as const,
    /** The last 30 days in numbers. */
    stats: (businessId: Id) => ["reviews", businessId, "stats"] as const,
    /** The latest visits asked about (audited as a view). */
    requests: (businessId: Id) => ["reviews", businessId, "requests"] as const,
  },

  notifications: {
    all: (businessId: Id) => ["notifications", businessId] as const,
    /** Staff contacts with their delivery state. */
    contacts: (businessId: Id) => ["notifications", businessId, "contacts"] as const,
    /** My events, quiet hours and devices. */
    mine: (businessId: Id) => ["notifications", businessId, "mine"] as const,
  },

  ...platformQueryKeys,

  assistantSettings: {
    /** Settings → General: whether the assistant remembers returning customers. */
    detail: (businessId: Id) => ["assistantSettings", businessId] as const,
  },

  supportAccess: {
    /** Platform support in a business now: open looks and the consent to changes. */
    status: (businessId: Id) => ["supportAccess", businessId] as const,
  },
} satisfies Record<string, Record<string, (...args: never[]) => QueryKey>>;
