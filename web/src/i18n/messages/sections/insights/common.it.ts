/** `insightsCommon.*` in Italian (a draft awaiting a native speaker's review). */

import type { Translation } from "../../../translate";
import type { insightsCommonEn } from "./common.en";

export const insightsCommonIt: Translation<typeof insightsCommonEn> = {
  loadingMore: "Caricamento…",
  showMore: "Mostra altro",
  includeTest: "Includi l'attività di prova",
  includeTestHint: "Dalla chat di prova e dalle verifiche",
  testBadge: "Test",
  afterHours: "Fuori orario",
  unknownCustomer: "Cliente senza nome",
  callPhone: "Chiama {phone}",
  openConversation: "Apri la conversazione",
  noMatchesTitle: "Nessun risultato con questi filtri",
  noMatchesDescription: "Modifica o azzera i filtri per vedere altro.",
  copy: "Copia",
  copied: "Copiato negli appunti",
  copyFailed: "Impossibile copiare. Seleziona il testo e copialo a mano.",
  customerMessage: {
    title: "Messaggio per il cliente",
    description: "Da qui l'assistente non invia questo testo da solo. Invialo tu al cliente nel canale in cui vi sentite.",
  },
  channels: {
    phone: "Telefono",
    whatsapp: "WhatsApp",
    instagram: "Instagram",
    messenger: "Messenger",
    telegram: "Telegram",
    web_chat: "Chat del sito",
    viber: "Viber",
    owner_test: "Chat di prova",
  },
};
