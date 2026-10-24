/**
 * `partnerPortal.*` texts of /partner: a partner's links and QR codes,
 * the businesses their links brought and their commissions, in English:
 * the reference that ru and ka are typed against.
 */

export const partnerPortalEn = {
  title: "Partner portal",
  description: "Your links, the businesses they brought and what you earned.",
  rate: "Your commission: {rate} of every invoice those businesses pay, before tax.",
  paused: "Your partnership is paused: new payments earn no commission until the platform team resumes it.",
  legal: "Your contract and how payouts reach you are agreed with the platform team.",
  links: {
    title: "Your links",
    description: "Make a link for each place you share it: the tag shows where sign-ups came from.",
    none: "You have no codes yet: the platform team adds them.",
    source: "Where you share it",
    sourcePlaceholder: "Instagram",
    sourceHint: "Optional. Latin letters, digits, dots, dashes and underscores.",
    sourceInvalid: "Use Latin letters, digits, dots, dashes and underscores only.",
    code: "Code",
    qrLabel: "QR code of the link with {code}",
    showQr: "QR code",
    hideQr: "Hide QR code",
  },
  totals: {
    title: "Commissions",
    businesses: "Businesses brought",
    paying: "Already paid",
    accrued: "To be paid",
    paid: "Paid out",
  },
  businesses: {
    title: "Businesses you brought",
    empty: "No businesses yet. Share your link to bring the first one.",
    signedUp: "Signed up",
    firstPaid: "First payment",
    notYet: "Not yet",
    unnamed: "Business",
  },
  commissions: {
    title: "Commission by invoice",
    empty: "No commissions yet: they appear when a business you brought pays.",
    base: "Invoice before tax",
    status: "Status",
    statuses: {
      accrued: "To be paid",
      paid: "Paid out",
    },
  },
  showMore: "Show more",
  loading: "Loading…",
} as const;
