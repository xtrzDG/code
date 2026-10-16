/**
 * `leads.*` texts of leads (customer requests), in English: the reference that
 * ru and ka are typed against.
 */

export const leadsEn = {
  loading: "Loading leads…",
  status: {
    new: "New",
    in_progress: "In progress",
    won: "Won",
    lost: "Lost",
  },
  type: {
    banquet: "Banquet",
    group: "Group",
    corporate: "Corporate event",
    order: "Order",
    viewing: "Viewing",
    otherRequest: "Other request",
  },
  updated: "Lead moved to “{status}”",
} as const;
