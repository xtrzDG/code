/**
 * `tunnel.*`: the frame of "Create an AI assistant" (/create and
 * /b/{id}/setup): the steps' names on the progress rail, moving between
 * them, saving, and what screen readers hear. English is the reference
 * that ru and ka are typed against.
 */

export const tunnelEn = {
  pageTitle: "Create an AI assistant",
  newAssistant: "New assistant",
  railLabel: "Setup steps",
  steps: {
    business: "Your business",
    place: "Where you are",
    offer: "What you offer",
    hours: "Hours and bookings",
    people: "Who helps",
    channels: "Where customers write",
    try: "Try it",
    launch: "Launch",
  },
  stepOf: "Step {number} of {total}",
  stepState: {
    done: "done",
    skipped: "skipped",
    current: "you are here",
    todo: "not yet",
  },
  announce: "Step {number} of {total}: {title}",
  announceFinale: "Your assistant is live",
  back: "Back",
  continue: "Continue",
  skip: "Skip for now",
  enterHint: "or press Enter",
  exit: "Save and exit",
  exitShort: "Exit",
  saving: "Saving…",
  saved: "Saved",
  saveFailed: "Not saved yet",
  loadFailed: "We couldn't open your setup. Check the connection and try again.",
  ownerOnlyTitle: "The owner is creating the assistant",
  ownerOnlyText: "Only an owner of {business} can set it up. Conversations, bookings and requests appear in the cabinet once it is live.",
  openCabinet: "Open the cabinet",
} as const;
