/**
 * `platformBrakes.*` texts of the admin System page's platform brakes card
 * (the global pause of every assistant, the daily budget stop), payment
 * reconciliation card and card of the campaigns held over their opt-out
 * rate, in English: the reference the other languages are typed against.
 */

export const platformBrakesEn = {
  brakes: {
    title: "Platform brakes",
    description:
      "Pausing stops every assistant at once: customers read, in their language, that a colleague takes over, and calls go to the business's staff phone. The daily budget stop does the same until UTC midnight.",
    states: {
      running: "Assistants answer",
      paused: "Every assistant is paused",
      stopped: "Daily budget stop holds",
    },
    pausedSince: "Paused since {time}",
    reason: "Reason:",
    budget:
      "Today {percent}% of the daily budget is spent; the assistants stop at {stop}%.",
    noBudget: "No daily budget is set: nothing stops the assistants.",
    pause: "Pause every assistant",
    resume: "Resume every assistant",
    pauseTitle: "Pause every assistant?",
    pauseDescription:
      "Every business's assistant stops answering at once. Customers are handed to the team and calls go to the staff phone until you resume. The audit log keeps your reason.",
    resumeTitle: "Resume every assistant?",
    resumeDescription:
      "Every business's assistant answers again at once. The audit log keeps your reason.",
    paused: "Every assistant is paused",
    resumed: "The assistants answer again",
  },
  reconciliation: {
    title: "Payment reconciliation",
    description:
      "Once a day the payments of the last week are compared with Flitt and Stripe. A difference is never corrected automatically: check it at the provider.",
    notYet: "No reconciliation has run yet today or yesterday.",
    summary:
      "Ran {time}: {checked} payments compared, {unreadable} could not be read.",
    allMatch: "Every payment matches the provider",
    differs: "Differences found",
    client: "Client",
    provider: "Provider",
    recorded: "Here",
    atProvider: "At the provider",
    kind: "Difference",
    providers: {
      flitt: "Flitt",
      stripe: "Stripe",
    },
    statuses: {
      created: "Created",
      processing: "Processing",
      approved: "Paid",
      declined: "Declined",
      expired: "Expired",
      reversed: "Refunded",
    },
    kinds: {
      paid_at_provider: "Paid at the provider, unpaid here",
      failed_at_provider: "Failed at the provider, paid here",
      reversed_at_provider: "Refunded at the provider, paid here",
      renewal_paid_at_provider:
        "Renewal paid at the provider, not recorded here",
    },
  },
  campaignHolds: {
    title: "Campaigns held for review",
    description:
      "A client's return-visit campaign stops writing when 5% or more of at least 40 customers it wrote to in 30 days asked for no more messages. Agree on a narrower audience with the owner before you lift the hold; after that only the messages sent since count.",
    client: "Client",
    heldSince: "Held since",
    optedOut: "Opted out",
    optedOutOf: "{optedOut} of {sent}",
    release: "Lift the hold",
    releaseTitle: "Lift the hold on this campaign?",
    releaseDescription:
      "The campaign writes to the client's customers again from its next hourly run, and the owners are told. The client's audit log keeps your reason.",
    released: "The campaign writes again",
  },
};
