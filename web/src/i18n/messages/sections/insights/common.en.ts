/**
 * `insights.*` texts of shared by the dashboard, conversations, bookings,
 * leads and handoffs, in English: the reference that ru and ka are typed
 * against.
 */

export const insightsCommonEn = {
  loadingMore: "Loading…",
  showMore: "Show more",
  shownOf: "Showing {shown} of {total}",
  includeTest: "Include test activity",
  includeTestHint: "From the test chat and autotests",
  testBadge: "Test",
  afterHours: "After hours",
  unknownCustomer: "Customer without a name",
  callPhone: "Call {phone}",
  openConversation: "Open the conversation",
  all: "All",
  clearFilters: "Clear filters",
  noMatchesTitle: "Nothing matches the filters",
  noMatchesDescription: "Change or clear the filters to see more.",
  copy: "Copy",
  copied: "Copied to the clipboard",
  copyFailed: "Could not copy. Select the text and copy it by hand.",
  customerMessage: {
    title: "Message for the customer",
    description: "The assistant does not send this text by itself here. Send it to the customer in the channel you talk in.",
  },
  channels: {
    phone: "Phone",
    whatsapp: "WhatsApp",
    instagram: "Instagram",
    messenger: "Messenger",
    telegram: "Telegram",
    web_chat: "Website chat",
    viber: "Viber",
    owner_test: "Test chat",
  },
} as const;
