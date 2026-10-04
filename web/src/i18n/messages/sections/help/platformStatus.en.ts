/**
 * `platformStatus.*` texts: the public status page (/status) and the
 * announcement banner over the cabinet, in English: the reference that ru
 * and ka are typed against.
 */

export const platformStatusEn = {
  title: "Platform status",
  description: "Whether customer chats, channels, calls and the cabinet work right now, and how the last 90 days went.",
  overall: {
    operational: "Everything works",
    maintenance: "Planned maintenance is under way",
    degraded: "Some parts are slower than usual",
    outage: "Some parts do not work right now",
    no_data: "Nothing measured yet",
  },
  levels: {
    operational: "Works",
    maintenance: "Maintenance",
    degraded: "Slow",
    outage: "Not working",
    no_data: "No data",
  },
  components: {
    chat: "Website chat and chat page",
    meta: "WhatsApp, Instagram and Messenger",
    telegram: "Telegram",
    voice: "Phone calls",
    cabinet: "Cabinet and sign-in",
  },
  checkedAt: "Checked {time}",
  componentsTitle: "Parts of the platform",
  historyLabel: "{component}: the last 90 days",
  historyStart: "90 days ago",
  historyEnd: "Today",
  uptime: "{share} of days without trouble",
  noHistory: "No days measured yet",
  day: "{day}: {level}",
  announcementLevels: {
    info: "Notice",
    maintenance: "Maintenance",
    degraded: "Slower",
    outage: "Outage",
  },
  activeTitle: "Now",
  scheduled: "Planned",
  starts: "Starts {time}",
  since: "Since {time}",
  expectedEnd: "Expected to end {time}",
  resolved: "Resolved {time}",
  updated: "Updated {time}",
  affects: "Affects: {components}",
  pastTitle: "Past incidents",
  pastEmpty: "No incidents in the last 90 days.",
  unreachable: {
    title: "The status cannot be loaded",
    body: "This page cannot reach the platform right now. If chats do not work either, write to support: the team already knows.",
  },
  selfMeasured: "The platform checks itself every five minutes; the team adds what it knows.",
  openCabinet: "Open the cabinet",
  banner: {
    region: "Platform announcement",
    details: "Details",
    dismiss: "Hide",
  },
} as const;
