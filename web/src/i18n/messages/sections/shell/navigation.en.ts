/**
 * `navigation.*` texts: the five sections of a business, their pages, the
 * sidebar and the phone tab bar, in English: the reference that ru and ka
 * are typed against.
 */

export const navigationEn = {
  sections: {
    overview: "Overview",
    messages: "Messages",
    bookings: "Bookings",
    assistant: "Assistant",
    settings: "Settings",
  },
  descriptions: {
    overview: "How your assistant is doing and what needs you today.",
    messages: "Every conversation, the ones waiting for a person and customers' requests, in one place.",
    bookings: "Bookings with their statuses; add one by hand.",
    assistant: "Try your assistant, teach it, choose where it answers and apply your changes.",
    settings: "Your business, team, notifications, calls, reviews, plan, privacy and the audit log.",
    assistantTest: "Write as a customer would. Nothing reaches real customers.",
    assistantProfile: "Contacts, opening hours, what you offer, booking rules and when to call a person: the profile your assistant follows.",
    assistantVersions: "Every update of the assistant with its checks, publishing and a way back.",
  },
  pages: {
    overviewDashboard: "Dashboard",
    overviewReports: "Reports",
    messagesAll: "All conversations",
    messagesHandoffs: "Needs a person",
    messagesLeads: "Requests",
    assistantTest: "Try it",
    assistantKnowledge: "Knowledge",
    assistantProfile: "Hours and rules",
    assistantChannels: "Channels",
    assistantVersions: "Updates and checks",
    settingsGeneral: "Business",
    settingsTeam: "Team",
    settingsNotifications: "Notifications",
    settingsCalls: "Calls",
    settingsReviews: "Reviews",
    settingsBilling: "Plan and billing",
    settingsPrivacy: "Privacy",
    settingsAudit: "Audit log",
  },
  sectionPages: "Pages of {section}",
  applyChanges: "Apply changes",
  applyChangesHint: "Prepare an update from the profile and knowledge, check it and publish it when it passes.",
  advanced: "Advanced",
  collapse: "Collapse the menu",
  expand: "Expand the menu",
  tabBar: "Sections",
  more: "More",
  waiting: {
    one: "{count} waiting",
    other: "{count} waiting",
  },
  ownerOnlyTitle: "This page is for owners",
  ownerOnlyDescription: "Your role in {business} does not include it. Ask an owner if something here needs changing.",
  toOverview: "Go to the overview",
} as const;
