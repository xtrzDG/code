/**
 * `handoffs.*` texts of "Needs a person" (conversations the assistant passed
 * to a person), in English: the reference that ru and ka are typed against.
 * Wording follows docs/glossary.md.
 */

export const handoffsEn = {
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
    profile_rule: "One of your rules",
    unverified_numbers: "Unconfirmed prices or figures",
  },
  status: {
    pending: "Notifying staff",
    notified: "Staff notified",
    notification_failed: "Notification failed",
    resolved: "Resolved",
  },
  notificationFailedHint: "Staff did not get the notification. Call the customer back and check the contacts in settings.",
  summaryCodes: {
    model_declined: "The assistant would not answer this message.",
    model_unavailable: "The assistant was briefly unavailable and could not answer.",
    answer_unfinished: "The assistant could not finish its answer.",
    unverified_values: "The assistant held back an answer with figures or statements that are not in your business details.",
    call_booking_unverified_values:
      "On the call the assistant named figures that are not in your business details. Check the booking from this call against the transcript.",
    call_request_unverified_values:
      "On the call the assistant named figures that are not in your business details. Check the request from this call against the transcript.",
    reply_undelivered: "The assistant's reply did not reach the customer. Contact them another way.",
    data_erased: "Details erased at the customer's request.",
  },
  summaryCodesWithValues: {
    unverified_values: "The assistant held back an answer with figures or statements that are not in your business details ({values}).",
    call_booking_unverified_values:
      "On the call the assistant named figures that are not in your business details ({values}). Check the booking from this call against the transcript.",
    call_request_unverified_values:
      "On the call the assistant named figures that are not in your business details ({values}). Check the request from this call against the transcript.",
  },
  quote: {
    customer: "The customer's message",
    reply: "The reply that did not arrive",
  },
} as const;
