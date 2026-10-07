/** `billingLifecycle.*` texts of Settings → Billing: why owners cancel, the offers instead, the seasonal pause. */

export const billingLifecycleEn = {
  reasons: {
    too_expensive: "It costs too much",
    seasonal_break: "We're closed for the season",
    not_enough_use: "Too few customers write or call right now",
    missing_feature: "It can't do something we need",
    answer_quality: "The answers aren't good enough",
    switched_provider: "We're moving to another service",
    closing_business: "We're closing the business",
    somethingElse: "Something else",
  },
  cancel: {
    reasonLegend: "What's the main reason?",
    reasonHint: "It helps us get better, and there may be something that suits you better than cancelling.",
    detailsLabel: "Anything to add?",
    detailsPlaceholder: "In your own words",
    continue: "Continue",
    offerTitle: "Before you go",
    cancelAnyway: "No, cancel anyway",
    back: "Back",
  },
  offerKinds: {
    pause: "Seasonal pause",
    downgrade: "Cheaper plan",
    credit: "One-time credit",
  },
  offers: {
    pause: {
      title: "Take a seasonal break instead",
      description:
        "A paused month costs {price}: the assistant keeps taking requests, your channels stay connected, and full service comes back by itself.",
      confirm: { one: "Pause for {count} month", other: "Pause for {count} months" },
    },
    downgrade: {
      title: "Keep your assistant for less",
      description:
        "“{plan}” costs {price}. Your answers, channels and settings stay as they are; the new price applies from the next invoice.",
      confirm: "Switch to “{plan}”",
    },
    credit: {
      title: "Stay, and {amount} is on us",
      description: "We put {amount} on your account; it comes off your next invoice.",
      confirm: "Take the credit",
    },
    taken: {
      pause: "The pause is scheduled",
      downgrade: "The plan is changed",
      credit: "The credit is on your account",
    },
  },
  pause: {
    title: "Seasonal pause",
    description:
      "Closed for the season? Pause instead of cancelling: the assistant keeps taking requests, your channels stay connected, and full service returns by itself.",
    price: "{price} a month, {percent}% of your plan",
    monthsLegend: "How long",
    months: { one: "{count} month", other: "{count} months" },
    window: "From {start} to {until}",
    submit: "Pause from {date}",
    allowance: "Paused {months} in {window}.",
    allowanceMonths: { one: "{used} of {cap} month", other: "{used} of {cap} months" },
    allowanceWindow: { one: "the last {window} month", other: "the last {window} months" },
    scheduledTitle: "Pause scheduled",
    scheduled:
      "From {start} to {until} the assistant only takes requests. Automatic payments are off; full-price payments start again after the pause.",
    callOff: "Call off the pause",
    calledOff: "The pause is called off",
    pausedTitle: "On pause until {date}",
    paused:
      "The assistant only takes requests; your channels stay connected. Each paused month is billed at {percent}% of your plan.",
    resume: "Resume full service",
    resumeTitle: "Resume full service now?",
    resumeDescription:
      "The assistant answers customers and takes bookings again. If this pause month is already paid, full service returns when it ends; otherwise now, and the next period is due.",
    resumed: "Full service is coming back",
    plansHint: "While paused, the plan stays as it is; resume full service to change it.",
    unavailable: {
      not_active: "A pause is possible for a paid monthly subscription.",
      not_monthly: "A yearly plan cannot be paused.",
      allowance_used: "Four months of pause are used in the last twelve; you can pause again later.",
    },
  },
  facts: {
    pause: "Seasonal pause",
  },
  errors: {
    offerGone: "This offer is no longer available. Close the window and try again.",
    pauseGone: "A pause is not possible right now. Reload the page to see why.",
  },
} as const;
