/**
 * `adminActions.*` texts of the admin client page's account actions (a
 * longer trial, a discount, credit, the setup fee waived, a payment
 * recorded by hand, a plan set by hand) and of what the team granted, in
 * English: the reference that ru and ka are typed against.
 */

export const adminActionsEn = {
  menu: "Account actions",
  reasonLabel: "Why",
  reasonHint: "The client's audit log keeps it, with your name.",
  reasonShort: "Say why in at least 8 characters.",
  done: "Saved to the client's account",
  autoDebitNote:
    "This client pays automatically: the card keeps being charged the amount agreed at checkout. Discounts and credit apply to bills paid in the cabinet or by bank transfer.",
  extend: {
    action: "Extend the trial",
    title: "Extend the trial of {name}",
    description:
      "A running trial ends later; a trial that ended unpaid starts again from today, its bills are voided and full service comes back.",
    days: "Extra days",
    daysHint: "From 1 to 60 days.",
    daysInvalid: "Enter a whole number of days from 1 to 60.",
    confirm: "Extend",
  },
  discount: {
    action: "Give a discount",
    title: "A discount for {name}",
    description:
      "Periods that start on or before the last day are billed with this much off the price, before tax. A new discount replaces the current one.",
    percent: "Discount, %",
    percentInvalid: "Enter a whole percent from 1 to 100.",
    lastDay: "Last day",
    lastDayHint: "In the client's time zone; at most three years ahead.",
    lastDayInvalid: "Pick a day from today on.",
    confirm: "Give the discount",
  },
  credit: {
    action: "Grant credit",
    title: "Credit for {name}",
    description:
      "Credit comes off the price of the next bills before tax until it is spent. A voided bill gives its credit back.",
    amount: "Amount, {currency}",
    amountInvalid: "Enter an amount above zero (at most two decimals).",
    confirm: "Grant credit",
  },
  waive: {
    action: "Waive the setup fee",
    title: "Waive the setup fee of {name}?",
    description:
      "The unpaid setup fee bill is voided and no setup fee is billed again. A fee already paid is refunded through the payment provider, not here.",
    confirm: "Waive the fee",
  },
  payment: {
    action: "Record a payment",
    title: "Record a payment from {name}",
    description:
      "Money that came outside the card payment pays an open bill now. A paid period brings full service back, as a card payment would.",
    invoice: "Bill",
    noOpenInvoices: "The client has no open bills.",
    method: "How it came",
    methods: {
      bank_transfer: "Bank transfer",
      cash: "Cash",
    },
    reference: "Reference",
    referenceHint: "The bank statement's reference or the cash receipt number.",
    referenceInvalid: "Enter the reference (up to 120 characters).",
    confirm: "Mark as paid",
  },
  plan: {
    action: "Change the plan",
    title: "Change the plan of {name}",
    description:
      "The next bill uses the price book's price, without a checkout. If what is charged changes, automatic payments stop and unpaid bills of the old price are voided; a plan without voice switches the voice agent off.",
    plan: "Plan",
    period: "Billing",
    confirm: "Change the plan",
  },
  account: {
    title: "Granted to the client",
    description: "What the platform team gave this account: the trial, a discount, credit and the setup fee.",
    trialEnds: "Trial ends",
    noTrial: "No trial running",
    discount: "Discount",
    discountActive: "{percent} off periods starting until {date}",
    discountEnded: "{percent}, ended {date}",
    noDiscount: "None",
    credit: "Credit left",
    setupFee: "Setup fee",
    setupFeeWaived: "Waived",
    setupFeeCharged: "Charged when it applies",
    noSubscription: "The client has no subscription yet: account actions wait for one.",
  },
  onboarding: {
    title: "Done-for-you setup requested",
    description: "On {date} the owner asked the platform team to set the business up ({plan}).",
    markDone: "Mark as done",
    marked: "The done-for-you setup is marked done",
  },
} as const;
