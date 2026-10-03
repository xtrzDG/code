/**
 * The information architecture of a business: five sections (Overview,
 * Messages, Bookings, Assistant, Settings), the pages inside each and who
 * may open them. The sidebar, the phone tab bar, the section tabs and the
 * page titles are all built from these tables.
 *
 * Staff see Overview (without the reports), Messages, Bookings, the assistant's test chat and
 * Settings → Notifications (their own devices); owners see everything. Versions and autotests sit in the "advanced"
 * group of the Assistant.
 */

import type { MessageKey } from "@/i18n/translate";

import type { BusinessPage } from "./navigation";

export const BUSINESS_SECTIONS = ["overview", "messages", "bookings", "assistant", "settings"] as const;

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
  messages: "navigation.sections.messages",
  bookings: "navigation.sections.bookings",
  assistant: "navigation.sections.assistant",
  settings: "navigation.sections.settings",
};

export const SECTION_DESCRIPTIONS: Record<BusinessSection, MessageKey> = {
  overview: "navigation.descriptions.overview",
  messages: "navigation.descriptions.messages",
  bookings: "navigation.descriptions.bookings",
  assistant: "navigation.descriptions.assistant",
  settings: "navigation.descriptions.settings",
};

/** The pages of each section in order; the first one is the section's own address. */
export const SECTION_PAGES: Record<BusinessSection, readonly PageEntry[]> = {
  overview: [
    { page: "overview", label: "navigation.pages.overviewDashboard", roles: EVERYONE },
    { page: "overview/reports", label: "navigation.pages.overviewReports", roles: OWNERS },
  ],
  messages: [
    { page: "messages", label: "navigation.pages.messagesAll", roles: EVERYONE },
    { page: "messages/handoffs", label: "navigation.pages.messagesHandoffs", roles: EVERYONE },
    { page: "messages/leads", label: "navigation.pages.messagesLeads", roles: EVERYONE },
  ],
  bookings: [{ page: "bookings", label: "navigation.sections.bookings", roles: EVERYONE }],
  assistant: [
    { page: "assistant", label: "navigation.pages.assistantTest", roles: EVERYONE },
    { page: "assistant/knowledge", label: "navigation.pages.assistantKnowledge", roles: OWNERS },
    { page: "assistant/profile", label: "navigation.pages.assistantProfile", roles: OWNERS },
    { page: "assistant/channels", label: "navigation.pages.assistantChannels", roles: OWNERS },
    { page: "assistant/versions", label: "navigation.pages.assistantVersions", roles: OWNERS, isAdvanced: true },
  ],
  settings: [
    { page: "settings", label: "navigation.pages.settingsGeneral", roles: OWNERS },
    { page: "settings/team", label: "navigation.pages.settingsTeam", roles: OWNERS },
    // Everyone turns notifications on for their own devices; owners also manage the staff contacts.
    { page: "settings/notifications", label: "navigation.pages.settingsNotifications", roles: EVERYONE },
    { page: "settings/calls", label: "navigation.pages.settingsCalls", roles: OWNERS },
    { page: "settings/reviews", label: "navigation.pages.settingsReviews", roles: OWNERS },
    { page: "settings/billing", label: "navigation.pages.settingsBilling", roles: OWNERS },
    { page: "settings/privacy", label: "navigation.pages.settingsPrivacy", roles: OWNERS },
    { page: "settings/audit", label: "navigation.pages.settingsAudit", roles: OWNERS },
  ],
};

/** What a page is for, under its title (pages without one show none). */
export const PAGE_DESCRIPTIONS: Partial<Record<BusinessPage, MessageKey>> = {
  "overview/reports": "reports.description",
  messages: "pages.conversations.description",
  "messages/handoffs": "pages.handoffs.description",
  "messages/leads": "pages.leads.description",
  bookings: "pages.bookings.description",
  assistant: "navigation.descriptions.assistantTest",
  "assistant/knowledge": "pages.knowledge.description",
  "assistant/profile": "navigation.descriptions.assistantProfile",
  "assistant/channels": "pages.channels.description",
  "assistant/versions": "navigation.descriptions.assistantVersions",
  "settings/calls": "callSettings.description",
  "settings/reviews": "reviewSettings.description",
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

/** The page title in the browser: "Needs a person · Messages" (the business name follows). */
export function pageTitleKeys(page: BusinessPage): readonly MessageKey[] {
  const section = sectionOf(page);
  const label = pageLabel(page);
  return label === SECTION_LABELS[section] ? [label] : [label, SECTION_LABELS[section]];
}

/** Every page is in exactly one section's list (a unit test keeps the two tables in step). */
export function listedPages(): readonly BusinessPage[] {
  return BUSINESS_SECTIONS.flatMap((section) => SECTION_PAGES[section].map((entry) => entry.page));
}
