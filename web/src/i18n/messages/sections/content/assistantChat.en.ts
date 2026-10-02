/**
 * `assistant.*` texts of the test chat, in English: the reference that ru and
 * ka are typed against.
 */

export const assistantChatEn = {
  chat: {
    version: "Version",
    versionOption: "Version {number} · {status}",
    unknownVersion: "Automatic",
    newConversation: "New conversation",
    sandboxNote: "Write as a customer would. Test conversations do not reach customers, staff or billing.",
    sandboxNoteRisky: "You are testing {version}. Test conversations do not reach customers, staff or billing.",
    logLabel: "Test conversation",
    emptyTitle: "Start a test conversation",
    emptyDescription: "Ask what your customers ask, in any language. Or try one of these:",
    suggestions: {
      hours: "What are your opening hours?",
      price: "How much does it cost?",
      booking: "I'd like to book for tomorrow at 7 pm for 4 people",
      human: "Can I talk to a person?",
    },
    typing: "The assistant is writing…",
    inputLabel: "Message",
    placeholder: "Write a message…",
    inputHint: {
      one: "Enter sends, Shift+Enter adds a line. Up to {count} character.",
      other: "Enter sends, Shift+Enter adds a line. Up to {count} characters.",
    },
    send: "Send",
    failed: "Not sent.",
    silent: "The assistant stays silent: the conversation was passed to a person.",
    handedOffTitle: "Passed to a person",
    handedOffDescription: "In a real chat your staff would answer now, so the assistant stays silent. Start a new conversation to keep testing.",
    guardRewritten: "Numbers checked and corrected",
    guardHandedOff: "Passed on: unsure about a number",
    handedOff: "Passed to a person",
    bookingsCreated: { one: "Test booking created", other: "{count} test bookings created" },
    leadsCreated: { one: "Test request created", other: "{count} test requests created" },
    toolCalls: { one: "{count} tool call", other: "{count} tool calls" },
    toolError: "Error",
    toolInput: "Input",
    toolResult: "Result",
    noVersionsTitle: "Nothing to test yet",
    noVersionsDescription: "Build the first version of the assistant from your profile, then talk to it here.",
    errors: {
      service: "The language model is not available right now. Try again in a minute.",
    },
  },
} as const;
