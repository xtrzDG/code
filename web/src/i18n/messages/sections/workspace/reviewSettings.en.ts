/**
 * `reviewSettings.*` texts of Settings → Reviews (feedback after visits,
 * the Google review link, the numbers of the last 30 days, the template
 * text and the latest requests), in English: the reference that ru and ka
 * are typed against.
 */

export const reviewSettingsEn = {
  description: "Ask customers how their visit went, invite everyone to review you on Google, and see what they answered.",
  stats: {
    title: "Last 30 days",
    description: "Customers asked about their visit, and what they answered.",
    asked: "Asked",
    answered: "Answered",
    answeredShare: "{percent} of those asked",
    average: "Average rating",
    averageValue: "{score} of 5",
    noAverage: "No ratings yet",
    opened: "Opened the review link",
    notTracked: "Not counted on this platform",
    scores: "Ratings",
    scoreRow: { one: "{score} star: {count}", other: "{score} stars: {count}" },
    notAsked: "Not asked: {count}",
    notDelivered: "Not delivered: {count}",
  },
  feedback: {
    title: "Feedback after visits",
    description:
      "After a completed visit we ask the customer to rate it from 1 to 5, in the messenger they used and in their language. The platform answers the rating itself: it thanks them and sends your review link.",
    toggle: "Ask customers how their visit went",
    delay: "When to ask",
    delayHint: "Counted from the end of the booking.",
    delayMinutes: { one: "{count} minute after the visit", other: "{count} minutes after the visit" },
    delayHours: { one: "{count} hour after the visit", other: "{count} hours after the visit" },
    delayDays: { one: "{count} day after the visit", other: "{count} days after the visit" },
    template: "WhatsApp template name",
    templateHint:
      "For WhatsApp customers who have not written for 24 hours: the approved utility template on your number (lowercase Latin letters, digits and underscores).",
    templateInvalid: "Use lowercase Latin letters, digits and underscores only.",
    readiness: {
      off: "Feedback requests are off.",
      everywhere: "Customers are asked in Telegram, WhatsApp, Messenger and Instagram; WhatsApp customers quiet for a day get your template.",
      window: "Customers are asked within 24 hours of their last message; WhatsApp customers quiet for longer are skipped until the template is set.",
    },
    whatsappMissing: "WhatsApp is not connected.",
    connectWhatsapp: "Connect WhatsApp",
    rules:
      "Each visit is asked about once, and each customer at most once a day. Customers who replied STOP get no requests. A rating of 3 or less also goes to Inbox → Needs a person, so someone gets in touch.",
  },
  link: {
    title: "Google review link",
    description:
      "Everyone who answers gets this link with the thank-you, whatever their rating: inviting only happy customers is against Google's rules.",
    label: "Link to your Google review page",
    hint: "In Google Business Profile, choose “Ask for reviews” and copy the link.",
    invalid: "Enter a full link that starts with https://",
    tracked: "We send it through the platform's short address to count how many customers open it.",
    missing: "Without a link, customers are only thanked.",
  },
  save: "Save",
  saved: "Review settings saved",
  template: {
    title: "Template text",
    description:
      "Create a WhatsApp utility template with this text in Meta Business Manager, one translation per language; its only parameter is your business name. Customers get it in their language, or in English when there is no translation.",
    body: "Text for the template",
    example: "What customers read",
  },
  requests: {
    title: "Latest requests",
    description: "The last 20 visits we asked about, and what customers answered.",
    empty: "No requests yet",
    emptyDescription: "Customers are asked after their visits once feedback is on.",
    customer: "Customer",
    visitEnded: "Visit ended {time}",
    rating: "Rated {score} of 5",
    openedLink: "Opened the review link",
    openConversation: "Open conversation",
    notAskedBecause: "Not asked: {reason}",
    statuses: {
      sent: "Waiting for a reply",
      answered: "Answered",
      skipped: "Not asked",
      failed: "Not delivered",
    },
    skipReasons: {
      opted_out: "the customer replied STOP",
      no_contact: "the customer's details were erased",
      no_channel: "no messenger to write to",
      window_closed: "WhatsApp needs the approved template after 24 hours",
      already_asked: "already asked today",
      daily_limit: "the daily limit of messages was reached",
    },
  },
};
