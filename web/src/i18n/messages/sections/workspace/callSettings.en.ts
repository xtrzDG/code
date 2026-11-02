/**
 * `callSettings.*` texts of Settings → Calls (summaries after calls,
 * messages to callers who did not get through, the recording of calls,
 * transfers to staff, the WhatsApp template text and the latest
 * text-backs), in English: the reference that it is typed against.
 */

export const callSettingsEn = {
  description: "What happens after each call: a summary for your staff, and a message to callers who did not get through.",
  summaries: {
    title: "Call summaries",
    description:
      "After every call, staff chats in Telegram and WhatsApp get who called, what they wanted, how the call ended and anything the assistant said that is not in your data. Callers who did not get through are reported on every channel, so someone calls back.",
    toggle: "Send a summary after every call",
    contactsHint: "Who gets them: the staff contacts in Settings → Notifications.",
    openContacts: "Staff contacts",
    turnedOff: "Call summaries are off",
  },
  textBack: {
    title: "Text back missed callers",
    description:
      "When a caller does not get through (the line is busy, nobody answers, they hang up early, the assistant cannot take the call, or nobody picks up a transfer), we write to them within a minute or two, in their language. Their reply continues as a WhatsApp conversation in the Inbox.",
    toggle: "Text back callers who did not get through",
    template: "WhatsApp template name",
    templateHint: "The name of the approved utility template on your WhatsApp number: lowercase Latin letters, digits and underscores.",
    templateInvalid: "Use lowercase Latin letters, digits and underscores only.",
    sms: "Send an SMS when WhatsApp is not possible",
    smsHint: "From the platform's SMS sender, when the number has no WhatsApp or the template is refused.",
    smsNeedsTextBack: "Turn on messages to callers who did not get through first.",
    rules: "Each caller is texted at most once a day. Customers who opted out of messages, or who are already writing to you, are not texted.",
    turnedOff: "Messages to callers who did not get through are off",
    smsTurnedOff: "SMS to callers who did not get through is off",
    readiness: {
      whatsapp: "Callers get your WhatsApp template.",
      sms: "Callers get an SMS.",
      none: "Nothing can be sent yet: connect WhatsApp and name the template, or allow SMS.",
      off: "Text-backs are off.",
    },
    whatsappMissing: "WhatsApp is not connected.",
    connectWhatsapp: "Connect WhatsApp",
    smsMissing: "SMS is not available right now. Contact support.",
  },
  recording: {
    title: "Call recording",
    description:
      "Off unless you turn it on. When it is on, the audio of each call is kept for listening in the call's card, for as long as Settings → Privacy says. When it is off, the audio is deleted right after the call and the transcript is kept without phone, card and account numbers or e-mail addresses.",
    toggle: "Record calls",
    noticeTitle: "What callers hear at the start of every call",
    noticeHint: "The greeting says this whether or not you record, so callers always know where to read how their call is processed. Where the law asks for consent, callers may say no and the call goes on without a recording.",
    turnedOff: "Call recording is off",
  },
  transfers: {
    title: "Transfers to staff",
    description:
      "While you are open, a caller who asks for a person is put through to your staff number. After the transfer the voice platform may still process the call, so Italian labour law (art. 4 of the Workers' Statute) asks that the staff who take these calls are told beforehand. We keep nothing of the staff part of the call: no transcript, summary or recording.",
    confirm: "The staff who take transferred calls have been told",
    confirmHint: "Without this confirmation nobody is put through: the assistant takes a message and a colleague calls back.",
    confirmedOn: "Confirmed on {date}",
    number: "Staff number for transfers",
    numberRule: "Only a mobile or landline of your country or another EU country, never a premium, shared-cost or satellite number.",
    openContacts: "Staff numbers",
    turnedOff: "Transfers to staff are off",
    readiness: {
      ready: "Callers who ask for a person are put through while you are open.",
      unconfirmed: "Nobody is put through yet: confirm that your staff have been told.",
      noNumber: "No staff number calls can be put through to. Add a mobile in Settings → Notifications.",
    },
  },
  template: {
    title: "Template text",
    description:
      "Create a WhatsApp utility template with this text in Meta Business Manager, one translation per language; its only parameter is your business name. Callers get it in their language, or in English when there is no translation.",
    body: "Text for the template",
  },
  history: {
    title: "Latest text-backs",
    description: "The last 20 callers who did not get through, and what they were sent.",
    empty: "No missed calls yet",
    emptyDescription: "Callers who do not get through will appear here.",
    hiddenNumber: "Hidden number",
    openConversation: "Open conversation",
    notSentBecause: "Not sent: {reason}",
    statuses: {
      queued: "Sending",
      sent: "Sent",
      failed: "Not delivered",
      skipped: "Not sent",
    },
    channels: {
      whatsapp: "WhatsApp",
      sms: "SMS",
    },
    reasons: {
      no_answer: "No answer",
      busy: "Line busy",
      abandoned: "Hung up before the answer",
      line_failed: "Call not connected",
      not_started: "Assistant could not take the call",
      no_speech: "Hung up without speaking",
      transfer_unanswered: "Transfer not answered",
      callback_requested: "Asked for a callback",
    },
    skipReasons: {
      turned_off: "text-backs were off",
      opted_out: "the customer opted out of messages",
      already_texted: "already texted today",
      daily_limit: "the daily limit was reached",
      in_conversation: "they are already writing to you",
      no_channel: "no channel to send from",
      not_live: "the assistant was not live",
      no_caller_number: "the number was hidden",
      too_late: "the call was reported too late",
    },
  },
} as const;
