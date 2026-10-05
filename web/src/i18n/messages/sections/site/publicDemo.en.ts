/** `publicDemo.*`: the landing page's live demo chat with a demo business, English. */

export const publicDemoEn = {
  label: "Live demo of the assistant",
  badge: "Live demo",
  sampleBadge: "Example",
  sandbox: "Sandbox: nothing is booked for real",
  pick: "Kind of business",
  place: "{niche} · {city}",
  greeting: "Hello! I'm the AI assistant of {business}. Ask me what your customers would ask: prices, opening hours, a booking.",
  starters: "Try asking",
  inputLabel: "Your message to the demo assistant",
  placeholder: "Write as a customer would…",
  send: "Send",
  typing: "The assistant is typing…",
  restart: "Start over",
  you: "You",
  assistant: "Assistant",
  outcomes: {
    booking: "Here a booking would be made",
    request: "Here the request would go to your manager",
    handoff: "Here the conversation would go to a person",
  },
  messagesLeft: {
    one: "{count} message left this hour",
    other: "{count} messages left this hour",
  },
  failures: {
    limit: "The demo has had a lot of messages. Try again a little later, or create your own assistant: it takes about ten minutes.",
    unavailable: "This demo is resting right now. Try another kind of business.",
    offline: "No connection. Check the internet and try again.",
    failed: "The message did not go through. Try again.",
  },
  privacy: "A public demo: please do not share personal details.",
  cta: "Create my own",
} as const;
