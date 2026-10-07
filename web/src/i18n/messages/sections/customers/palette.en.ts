/**
 * `palette.*` texts: the command palette (Cmd/Ctrl+K) that finds pages,
 * customers, conversations and bookings, in English: the reference that
 * ru and ka are typed against.
 */

export const paletteEn = {
  title: "Search and go",
  open: "Search",
  openTitle: "Search (Ctrl+K or ⌘K)",
  placeholder: "Find a customer, conversation, booking or page",
  groups: {
    navigation: "Go to",
    customers: "Customers",
    conversations: "Conversations",
    bookings: "Bookings",
  },
  searching: "Searching…",
  noResults: "Nothing found for “{text}”.",
  resultCount: { one: "{count} result", other: "{count} results" },
  typeMore: "Type two letters or more to search customers, conversations and bookings.",
  searchFailed: "The search did not answer; the pages are still here.",
  keys: "↑ ↓ to move · Enter to open · Esc to close",
  unnamed: "Customer without a name",
  conversationDetail: "{channel} · {date}",
  bookingDetail: "{date} · {guests}",
  partySize: { one: "{count} guest", other: "{count} guests" },
} as const;
