/**
 * `referrals.*` texts: an owner's invitation ("Invite a business: a month
 * free for both"), on the Overview card and in the account menu, and the
 * "Powered by" link on the chat, the chat page and the printed card, in
 * English: the reference that ru and ka are typed against.
 */

export const referralsEn = {
  title: "Invite a business — a month free",
  lead: "Share your link with a business you know. When it pays its first invoice, you both get a month of your plans free.",
  terms: "The month comes as credit on your next invoices. Your own other businesses do not count.",
  menu: "Invite a business",
  menuHint: "A month free for both of you",
  linkLabel: "Your invitation link",
  copy: "Copy link",
  share: "Share",
  shareText: "We answer our customers with {app}. Sign up by my link and we both get a month free:",
  showQr: "Show QR code",
  hideQr: "Hide QR code",
  qrLabel: "QR code of your invitation link",
  noLink: "Your invitation link is not ready yet. Try again later.",
  loading: "Loading your invitation…",
  statsLabel: "Your invitations",
  invited: "Signed up",
  paid: "Paid",
  rewarded: "Months earned",
  close: "Close",
  poweredBy: {
    title: "“Powered by” link",
    description: "A small link with your invitation code under the chat, on the chat page and on the printed card.",
    toggle: "Show the “Powered by” link",
    plusOnly: "Taking it off is part of the Plus plan.",
    hidden: "Off: the chat, the page and the card show no link.",
    saved: "Saved",
    footer: "Powered by {app}",
  },
  partnerPortal: "Partner portal",
} as const;
