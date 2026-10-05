/**
 * `customerMemory.*` texts of Settings → General's customer memory card
 * (the assistant recognises returning customers), in English: the
 * reference that ru and ka are typed against.
 */

export const customerMemoryEn = {
  title: "Customer memory",
  description:
    "The assistant recognises customers who come back: it greets them, knows their upcoming bookings and open requests, and remembers what earlier conversations were about.",
  remember: {
    label: "Remember returning customers",
    hint: "Two hours after a conversation goes quiet, a short summary of it is saved. Turned off, no summaries are written and every conversation starts from scratch.",
  },
  notes: {
    label: "Share the team's notes with the assistant",
    hint: "Internal notes on the customer's latest conversations join the memory. The assistant never quotes them to the customer.",
    needsMemory: "Turn on customer memory first.",
  },
  remembers: {
    title: "What the assistant remembers",
    visits: "How often the customer wrote and when they were last here",
    summaries: "What their three latest conversations were about",
    bookings: "Their bookings still to come and the requests your team has not closed",
  },
  bookingsQuestion:
    "In any channel customers can also ask “What time is my booking?”: the assistant looks up their own bookings.",
  privacy:
    "Memory never passes to another business. Erasing a customer's data in Settings → Privacy also erases what the assistant remembered of them.",
  ownerOnly: "Only owners can change this.",
  turnedOn: "The assistant remembers returning customers",
  turnedOff: "Customer memory is off",
  notesShared: "The assistant now reads the team's notes",
  notesHidden: "The team's notes stay with the team",
  loadError: "Customer memory settings could not be loaded.",
} as const;
