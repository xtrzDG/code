/**
 * `adminReplyGuard.*` texts of the reply-guard card on the platform admin's
 * client page, in English: the reference that ru and ka are typed against.
 */

export const adminReplyGuardEn = {
  title: "Reply guard, 7 days",
  description:
    "Replies the guard held back because figures, statements or contact details were not backed by the business's data, and messages that tried to change the assistant's instructions.",
  checked: "Checked replies",
  heldBack: "Held back",
  heldBackShare: "{share} of replies",
  rewritten: "Rewritten once",
  handedOff: "Passed to staff",
  injectionFlags: "Injection attempts",
  heldBackNote:
    "The guard held back at least one reply in six. Check the business's facts and prices: the assistant is missing something customers ask about.",
  probedNote:
    "Someone keeps trying to change the assistant's instructions. The contacts are stopped for a day after three attempts; look at the conversations.",
  empty: "No checked replies in the last 7 days.",
  issueLabel: "Reply guard spike",
} as const;
