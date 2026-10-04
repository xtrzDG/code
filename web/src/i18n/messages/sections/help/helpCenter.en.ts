/**
 * `helpCenter.*` texts: the help center (/help), the article drawer behind a
 * page's "?", and "Help and support" in the account panel, in English: the
 * reference that ru and ka are typed against.
 */

export const helpCenterEn = {
  title: "Help",
  description: "Short guides to every part of the cabinet. Cannot find an answer? Write to us.",
  searchLabel: "Search the help",
  searchPlaceholder: "Telegram, booking, invoice…",
  search: "Search",
  clearSearch: "Clear the search",
  results: {
    one: "{count} article found",
    other: "{count} articles found",
  },
  noResults: "Nothing found for “{query}”. Try another word, or write to us.",
  topics: {
    getting_started: "Getting started",
    channels: "Channels",
    daily_work: "Daily work",
    account: "Account and billing",
  },
  loadFailed: "The help could not be loaded. Check the connection and try again.",
  allArticles: "All articles",
  related: "Read next",
  otherLanguage: "This article is not translated yet, so it is shown in {language}.",
  pageHelp: "Help for this page",
  drawerTitle: "Help",
  openInCenter: "Open in the help center",
  back: "Back",
  stillStuck: "Still stuck?",
  stillStuckLead: "Write to us: a person from the team answers.",
  tipsAgain: "Show tips again",
  tipsShown: "The tips will show again on the Inbox, Assistant and Channels pages.",
  opensInNewTab: "opens in a new tab",
  support: {
    title: "Help and support",
    center: "Help center",
    whatsNew: "What's new",
    unread: {
      one: "{count} new",
      other: "{count} new",
    },
    status: "Platform status",
    contact: "Write to support",
    whatsapp: "WhatsApp",
    telegram: "Telegram",
    email: "E-mail",
  },
} as const;
