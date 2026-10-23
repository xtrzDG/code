/** `billingCard.*` texts of Settings → Billing: the card on file, the retries of a declined payment and the trial's "Save card" prompt. */

export const billingCardEn = {
  title: "Card for payments",
  description: "The subscription's automatic payments go to this card.",
  endingIn: "Card ending in {digits}",
  expires: "Expires {date}",
  noExpiry: "Expiry not reported",
  expiryStates: {
    expired: "Expired",
    expiring: "Expires soon",
  },
  facts: {
    provider: "Payment service",
    savedAt: "Saved on",
  },
  noCard: "No card saved yet",
  noCardTrial: "Save a card and the subscription carries on by itself when the trial ends.",
  noCardPaid: "Save a card so the next payments go through by themselves.",
  cardWithoutDetails: "A card is saved with {provider}. Its details show here after the next payment.",
  expiredHint: "This card has expired. Save a new one before the next payment.",
  expiringHint: "This card expires soon. Save a new one so the next payment goes through.",
  noCharge: "Saving a card charges nothing: the payment service only checks it.",
  payToSave: "Paying the open bill saves the card you pay with.",
  setupFeeNow: "Saving the card charges the one-time setup fee of {amount} now. The monthly payments start when the trial ends.",
  retryUsesNewCard: "The next try charges the card you save.",
  save: "Save card",
  update: "Update card",
  opening: "Opening…",
  retry: {
    title: "The automatic payment didn't go through",
    declined: "The card was declined. We'll try it again by ourselves.",
    outcomes: {
      claimed: "Try {attempt} of {total} is under way.",
      approved: "Try {attempt} of {total} went through. The payment is being confirmed.",
      declined: "Try {attempt} of {total} was declined.",
      processing: "Try {attempt} of {total} is being processed.",
      failed: "Try {attempt} of {total} didn't reach the payment service.",
      not_possible: "Try {attempt} of {total} wasn't possible: there is no saved card to charge.",
      skipped: "Try {attempt} of {total} was skipped.",
    },
    next: "Next try: {date}",
    noMore: "No more tries. From {date} the assistant only takes requests.",
  },
  trialPrompt: {
    title: { one: "{count} day of the trial left", other: "{count} days of the trial left" },
    body: "Nothing is charged until {date}: save a card now and the assistant keeps answering after the trial.",
    bodyWithSetupFee: "Save a card now: it pays the one-time setup fee of {amount}, and from {date} the monthly payments go to it. The assistant keeps answering after the trial.",
  },
  returned: {
    title: "Saving your card",
    pending: "The card shows here once the payment service confirms it, usually within a minute.",
    savedTitle: "Card saved",
    saved: "The automatic payments now go to this card.",
  },
  errors: {
    cannotSave: "A card can't be saved now. Pay the open bill instead: that saves the card you pay with.",
  },
} as const;
