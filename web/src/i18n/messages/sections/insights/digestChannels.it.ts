/** `digestChannels.*` in Italian (a draft awaiting a native speaker's review). */

import type { Translation } from "../../../translate";
import type { digestChannelsEn } from "./digestChannels.en";

export const digestChannelsIt: Translation<typeof digestChannelsEn> = {
  title: "Dove arrivano",
  email: "E-mail",
  emailTo: "A {email}",
  emailMissing: "Accedi con il telefono, quindi non c'è un indirizzo e-mail a cui inviarli.",
  emailNotReady: "L'e-mail non è disponibile al momento.",
  push: "Dispositivi",
  devices: { one: "{count} dispositivo ha le notifiche attive", other: "{count} dispositivi hanno le notifiche attive" },
  noDevices: "Nessun dispositivo ha ancora le notifiche attive.",
  manageDevices: "Impostazioni delle notifiche",
  telegram: "Telegram",
  telegramHint: "Il report completo, dal bot della piattaforma.",
  telegramChat: "Chat Telegram",
  telegramNoChats: "Prima collega una chat Telegram: Canali → Notifiche al personale su Telegram.",
  openChannels: "Apri Canali",
  telegramNotReady: "Telegram non è disponibile al momento.",
  whatsapp: "WhatsApp",
  whatsappHint: "Un breve riepilogo con un link, dal numero della piattaforma.",
  whatsappNumber: "Il tuo numero WhatsApp",
  whatsappNumberHint: "Con il prefisso internazionale. Scegliendo WhatsApp acconsenti a ricevere questi messaggi.",
  whatsappNotReady: "I riepiloghi su WhatsApp non sono disponibili al momento.",
  save: "Salva",
  invalidNumber: "Inserisci il numero con il prefisso internazionale, ad es. +39 333 123 4567.",
  refusals: {
    telegramNotAvailable: "I riepiloghi su Telegram non sono disponibili al momento.",
    telegramChatNotLinked: "Quella chat non è più collegata a questa attività. Scegline un'altra o collegala di nuovo.",
    whatsappNotAvailable: "I riepiloghi su WhatsApp non sono disponibili al momento.",
    whatsappNumberMissing: "Inserisci il numero WhatsApp a cui inviare i riepiloghi.",
  },
};
