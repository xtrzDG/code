/**
 * `navigation.*` texts: the five sections of a business, their pages, the
 * sidebar and the phone tab bar, in English: the reference that ru and ka
 * are typed against.
 */

export const navigationEn = {
  sections: {
    overview: "Overview",
    inbox: "Inbox",
    bookings: "Bookings",
    assistant: "Assistant",
    settings: "Settings",
  },
  descriptions: {
    overview: "How your assistant is doing and what needs you today.",
    inbox: "Every conversation in one place: the customers waiting for a person, requests, and who of the team handles what.",
    bookings: "Bookings with their statuses; add one by hand.",
    assistant: "Try your assistant, teach it, choose where it answers and apply your changes.",
    settings: "Your business, team, notifications, quick replies, calls, reviews, plan, privacy and the audit log.",
    assistantTest: "Write as a customer would. Nothing reaches real customers.",
    assistantProfile: "What your assistant knows about the business: the place, the offer, hours and bookings, people and rules. Changes save as you type.",
    assistantVersions: "Every update of the assistant: when customers got it, its checks and a way back.",
    assistantChecks: "Questions with what the answer must do, asked in every “Apply changes”.",
  },
  pages: {
    overviewDashboard: "Dashboard",
    overviewReports: "Reports",
    assistantTest: "Try it",
    assistantKnowledge: "Knowledge",
    assistantProfile: "Business profile",
    assistantChannels: "Channels",
    assistantVersions: "History",
    assistantChecks: "My checks",
    settingsGeneral: "Business",
    settingsTeam: "Team",
    settingsNotifications: "Notifications",
    settingsQuickReplies: "Quick replies",
    settingsCalls: "Calls",
    settingsReviews: "Reviews",
    settingsBilling: "Plan and billing",
    settingsPrivacy: "Privacy",
    settingsAudit: "Audit log",
  },
  sectionPages: "Pages of {section}",
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
