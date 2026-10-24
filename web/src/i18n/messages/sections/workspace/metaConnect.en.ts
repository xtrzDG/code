/**
 * `metaConnect.*` texts in English (the reference the other languages are
 * typed against): "Continue with Facebook" for WhatsApp, Instagram and
 * Messenger, the page picker, Meta's refusals in plain words, the
 * Instagram card's replies to comments and the setup tunnel's Meta card.
 */

export const metaConnectEn = {
  continue: "Continue with Facebook",
  intro: {
    whatsapp:
      "Sign in with Facebook, then choose or create your WhatsApp Business account and number in Facebook's window. We connect the number ourselves.",
    instagram:
      "Sign in with Facebook and pick the page your Instagram professional account is linked to. We connect it ourselves.",
    messenger: "Sign in with Facebook and pick the page whose Messenger chats the assistant answers.",
  },
  orManual: "Already have the ids and key? You can still enter them by hand.",
  preparing: "Getting Facebook ready…",
  starting: "Starting…",
  openWindow: "Open Facebook's window",
  openHint: "Your browser asked us to wait for a click: Facebook's sign-in opens in a new window.",
  waiting: "Finish in Facebook's window. This dialog waits for it.",
  finishing: "Connecting…",
  notices: {
    cancelled: "Facebook's window closed before the end. Try again when you are ready.",
    failed: "Facebook could not finish the signup. Try again, or enter the details manually.",
    unavailable:
      "Facebook's sign-in did not load (an ad or privacy blocker may stop it). Try again later, or enter the details manually.",
  },
  pages: {
    title: "Choose a page",
    hint: "The pages you manage on Facebook.",
    instagramHint: "Only a page linked to an Instagram professional account can connect Instagram.",
    none: "Facebook shows no pages you manage. Start again and tick your business's page in Facebook's window.",
    instagram: "Instagram: @{username}",
    instagramNoName: "Instagram account linked",
    noInstagram: "No Instagram account linked",
    connect: "Connect this page",
    connecting: "Connecting…",
  },
  refusals: {
    meta_link_expired: "This Facebook sign-in has ended. Start again.",
    meta_not_configured: "Facebook sign-in is not set up on this server. Enter the details manually.",
    meta_permission_missing:
      "Facebook did not give every permission we need. Start again and leave all the boxes ticked.",
    whatsapp_account_missing:
      "No WhatsApp Business account came back from Facebook. Start again and choose or create one.",
    whatsapp_number_missing: "That WhatsApp Business account has no phone number yet. Add one in Facebook's window.",
    whatsapp_pin_mismatch:
      "This number has two-step verification with another PIN. Turn it off in WhatsApp Manager, then try again.",
    meta_page_not_found: "Facebook did not give access to this page. Start again and tick it in Facebook's window.",
    instagram_account_missing:
      "This page has no Instagram professional account linked. Link one in Instagram's settings, or pick another page.",
  },
  commentReplies: {
    title: "Replies to comments",
    toggle: "Reply in Direct to comments with a keyword",
    description:
      "When someone writes one of your keywords in a comment under a post, the assistant sends them one message in Direct. At most one a day to each person and 60 an hour.",
    unavailable: "Replies to comments start with the next update of the service. Your settings are kept until then.",
    summaryOn: "On, for: {keywords}",
    summaryOff: "Off",
    keywords: "Keywords",
    keywordsHint: "A word or a short phrase; press Enter after each. Up to 20.",
    keywordInput: "New keyword",
    addKeyword: "Add",
    removeKeyword: "Remove “{keyword}”",
    replyText: "Message in Direct",
    replyHint: "Up to 1000 characters. The customer can answer it, and the assistant carries on.",
    save: "Save",
    saving: "Saving…",
    savedToast: "Replies to comments are saved",
    errors: {
      keywordsMissing: "Add at least one keyword",
      replyMissing: "Write the message",
      keyword: "Up to 50 characters, on one line",
      tooMany: "Up to 20 keywords",
    },
  },
  tunnel: {
    title: "WhatsApp, Instagram and Messenger",
    text: "Connect them with your Facebook account now, or later on the Channels page.",
    connect: "Connect {channel}",
    connected: "Connected",
  },
} as const;
