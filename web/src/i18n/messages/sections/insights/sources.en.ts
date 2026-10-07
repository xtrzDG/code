/**
 * `sources.*` texts: Reports → "Where customers came from" (conversations,
 * bookings and value per link, QR code, ad and phone line) and the source
 * chip of the inbox, in English: the reference ru and ka are typed against.
 */

export const sourcesEn = {
  title: "Where customers came from",
  description: "Conversations, bookings and what they are worth per link, QR code, ad and phone line.",
  periodLabel: "Period",
  periods: {
    "7d": "7 days",
    "30d": "30 days",
    "90d": "90 days",
  },
  caption: "Customers per source, {range}",
  columns: {
    source: "Source",
    conversations: "Conversations",
    bookings: "Bookings",
    requests: "Requests",
    value: "Worth",
  },
  untagged: "No tag",
  other: { one: "{count} more tag", other: "{count} more tags" },
  phone: "Call to {number}",
  ad: "Ad",
  adWithId: "Ad {id}",
  total: "Total",
  noValue: "—",
  share: "{percent} of conversations",
  empty: {
    title: "No conversations in this period",
    description: "Sources appear as customers write and call.",
  },
  tagHint: "Give each link and QR code its own tag in Channels → Share, and it shows up here as its own row.",
  tagLink: "Tag your links",
  loading: "Loading the sources…",
} as const;
