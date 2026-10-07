/**
 * The information architecture of a business: six sections (Overview,
 * Inbox, Bookings, Customers, Assistant, Settings), the pages inside each
 * and who may open them. The sidebar, the phone tab bar, the section tabs
 * and the page titles are all built from these tables.
 *
 * The Inbox is one page: conversations, the ones that need a person and
 * customers' requests are its views. Staff see Overview (without the
 * reports), Inbox, Bookings, the customer list (phones masked unless the
 * owner allows them), the assistant's test chat and Settings →
 * Notifications (their own devices); owners see everything, saved
 * segments among it. Versions and autotests sit in the "advanced" group
 * of the Assistant.
 */

import type { MessageKey } from "@/i18n/translate";

import type { BusinessPage } from "./navigation";

export const BUSINESS_SECTIONS = ["overview", "inbox", "bookings", "customers", "assistant", "settings"] as const;

export type BusinessSection = (typeof BUSINESS_SECTIONS)[number];

/** How a person takes part in a business (a platform admin looks around as an owner). */
export type MemberRole = "owner" | "staff";

const EVERYONE: readonly MemberRole[] = ["owner", "staff"];
const OWNERS: readonly MemberRole[] = ["owner"];

export interface PageEntry {
  page: BusinessPage;
  /** Its name in the sidebar and the section tabs. */
  label: MessageKey;
  roles: readonly MemberRole[];
  /** Shown under the "Advanced" disclosure. */
  isAdvanced?: boolean;
}

export const SECTION_LABELS: Record<BusinessSection, MessageKey> = {
  overview: "navigation.sections.overview",
  inbox: "navigation.sections.inbox",
  bookings: "navigation.sections.bookings",
  customers: "navigation.sections.customers",
  assistant: "navigation.sections.assistant",
  settings: "navigation.sections.settings",
};

/** A shorter name in the phone tab bar, for a section whose name has a word too long for a fifth of a phone ("Posteingang"). */
export const SECTION_TAB_LABELS: Partial<Record<BusinessSection, MessageKey>> = {
  inbox: "navigation.tabLabels.inbox",
};

export const SECTION_DESCRIPTIONS: Record<BusinessSection, MessageKey> = {
  overview: "navigation.descriptions.overview",
  inbox: "navigation.descriptions.inbox",
  bookings: "navigation.descriptions.bookings",
  customers: "navigation.descriptions.customers",
  assistant: "navigation.descriptions.assistant",
  settings: "navigation.descriptions.settings",
};

/** The pages of each section in order; the first one is the section's own address. */
export const SECTION_PAGES: Record<BusinessSection, readonly PageEntry[]> = {
  overview: [
    { page: "overview", label: "navigation.pages.overviewDashboard", roles: EVERYONE },
    { page: "overview/reports", label: "navigation.pages.overviewReports", roles: OWNERS },
  ],
  inbox: [{ page: "inbox", label: "navigation.sections.inbox", roles: EVERYONE }],
  bookings: [
    { page: "bookings", label: "navigation.pages.bookingsList", roles: EVERYONE },
    { page: "bookings/waitlist", label: "navigation.pages.bookingsWaitlist", roles: EVERYONE },
    { page: "bookings/return-visits", label: "navigation.pages.bookingsReturnVisits", roles: OWNERS },
  ],
  customers: [
    { page: "customers", label: "navigation.pages.customersList", roles: EVERYONE },
    { page: "customers/segments", label: "navigation.pages.customersSegments", roles: OWNERS },
  ],
  assistant: [
    { page: "assistant", label: "navigation.pages.assistantTest", roles: EVERYONE },
    { page: "assistant/knowledge", label: "navigation.pages.assistantKnowledge", roles: OWNERS },
    { page: "assistant/profile", label: "navigation.pages.assistantProfile", roles: OWNERS },
    { page: "assistant/channels", label: "navigation.pages.assistantChannels", roles: OWNERS },
    { page: "assistant/versions", label: "navigation.pages.assistantVersions", roles: OWNERS, isAdvanced: true },
    { page: "assistant/checks", label: "navigation.pages.assistantChecks", roles: OWNERS, isAdvanced: true },
  ],
  settings: [
    { page: "settings", label: "navigation.pages.settingsGeneral", roles: OWNERS },
    { page: "settings/team", label: "navigation.pages.settingsTeam", roles: OWNERS },
    // Everyone turns notifications on for their own devices; owners also manage the staff contacts.
    { page: "settings/notifications", label: "navigation.pages.settingsNotifications", roles: EVERYONE },
    { page: "settings/quick-replies", label: "navigation.pages.settingsQuickReplies", roles: OWNERS },
    { page: "settings/calls", label: "navigation.pages.settingsCalls", roles: OWNERS },
    { page: "settings/reviews", label: "navigation.pages.settingsReviews", roles: OWNERS },
    { page: "settings/integrations", label: "navigation.pages.settingsIntegrations", roles: OWNERS },
    { page: "settings/billing", label: "navigation.pages.settingsBilling", roles: OWNERS },
    { page: "settings/privacy", label: "navigation.pages.settingsPrivacy", roles: OWNERS },
    { page: "settings/audit", label: "navigation.pages.settingsAudit", roles: OWNERS },
  ],
};

