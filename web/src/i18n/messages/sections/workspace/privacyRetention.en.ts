/**
 * `privacyRetention.*` texts: Settings → Privacy → "How long data is
 * kept" (the retention periods, the nightly cleanup, the copies at the
 * sub-processors), in English: the reference that ru and ka are typed
 * against.
 */

export const privacyRetentionEn = {
  title: "How long data is kept",
  description:
    "Customers' data is deleted automatically once these periods pass. Your hosted chat's privacy notice tells customers the same periods.",
  conversations: {
    label: "Conversations",
    hint: "Counted from a conversation's last message. Then its messages, the team's notes, call transcripts and recordings are deleted; bookings, leads and requests keep only what is not personal.",
  },
  modelRecords: {
    label: "Records of the assistant's AI calls",
    hint: "The exact text sent to the AI model, kept to check answers. Deleted here and at the quality journal (Langfuse). At most 30 days.",
  },
  periods: {
    days: { one: "{count} day", other: "{count} days" },
    months: { one: "{count} month", other: "{count} months" },
    years: { one: "{count} year", other: "{count} years" },
    recommended: "{period} (recommended)",
    maximum: "{period} (maximum)",
  },
  recordings: "Call recordings are kept for {period}.",
  changeRecordings: "Change in General",
  processorsTitle: "Copies at our sub-processors",
  processors: {
    langfuse: "Langfuse: logs of the assistant's AI calls",
    elevenlabs: "ElevenLabs: phone calls (audio and transcript)",
  },
  processorsDeleted: "are deleted together with ours, by these periods and when you erase a customer's data:",
  processorsNone:
    "Langfuse and ElevenLabs are not used on this platform, so they keep no copies of your customers' data.",
  messagingApps:
    "Chats in WhatsApp, Messenger, Instagram and Telegram stay in the customer's own app: those platforms let only the customer delete them.",
  lastCleanupTitle: "Latest cleanup",
  lastCleanup: "{date}",
  nothingDue: "Nothing was due for deletion.",
  noCleanupYet: "The first cleanup runs tonight.",
  removed: { one: "{count} record removed", other: "{count} records removed" },
  counts: {
    deleted_messages: "messages",
    deleted_llm_turns: "AI call records",
    deleted_notes: "team notes",
    deleted_media: "customer files",
    deleted_missed_calls: "missed calls",
    erased_calls: "calls",
    anonymized_leads: "leads",
    anonymized_bookings: "bookings",
    anonymized_handoffs: "requests",
  },
  shorterTitle: "Delete older data tonight?",
  shorterDescription:
    "With shorter periods, tonight's cleanup deletes for good everything beyond them (conversations: {conversations}; AI call records: {modelRecords}). This cannot be undone.",
  shorterConfirm: "Shorten and delete",
  qualitySampling: {
    label: "Quality checks of real conversations",
    hint: "Each night a small sample of finished conversations (test chats left out) is scored by the same AI provider that writes the answers, so weak answers show up in the assistant's quality. Turn it off to keep your customers' conversations out of these checks.",
  },
} as const;
