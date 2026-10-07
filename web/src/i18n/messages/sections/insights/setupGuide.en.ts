/**
 * `setupGuide.*`: the Overview's setup guide (the steps of the setup, then
 * a test from the owner's phone, a second channel and the link for
 * customers), the progress ring in the bar and the milestone toasts.
 * English is the reference that ru and ka are typed against.
 */

export const setupGuideEn = {
  titleSetup: "Set up your assistant",
  titleLive: "Bring in the first customers",
  descriptionSetup: "Each step opens where you left off. The assistant answers customers once it is published.",
  liveSince: "Answering customers since {date}",
  minutesLeft: { one: "about {count} minute left", other: "about {count} minutes left" },
  continueSetup: "Continue setup",
  afterLaunchHint: "After the launch: a test from your phone, a second channel and the link for customers.",
  minutes: "{count} min",
  optional: "optional",
  skip: "Skip",
  unskip: "Bring back",
  skipLabel: "Skip “{step}”",
  unskipLabel: "Bring back “{step}”",
  status: {
    next: "Next",
    skipped: "Skipped",
  },
  phone: {
    description: "Point your phone camera at the code and write to the assistant the way a customer would.",
    qrAlt: "QR code of {link}",
    copyLink: "Copy link",
    unavailable: "The chat page is off. Turn on the website chat in Channels, or write from your phone to a connected messenger.",
    orTelegram: "Or in Telegram:",
    listening: "Waiting for your message…",
    hint: "The step is done when your message arrives.",
    success: "It works: your message reached the assistant.",
    hide: "Hide",
  },
  finished: {
    title: "All set",
    description: "The assistant answers customers, and they know where to find it.",
    dismiss: "Hide this card",
  },
  wins: {
    title: "Reached",
    first_conversation: "First customer conversation",
    first_booking: "First booking",
    first_after_hours_booking: "First booking after hours",
  },
  ring: {
    title: "Setup",
    label: "Setup {percent}% done",
    short: "{percent}%",
  },
  celebrations: {
    first_conversation: {
      title: "The first customer wrote in",
      description: "The assistant answered. The conversation is in the inbox.",
    },
    first_booking: {
      title: "The first booking",
      description: "The assistant booked a customer by itself.",
    },
    first_after_hours_booking: {
      title: "A booking while you were closed",
      description: "A customer booked after hours, and nobody had to pick up.",
    },
    openInbox: "Open inbox",
    openBookings: "Open bookings",
    close: "Close",
  },
} as const;
