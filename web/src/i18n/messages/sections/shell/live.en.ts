/**
 * `live.*` texts: the live cabinet (pages that update by themselves, the
 * "Updated just now" line, the chime and announcement when a customer
 * needs a person), in English: the reference that ru and ka are typed
 * against.
 */

export const liveEn = {
  status: {
    live: "Live",
    connecting: "Connecting…",
    reconnecting: "Reconnecting…",
    paused: "Live updates paused",
  },
  updatedJustNow: "Updated just now",
  updatedMinutesAgo: {
    one: "Updated {count} minute ago",
    other: "Updated {count} minutes ago",
  },
  updatedAt: "Updated at {time}",
  updating: "Updating…",
  liveHint: "This page updates by itself when customers write, book or need a person.",
  reconnectingHint: "The connection dropped and we keep trying. You can also try now.",
  reconnect: "Try now",
  needsPersonTitle: "A customer needs a person",
  needsPersonOpen: "Open",
  needsPersonAnnouncement: "A customer needs a person. {count} waiting.",
  sound: "Chime when someone needs a person",
  soundHint: "A short sound on this device when a conversation is handed to your team.",
} as const;
