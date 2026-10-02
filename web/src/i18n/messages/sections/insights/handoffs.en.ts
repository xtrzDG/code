/**
 * `handoffs.*` texts of handoffs to a person, in English: the reference that
 * ru and ka are typed against.
 */

export const handoffsEn = {
  loading: "Loading handoffs…",
  tabsLabel: "Handoff status",
  tabs: {
    open: "Open",
    resolved: "Resolved",
    all: "All",
  },
  urgency: {
    critical: "Critical",
    high: "Urgent",
    normal: "Normal",
    low: "Low",
  },
  reason: {
    customer_request: "Asked for a person",
    complaint: "Complaint",
    vip_guest: "VIP guest",
    non_standard_request: "Non-standard request",
    unknown_answer: "Assistant did not know the answer",
    emergency: "Emergency",
    sensitive_topic: "Sensitive topic",
    profile_rule: "Your handoff rule",
    unverified_numbers: "Unverified prices or numbers",
  },
  status: {
    pending: "Notifying staff",
    notified: "Staff notified",
    notification_failed: "Notification failed",
    resolved: "Resolved",
  },
  notificationFailedHint: "Staff did not get the notification. Call the customer back and check the contacts in settings.",
  resolvedAt: "Resolved {date}",
  resolve: "Resolve",
  confirmResolve: {
    title: "Mark the handoff as resolved?",
    description: "{name}: the assistant starts answering this customer again.",
    confirm: "Resolve",
  },
  resolved: "Handoff resolved",
  emptyOpenTitle: "No open handoffs",
  emptyOpenDescription: "When the assistant passes a conversation to a person, it waits here with a short summary.",
  emptyTitle: "No handoffs yet",
} as const;
