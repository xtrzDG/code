/**
 * `setup.*` texts: "Create an AI assistant", what the cabinet shows before
 * the assistant exists, in English: the reference that ru and ka are typed
 * against.
 */

export const setupEn = {
  navEntry: "Create an AI assistant",
  navEntryHint: "Step by step, about 10 minutes",
  eyebrow: "{business}",
  title: "Let's create your AI assistant",
  description:
    "Tell us about your business in a few simple steps. We will build an assistant that answers your customers day and night, takes bookings and calls you when a person is needed.",
  start: "Create an AI assistant",
  continue: "Continue creating",
  progress: "{done} of {total} steps done",
  duration: "About 10 minutes. You can stop and come back any time.",
  stagesLabel: "How it goes",
  stages: {
    business: {
      title: "Tell about your business",
      description: "Contacts, opening hours and what you offer.",
    },
    rules: {
      title: "Teach it your rules",
      description: "Bookings, answers to common questions and when to call you.",
    },
    meet: {
      title: "Meet your assistant",
      description: "Try it in a chat, then switch it on for your customers.",
    },
  },
  staffTitle: "The assistant is being created",
  staffDescription:
    "The owner of {business} is setting it up. Conversations, bookings and requests will appear here as soon as it is ready.",
  create: "Create my assistant",
} as const;
