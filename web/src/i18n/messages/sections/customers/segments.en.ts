/**
 * `segments.*` texts: saved groups of customers by tag, last visit,
 * booking count and VIP mark, their members and their CSV, in English:
 * the reference that ru and ka are typed against.
 */

export const segmentsEn = {
  loading: "Loading segments…",
  new: "New segment",
  empty: "No segments yet",
  emptyDescription: "Save a group of customers, for example the regulars who have not been back for 60 days, and download it for a campaign.",
  limit: "A business keeps at most 50 segments. Delete one to save another.",
  members: "Customers",
  noMembers: "Nobody matches this segment right now.",
  showMore: "Show more customers",
  export: "Download CSV",
  exportHint: "The customers of the segment with their phones, channels, tags and bookings, for a campaign elsewhere.",
  edit: "Edit",
  delete: "Delete",
  deleteTitle: "Delete the segment “{name}”?",
  deleteBody: "Only the saved rules go; no customer is changed.",
  deleted: "The segment is deleted",
  saved: "The segment is saved",
  editor: {
    newTitle: "New segment",
    editTitle: "Edit the segment",
    name: "Name",
    namePlaceholder: "e.g. Not back in 60 days",
    rules: "Who belongs",
    rulesHint: "Every rule you fill in must hold. Blocked and erased customers never belong.",
    tag: "Tag",
    anyTag: "Any tag",
    lastVisit: "Last visit more than … days ago",
    minBookings: "At least … bookings",
    maxBookings: "At most … bookings",
    vipOnly: "VIP customers only",
    save: "Save the segment",
  },
  errors: {
    name: "Give the segment a name (up to 60 characters).",
    days: "Days are a whole number from 1 to 3650.",
    bookings: "Bookings are a whole number from 0 to 10000.",
    minMax: "“At least” cannot be more than “at most”.",
  },
  preview: {
    counting: "Counting…",
    count: { one: "{count} customer matches", other: "{count} customers match" },
    atLeast: { one: "At least {count} customer matches", other: "At least {count} customers match" },
    none: "Nobody matches yet.",
  },
  summary: {
    everyone: "Every customer",
    tag: "tag “{tag}”",
    lastVisit: { one: "last visit over {count} day ago", other: "last visit over {count} days ago" },
    minBookings: { one: "at least {count} booking", other: "at least {count} bookings" },
    maxBookings: { one: "at most {count} booking", other: "at most {count} bookings" },
    vipOnly: "VIP only",
  },
} as const;
