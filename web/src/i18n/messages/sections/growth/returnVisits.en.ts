/**
 * `returnVisits.*` texts: Bookings → Return visits (owners), the opt-in
 * message that brings customers back (an invitation after a visit, a
 * reminder that a check is due, a note before arrival), who may get it,
 * the monthly cap, what customers read and the latest messages, in
 * English: the reference that ru and ka are typed against.
 */

export const returnVisitsEn = {
  loading: "Loading return visits…",
  rules: {
    rebook: "An invitation back",
    recall: "A reminder that a check is due",
    pre_arrival: "A note before arrival",
  },
  ruleHints: {
    rebook: "Sent the chosen number of days after a customer's last visit, unless they have booked again.",
    recall: "Sent the chosen number of days after the last visit, for a regular check or service.",
    pre_arrival: "Sent the chosen number of days before a booking starts, with a reminder of the date.",
  },
  settings: {
    title: "Return-visit messages",
    description: "One message to bring customers back, in their channel and language. Nothing is sent until you turn it on.",
    toggle: "Send return-visit messages",
    rule: "What to send",
    daysAfter: "Days after the last visit",
    daysBefore: "Days before arrival",
    suggested: {
      one: "Usual for your kind of business: “{rule}” after {count} day.",
      other: "Usual for your kind of business: “{rule}” after {count} days.",
    },
    suggestedBefore: {
      one: "Usual for your kind of business: “{rule}” {count} day before.",
      other: "Usual for your kind of business: “{rule}” {count} days before.",
    },
    useSuggested: "Use it",
    audience: "Who may get it",
    audiences: {
      all_customers: "Every customer the rule finds",
      segment: "Only the customers of one segment",
    },
    segment: "Segment",
    chooseSegment: "Choose a segment",
    noSegments: "There are no saved segments yet.",
    toSegments: "Create one in Customers → Segments",
    cap: "At most a month",
    capHint: "The messages stop for the rest of the month at this number.",
    monthSent: { one: "{count} message sent this month, of {cap}", other: "{count} messages sent this month, of {cap}" },
    honours:
      "Customers who wrote STOP, are on the do-not-contact list or are blocked never get it. A customer gets at most one such message every two weeks, and none after booking again.",
    whatsapp:
      "On WhatsApp, a customer who has not written for 24 hours gets the platform's approved template for invitations and reminders; a note before arrival waits for an open conversation.",
    save: "Save",
    saved: "Return-visit messages are saved",
    errors: {
      days: "Days are a whole number from 1 to 730.",
      cap: "The monthly cap is a whole number from 1 to 2000.",
      segment: "Choose a segment, or write to every customer the rule finds.",
    },
  },
  recent: {
    title: "The last 30 days",
    sent: "Sent",
    booked: "Booked again",
    skipped: "Not sent",
  },
  preview: {
    title: "What customers read",
    description: "The message in each language of your business, with the date filled in as it would be today.",
  },
  messages: {
    title: "Latest messages",
    description: "Who got a message and who booked again after it.",
    empty: "No messages yet",
    emptyDescription: "When the messages are on, an hourly check writes to the customers who are due.",
    customer: "Customer",
    status: {
      sent: "Sent",
      booked: "Booked again",
      skipped: "Not sent",
    },
    skipReasons: {
      opted_out: "they asked not to be written to",
      no_contact: "the customer is unknown or erased",
      no_channel: "there is no channel to reach them",
      window_closed: "the 24-hour window is closed and there is no template",
    },
    notSentBecause: "Not sent: {reason}",
    sentAt: "Sent {time}",
    bookedAt: "Booked {time}",
    openConversation: "Open the conversation",
    showMore: "Show more",
  },
} as const;
