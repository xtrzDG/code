/** `digestChannels.*` in German (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { digestChannelsEn } from "./digestChannels.en";

export const digestChannelsDe: Translation<typeof digestChannelsEn> = {
  title: "Wo sie ankommen",
  email: "E-Mail",
  emailTo: "An {email}",
  emailMissing: "Sie melden sich per Telefon an, daher gibt es keine E-Mail-Adresse, an die gesendet werden kann.",
  emailNotReady: "E-Mail ist auf dieser Plattform noch nicht eingerichtet.",
  push: "Geräte",
  devices: { one: "Auf {count} Gerät sind Benachrichtigungen an", other: "Auf {count} Geräten sind Benachrichtigungen an" },
  noDevices: "Noch hat kein Gerät Benachrichtigungen an.",
  manageDevices: "Einstellungen der Benachrichtigungen",
  telegram: "Telegram",
  telegramHint: "Der ganze Bericht, vom Bot der Plattform.",
  telegramChat: "Telegram-Chat",
  telegramNoChats: "Verknüpfen Sie zuerst einen Telegram-Chat: Kanäle → Benachrichtigungen für das Team in Telegram.",
  openChannels: "Kanäle öffnen",
  telegramNotReady: "Telegram ist auf dieser Plattform noch nicht eingerichtet.",
  whatsapp: "WhatsApp",
  whatsappHint: "Eine kurze Zusammenfassung mit Link, von der Nummer der Plattform.",
  whatsappNumber: "Ihre WhatsApp-Nummer",
  whatsappNumberHint: "Mit Ländervorwahl. Mit der Wahl von WhatsApp stimmen Sie diesen Nachrichten zu.",
  whatsappNotReady: "WhatsApp-Zusammenfassungen sind auf dieser Plattform noch nicht eingerichtet.",
  save: "Speichern",
  invalidNumber: "Geben Sie die Nummer mit Ländervorwahl ein, z. B. +49 151 23456789.",
  refusals: {
    telegramNotAvailable: "Telegram-Zusammenfassungen sind auf dieser Plattform noch nicht eingerichtet.",
    telegramChatNotLinked: "Dieser Chat ist nicht mehr mit dem Unternehmen verknüpft. Wählen Sie einen anderen oder verknüpfen Sie ihn neu.",
    whatsappNotAvailable: "WhatsApp-Zusammenfassungen sind auf dieser Plattform noch nicht eingerichtet.",
    whatsappNumberMissing: "Geben Sie die WhatsApp-Nummer ein, an die die Zusammenfassungen gehen.",
  },
};