/** What a page is for, under its title (pages without one show none). */
export const PAGE_DESCRIPTIONS: Partial<Record<BusinessPage, MessageKey>> = {
  "overview/reports": "reports.description",
  inbox: "navigation.descriptions.inbox",
  bookings: "pages.bookings.description",
  "bookings/waitlist": "navigation.descriptions.bookingsWaitlist",
  "bookings/return-visits": "navigation.descriptions.bookingsReturnVisits",
  customers: "navigation.descriptions.customersList",
  "customers/segments": "navigation.descriptions.customersSegments",
  assistant: "navigation.descriptions.assistantTest",
  "assistant/knowledge": "pages.knowledge.description",
  "assistant/profile": "navigation.descriptions.assistantProfile",
  "assistant/channels": "pages.channels.description",
  "assistant/versions": "navigation.descriptions.assistantVersions",
  "assistant/checks": "navigation.descriptions.assistantChecks",
  "settings/quick-replies": "quickReplies.description",
  "settings/calls": "callSettings.description",
  "settings/reviews": "reviewSettings.description",
  "settings/integrations": "calendarSync.integrations.description",
  "settings/billing": "pages.billing.description",
};

/** The section of a page: "assistant/knowledge" -> "assistant". */
export function sectionOf(page: BusinessPage): BusinessSection {
  return page.split("/")[0] as BusinessSection;
}

function entryOf(page: BusinessPage): PageEntry {
  const pages: readonly PageEntry[] | undefined = SECTION_PAGES[sectionOf(page)];
  const entry = pages?.find((candidate) => candidate.page === page);
  if (!entry) {
    throw new Error(`The page ${page} is missing from SECTION_PAGES.`);
  }
  return entry;
}

/** Whether a person with this role may open the page (the API refuses the rest anyway). */
export function canOpenPage(page: BusinessPage, role: MemberRole): boolean {
  return entryOf(page).roles.includes(role);
}

/** The pages of a section this role may open, in order. */
export function visiblePages(section: BusinessSection, role: MemberRole): readonly PageEntry[] {
  return SECTION_PAGES[section].filter((entry) => entry.roles.includes(role));
}

/** The sections with at least one page for this role. */
export function visibleSections(role: MemberRole): readonly BusinessSection[] {
  return BUSINESS_SECTIONS.filter((section) => visiblePages(section, role).length > 0);
}

/** The page's name: the section's for a section's own page, else the page's. */
export function pageLabel(page: BusinessPage): MessageKey {
  const section = sectionOf(page);
  return SECTION_PAGES[section].length === 1 ? SECTION_LABELS[section] : entryOf(page).label;
}

/** The page title in the browser: "Team · Settings" (the business name follows). */
export function pageTitleKeys(page: BusinessPage): readonly MessageKey[] {
  const section = sectionOf(page);
  const label = pageLabel(page);
  return label === SECTION_LABELS[section] ? [label] : [label, SECTION_LABELS[section]];
}

/** Every page is in exactly one section's list (a unit test keeps the two tables in step). */
export function listedPages(): readonly BusinessPage[] {
  return BUSINESS_SECTIONS.flatMap((section) => SECTION_PAGES[section].map((entry) => entry.page));
}
