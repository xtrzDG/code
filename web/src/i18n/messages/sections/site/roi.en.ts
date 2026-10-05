/** `roi.*`: the landing page's value calculator, English. */

export const roiEn = {
  title: "What do the requests you miss cost?",
  subtitle: "Count only what arrives when nobody can answer. The rest is simple arithmetic, with your numbers.",
  niche: "Your kind of business",
  missed: "Calls and messages you miss or answer too late, a month",
  missedHint: "A call nobody picked up, a message answered hours later",
  afterHours: "Of them, outside working hours",
  check: "Average check",
  checkHint: "A typical check for this kind of business; change it to yours",
  checkUnknown: "Checks vary a lot here: enter yours",
  conversion: "Requests that become a booking",
  plan: "Compare with the plan",
  percent: "{value}%",
  resultLabel: "The assistant would bring about",
  bookings: {
    one: "{count} more booking a month",
    other: "{count} more bookings a month",
  },
  bookingsUnderOne: "less than one more booking a month",
  perMonth: "{value} a month",
  multiple: "{multiple}× the price of {plan} ({price} a month)",
  belowPrice: "Less than the price of {plan} ({price} a month): count also the time your team saves on answers.",
  breakEven: {
    one: "{count} booking a month pays for the plan",
    other: "{count} bookings a month pay for the plan",
  },
  noCheck: "Enter an average check to see the money.",
  breakdown: {
    label: "How it adds up",
    answered: "Answers outside working hours",
    bookings: "Bookings among them",
    check: "Average check",
  },
  note: "An estimate from your numbers, not a promise. In the cabinet you see the real figures: answered requests, bookings and what they brought.",
  currency: "in {currency}",
} as const;
