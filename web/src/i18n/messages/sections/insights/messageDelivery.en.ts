/**
 * `messageDelivery.*` texts of how a staff reply travels to the customer
 * (the chip under it in the conversation), in English: the reference that
 * ru and ka are typed against.
 */

export const messageDeliveryEn = {
  label: "Delivery",
  states: {
    sending: "Sending…",
    retrying: "Not delivered yet, trying again",
    delivered: "Delivered",
    failed: "Not delivered",
  },
  nextAttempt: "next try at {time}",
  reasons: {
    rate_limited: "the messenger asked to wait",
    provider_unavailable: "the messenger did not answer",
    recipient_refused: "the messenger refused it (the customer may have blocked the business, or the 24-hour window closed)",
    template_rejected: "WhatsApp did not accept the message template",
    channel_disconnected: "the channel is not connected any more",
    credential_rejected: "the channel's access stopped working: reconnect it in Channels",
    not_configured: "nothing can carry this message",
    expired: "its moment passed before it could go out",
  },
} as const;
