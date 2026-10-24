/**
 * `channelPages.*` texts of the Channels pages on a phone: the links from
 * the channel cards to the website chat's look and code, call forwarding
 * and sharing, each a page of its own, in English: the reference that ru
 * and ka are typed against.
 */

export const channelPagesEn = {
  heading: "Set up",
  back: "All channels",
  website: {
    title: "Website chat",
    hint: "Colour, button, the code for your site and where it may show",
  },
  calls: {
    title: "Call forwarding",
    hint: "Codes that send the calls you miss to the assistant",
  },
  share: {
    title: "Share",
    hint: "Links, a QR code and a table card",
  },
  off: {
    website: "The website chat is off. Turn it on among the channels to choose its look and put it on your site.",
    calls: "The phone channel is not connected. Connect it among the channels to get your forwarding codes.",
  },
} as const;
