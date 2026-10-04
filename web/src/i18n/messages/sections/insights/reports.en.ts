/**
 * `reports.*` texts: Overview → Reports (the month so far, stored monthly
 * reports and digests, the owner's summaries), in English: the reference
 * that ru and ka are typed against.
 */

export const reportsEn = {
  description: "What the assistant did each month and week, and the summaries you get about it.",
  loading: "Loading the reports…",
  opened: "From your summary",
  past: "Past reports",
  kindLabel: "Kind of report",
  kinds: {
    monthly: "Monthly",
    weekly: "Weekly",
    daily: "Daily",
  },
  empty: {
    title: "No reports yet",
    monthly: "The first monthly report is made on the 1st, about the month before.",
    weekly: "Weekly digests are made on Mondays, about the week before.",
    daily: "Daily digests are made each morning for owners who turned them on.",
  },
  monthSoFar: {
    title: "This month so far",
    next: "The full report arrives on {date}",
  },
  summary: {
    bookings: { one: "{count} booking", other: "{count} bookings" },
    requests: { one: "{count} request", other: "{count} requests" },
  },
  delivery: {
    sent: { one: "Sent to {count} owner", other: "Sent to {count} owners" },
    quiet: "Not sent: a quiet period",
    noRecipients: "Nobody had it turned on",
  },
  details: {
    toggle: "All numbers",
    caption: "The report's numbers against the period before",
    measure: "What",
    change: "Change",
    before: "before: {value}",
    noCheck: "No average check was set, so the report has no money estimate.",
    ownerCheck: "Money estimated with your average check of {money}.",
    typicalCheck: "Money estimated with the typical check of {money} for your kind of business.",
    bookedPrices: "Money from the prices of what was booked.",
    mixedCheck: "Money from the prices of what was booked; bookings without a price at the average check of {money}.",
  },
  rows: {
    assistantBookings: "Bookings by the assistant",
    estimate: "Worth (estimate)",
    staffTime: "Staff time saved",
    afterHours: "Conversations after hours",
    conversations: "Conversations",
    customerMessages: "Customer messages",
    assistantReplies: "Replies by the assistant",
    calls: "Calls answered",
    bookings: "All bookings",
    requests: "Requests",
    handoffs: "Needed a person",
  },
  duration: {
    hoursMinutes: "{hours} h {minutes} min",
    minutes: "{minutes} min",
  },
  digests: {
    title: "Your summaries",
    description: "What the assistant did, sent to you in your language with a link back here.",
    monthly: "Monthly report",
    monthlyHint: "On the 1st at 9:00, about the month before",
    weekly: "Weekly digest",
    weeklyHint: "On Mondays at 9:00, about the week before",
    daily: "Daily digest",
    dailyHint: "Every morning at 9:00, about the day before",
    email: "By e-mail to {email} and to your devices.",
    emailNotReady: "E-mail is not set up on this platform yet, so summaries go to your devices only.",
    noEmail: "You sign in by phone, so summaries go to your devices only.",
    devices: { one: "{count} device has notifications on.", other: "{count} devices have notifications on." },
    noDevices: "No device has notifications on yet.",
    manageDevices: "Notification settings",
  },
} as const;
