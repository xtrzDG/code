/**
 * `deposits.*` texts: the deposit that holds a booking until the customer
 * pays it on the owner's own payment page. The chip and the "Paid" action
 * of a booking, the deposit of a table, room or master and of a service,
 * Settings → Deposits (the hold, the refund window, the payment pages, the
 * banquet requests) and the Reports card, in English: the reference the
 * other languages are typed against.
 */

export const depositsEn = {
  chip: "Deposit",
  status: {
    awaiting: "Awaiting payment",
    paid: "Paid",
    expired: "Not paid in time",
    cancelled: "Cancelled",
    refund_due: "Refund due",
    kept: "Kept",
  },
  booking: {
    label: "Deposit",
    heldUntil: "The place is held until {time}",
    reference: "Payment reference: {reference}",
    markPaid: "Paid",
    confirmTitle: "Mark the deposit as paid?",
    confirmDescription:
      "Do it once you see {amount} with the reference {reference} in your merchant account. The booking is then confirmed.",
    confirm: "Yes, it is paid",
    marked: "Deposit marked as paid",
    refundDue: "The booking was cancelled in time: return the deposit in your merchant account.",
  },
  request: {
    linkUntil: "The payment link is valid until {time}",
    confirmDescription: "Do it once you see {amount} with the reference {reference} in your merchant account.",
  },
  policy: {
    title: "Deposit",
    description:
      "Asked on your payment page when this is booked. The amount always comes from here, never from the assistant.",
    rule: "Deposit",
    rules: {
      none: "No deposit",
      fixed: "Fixed amount per booking",
      per_guest: "Amount per guest",
      percent_of_value: "Percent of the booking value",
    },
    amount: "Amount, {currency}",
    amountPerGuest: "Amount per guest, {currency}",
    percent: "Percent of the value",
    minParty: "From how many guests",
    minPartyHint: "Leave it empty to ask every booking.",
    page: "Payment page",
    defaultPage: "The default page",
    pageHint: "A page with one fixed amount fits only a fixed deposit of that amount.",
    save: "Save the deposit",
    saved: "Deposit saved",
    removed: "No deposit is asked now",
    off: "Deposits are off, so nobody is asked yet.",
    noPage: "Add your payment page first.",
    openSettings: "Deposit settings",
    summary: {
      fixed: "Deposit {amount}",
      per_guest: "Deposit {amount} per guest",
      percent_of_value: "Deposit {percent}% of the value",
    },
    fromGuests: { one: "from {count} guest", other: "from {count} guests" },
    errors: {
      percent: "Enter a percent from 1 to 100.",
      minParty: "Enter a whole number of guests, 1 or more.",
    },
  },
  settings: {
    title: "Deposits",
    description:
      "Hold a booking until the customer pays a deposit on your own payment page. The assistant sends your link with the amount you set; it never chooses an amount or a link.",
    toggle: "Ask deposits",
    toggleHint: "Tables, rooms, masters and services with a deposit ask it when they are booked.",
    turnedOff: "Deposits turned off",
    holdMinutes: "Wait for the payment, minutes",
    holdHint:
      "From 15 minutes to a day. A wait of 30 minutes or more sends the customer one reminder halfway; an unpaid place is then let go and the customer is told.",
    refundHours: "Refund when cancelled, hours before the visit",
    refundHint: "Cancelled earlier: you return the deposit. Later, or a no-show: the deposit stays with you.",
    manual:
      "Payments are confirmed by hand: when the money is in your merchant account, open the booking and press “Paid”. Confirmation straight from the payment provider is not connected.",
    errors: {
      hold: "Enter minutes from 15 to 1440.",
      refund: "Enter hours from 0 to 720.",
    },
  },
  pages: {
    title: "Payment pages",
    description:
      "Your own pages where customers pay: Flitt, Stripe Payment Links, TBC, Bank of Georgia or any provider with a link, in any country and currency.",
    empty: "No payment page yet",
    emptyDescription: "Add the link of your payment page. The assistant sends it with the deposit.",
    add: "Add the page",
    label: "Name",
    labelPlaceholder: "Flitt, table deposits",
    kind: "Kind",
    kinds: {
      template: "Fills in the amount",
      static: "One fixed amount",
    },
    kindHints: {
      template: "Put {amount} where the amount goes and {reference} where the payment reference goes.",
      static: "A page that always charges the same amount: it fits only a fixed deposit.",
    },
    address: "Link",
    addressHint: "https only. A link that carries a key is stored encrypted and shown without it.",
    sealed: "Key hidden",
    default: "Default",
    makeDefault: "Make default",
    defaultHint: "The page deposits use unless a table, room, master or service names another one.",
    removeLabel: "Remove {label}",
    removeTitle: "Remove this payment page?",
    removeDescription: "Deposits already asked keep their link. Deposits set to this page use the default one.",
    added: "Payment page added",
    removed: "Payment page removed",
    defaultSet: "Default page changed",
    errors: {
      label: "Enter a name.",
      address: "Enter the link.",
    },
    refusals: {
      linkNotHttps: "The link must start with https://.",
      linkInvalid: "This link cannot be used: check the address.",
      templateInvalid: "A page that fills in the amount needs {amount} in the link, and only {amount}, {amount_minor}, {currency} and {reference} are filled in.",
      noPaymentLink: "Choose one of your payment pages that fills in the amount.",
      depositsOff: "Deposits are off.",
      currencyMismatch: "The deposit must be in the business currency.",
      statusChanged: "This deposit has changed meanwhile: it is no longer waiting for payment.",
    },
  },
  banquet: {
    title: "Banquet requests",
    description: "The deposit a banquet request asks before the team calls back. Leave it off to ask none.",
  },
  report: {
    title: "Deposits",
    description: "The last 30 days: deposits asked and paid, the money collected, and how often guests did not come with a paid deposit and without one.",
    requested: "Asked",
    paid: "Paid",
    awaiting: "Waiting",
    expired: "Not paid in time",
    collected: "Collected",
    refundDue: "To return",
    noShowWith: "No-shows with a paid deposit",
    noShowWithout: "No-shows without a deposit",
    noShowCounts: "{noShows} of {finished} visits",
    notEnoughData: "Not enough data yet: {finished} of {min} finished visits",
    off: "Deposits are off. Turn them on in Settings → Deposits.",
    openSettings: "Deposit settings",
    loading: "Loading deposits…",
  },
} as const;
