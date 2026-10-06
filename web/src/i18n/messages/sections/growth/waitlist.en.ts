/**
 * `waitlist.*` texts: Bookings → Waitlist, the customers waiting for a
 * full day to free up, the place held for one of them, and the owner's
 * choices (keep a waitlist, how long a freed place is held), in English:
 * the reference that ru and ka are typed against.
 */

export const waitlistEn = {
  loading: "Loading the waitlist…",
  filters: {
    label: "Which entries",
    active: "Waiting",
    booked: "Booked",
    ended: "Ended",
  },
  empty: {
    active: "Nobody is waiting",
    activeDescription:
      "When a day is full, the assistant offers to put the customer on the waitlist. A place freed by a cancellation or a move is offered to the first one it fits.",
    booked: "No bookings from the waitlist yet",
    bookedDescription: "Customers who said yes to a freed place show here with their booking.",
    ended: "Nothing has ended yet",
    endedDescription: "Entries end when the customer says no, does not answer in time, or the day passes.",
  },
  customer: "Customer",
  wants: "Wants {date}",
  window: {
    any: "any time",
    between: "{from}–{to}",
    from: "from {from}",
    until: "until {to}",
  },
  nights: { one: "{count} night", other: "{count} nights" },
  status: {
    waiting: "Waiting",
    offered: "Place held",
    booked: "Booked",
    expired: "Ended",
  },
  endReasons: {
    declined: "Said no to the place",
    no_answer: "Did not answer in time",
    date_passed: "The day passed",
    unreachable: "Could not be reached",
    removed: "Taken off the list",
  },
  offer: {
    held: "Held for them: {place}, {time}",
    heldNoPlace: "Held for them: {time}",
    until: "Until {time}",
    minutesLeft: { one: "{count} minute left", other: "{count} minutes left" },
    answerDue: "Waiting for the answer",
  },
  offerCount: { one: "Offered a place {count} time", other: "Offered a place {count} times" },
  joined: "Joined {time}",
  booked: "Booked {time}",
  ended: "Ended {time}",
  openConversation: "Open the conversation",
  remove: "Take off the list",
  removeTitle: "Take {name} off the waitlist?",
  removeBody: "They will not be offered a freed place. A place held for them now goes to the next one in line.",
  removeConfirm: "Take off the list",
  removed: "Taken off the waitlist",
  showMore: "Show more",
  timeZone: "Times are in {timezone}.",
  settings: {
    title: "Waitlist",
    description:
      "A cancelled or moved booking frees a place: it is held for the first customer it fits and offered in their channel and language. A “yes” books it.",
    toggle: "Keep a waitlist",
    off: "The assistant does not offer the waitlist. Customers already on it stay until their day.",
    hold: "Hold a freed place for",
    holdHint: "Without an answer by then, the place goes to the next one in line.",
    holdOption: { one: "{count} minute", other: "{count} minutes" },
    save: "Save",
    saved: "The waitlist settings are saved",
    ownersOnly: "Only an owner can change these settings.",
  },
} as const;
