/** `publicPricing.*`: honest prices on the public site (conversions, setup options, testimonials), English. */

export const publicPricingEn = {
  converted: "{price} a month in your currency",
  billedIn: "Plans for this country are billed in {currency}.",
  conversionNote: "≈ amounts are a guide only: converted from euros at {source} as of {date}; you pay in euros.",
  rateSources: {
    nbg: "the official rate of the National Bank of Georgia",
    ecb: "the reference rate of the European Central Bank",
    official: "the official rates of the central banks",
    planning: "the platform's planning rate (not a bank's rate)",
  },
  setup: {
    title: "Set it up yourself, or let us do it",
    subtitle: "The same assistant either way. You choose when you subscribe.",
    selfTitle: "On your own",
    selfPrice: "Free",
    selfPoints: {
      guide: "A guide of eight short steps, with ready answers for your kind of business",
      test: "A test chat and automatic checks before launch",
      channels: "You connect the channels with step-by-step help",
    },
    doneTitle: "Done for you",
    donePrice: "{price} once",
    donePoints: {
      knowledge: "We fill in your prices, menu and rules from your site or files",
      channels: "We connect your channels and phone forwarding",
      launch: "We test the assistant with you and launch it together",
    },
    note: "Done-for-you setup is paid once; on your own it is free.",
  },
  testimonials: {
    title: "What owners say",
  },
} as const;
