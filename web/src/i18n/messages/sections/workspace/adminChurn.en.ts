/**
 * `adminChurn.*` texts of the platform admin's Metrics page (/admin/metrics):
 * why owners cancel, the offers they took instead, seasonal pauses and the
 * win-back messages. Reason and offer names are `billingLifecycle.*`.
 */

export const adminChurnEn = {
  title: "Why owners cancel",
  description:
    "Cancellations in the period by the reason the owner chose, the offers taken instead, seasonal pauses and the messages sent 14 and 30 days after a cancellation.",
  empty: "No cancellations, offers or pauses in this period.",
  stats: {
    cancellations: "Cancelled",
    saved: "Stayed with an offer",
    pausesScheduled: "Pauses scheduled",
    pausesEnded: "Pauses ended",
    winBackSent: "Win-back messages",
    returned: "Came back after one",
  },
  reason: "Reason",
  cancelled: "Cancelled",
  tookOffer: "Took the offer instead",
  noReason: "Not asked (before the question)",
  offersTitle: "Offers taken",
  commentsTitle: "In the owners' words",
  openClient: "Open the client",
} as const;
