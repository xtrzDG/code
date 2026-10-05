/**
 * `privacyNotice.*`: the platform's default privacy notice for a business's
 * chat (/c/{address}/privacy), shown when the business has not linked its
 * own. Customers read it; `{business}` is the business's name. English is
 * the reference that ru and ka are typed against.
 */

export const privacyNoticeEn = {
  title: "Privacy notice",
  subtitle: "How {business} handles what you write in its chat",
  whoTitle: "Who answers",
  who: "{business} answers messages with an AI assistant, on its website, on this page and in messengers. Assistant Workshop provides the assistant and handles your messages for {business}, which decides what is done with them.",
  whatTitle: "What is kept",
  whatMessages: "What you write in the chat and the assistant's answers.",
  whatContacts: "Your name, phone number or e-mail, if you give them (for example, for a booking or a call back).",
  whatBrowser: "A random key in your browser's storage, so the chat continues where you left it. The chat sets no cookies.",
  whatTechnical: "Technical data such as your IP address, kept for a short time to protect the chat from abuse.",
  whyTitle: "Why",
  why: "To answer your questions, take bookings and requests, and pass the conversation to the staff of {business} when you ask for a person or the assistant cannot help.",
  sharedTitle: "Who sees it",
  shared: "The staff of {business}. To write answers, the text of the conversation is processed by the AI model provider the assistant runs on, only for that purpose.",
  keptTitle: "How long",
  kept:
    "{business} keeps conversations for {conversations} after their last message, then they are deleted automatically, and the records of the assistant's AI calls for {modelRecords}. You can ask it to delete yours at any time.",
  rightsTitle: "Your choices",
  rights: "You can ask {business} what it keeps about you, and to correct or delete it: write in the chat or contact the business directly. The assistant can make mistakes, so check important details (prices, times) with the business.",
  platformNote: "This is the default notice of the Assistant Workshop platform. {business} may publish its own.",
  backToChat: "Back to the chat",
} as const;
