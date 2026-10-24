/**
 * `adminReplySpeed.*` texts of the reply-speed card on the platform admin's
 * client page, in English: the reference that ru and ka are typed against.
 */

export const adminReplySpeedEn = {
  title: "Reply speed, 7 days",
  description: "How long customers waited, from their first unanswered message to the assistant's reply.",
  median: "Typical wait (median)",
  p95: "19 of 20 replies within",
  replies: "Measured replies",
  slowNote: "More than one reply in twenty took over 15 seconds. Check the model provider and the business's tools.",
  empty: "No measured replies in the last 7 days. Chats are measured from this release on; calls and the test chat are not.",
  tableCaption: "Reply speed by channel",
  channel: "Channel",
  channelReplies: "Replies",
  channelMedian: "Median",
  channelP95: "95%",
  seconds: "{value} s",
  minutes: "{value} min",
  issueLabel: "Slow replies",
} as const;
