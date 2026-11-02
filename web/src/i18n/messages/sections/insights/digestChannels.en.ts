/**
 * `digestChannels.*` texts: Reports → Your summaries → where they arrive
 * (e-mail, devices, a Telegram chat of the platform bot, WhatsApp from the
 * platform's number), in English: the reference it is typed against.
 */

export const digestChannelsEn = {
  title: "Where they arrive",
  email: "E-mail",
  emailTo: "To {email}",
  emailMissing: "You sign in by phone, so there is no e-mail to send to.",
  emailNotReady: "E-mail is not available right now.",
  push: "Devices",
  devices: { one: "{count} device has notifications on", other: "{count} devices have notifications on" },
  noDevices: "No device has notifications on yet.",
  manageDevices: "Notification settings",
  telegram: "Telegram",
  telegramHint: "The whole report, from the platform's bot.",
  telegramChat: "Telegram chat",
  telegramNoChats: "Link a Telegram chat first: Channels → Staff notifications in Telegram.",
  openChannels: "Open Channels",
  telegramNotReady: "Telegram is not available right now.",
  whatsapp: "WhatsApp",
  whatsappHint: "A short summary with a link, from the platform's number.",
  whatsappNumber: "Your WhatsApp number",
  whatsappNumberHint: "With the country code. Choosing WhatsApp is your consent to these messages.",
  whatsappNotReady: "WhatsApp summaries are not available right now.",
  save: "Save",
  invalidNumber: "Enter the number with its country code, e.g. +39 333 123 4567.",
  refusals: {
    telegramNotAvailable: "Telegram summaries are not available right now.",
    telegramChatNotLinked: "That chat is no longer linked to this business. Choose another or link it again.",
    whatsappNotAvailable: "WhatsApp summaries are not available right now.",
    whatsappNumberMissing: "Enter the WhatsApp number the summaries go to.",
  },
} as const;
