/**
 * `leads.*` texts of leads (customer requests), in English: the reference that
 * ru and ka are typed against.
 */

export const leadsEn = {
  loading: "Loading leads…",
  tabsLabel: "Lead status",
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
  statusOf: "Status of the lead from {name}",
  statusLabel: "Status",
  requestedDate: "Date",
  partySize: "People",
  budget: "Budget",
  source: "Source",
  received: "Received",
  details: "Details",
  showDetails: "Details",
  contact: "Customer",
  updated: "Lead moved to “{status}”",
  emptyTitle: "No leads yet",
  emptyDescription: "When a customer asks for something the assistant does not book itself (a banquet, a group, an order), the request comes here for the manager.",
} as const;
