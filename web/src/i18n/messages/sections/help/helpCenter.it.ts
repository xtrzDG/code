/** `helpCenter.*` texts of the help center and the support panel, in Italian (draft awaiting a native speaker's review). */

import type { Translation } from "../../../translate";
import type { helpCenterEn } from "./helpCenter.en";

export const helpCenterIt: Translation<typeof helpCenterEn> = {
  title: "Aiuto",
  description: "Brevi guide per ogni parte del pannello.",
  searchFieldLabel: "Cerca nella guida",
  searchPlaceholder: "Telegram, prenotazione, fattura…",
  search: "Cerca",
  clearSearch: "Cancella la ricerca",
  results: {
    one: "{count} articolo trovato",
    other: "{count} articoli trovati",
  },
  noResults: "Nessun risultato per “{query}”. Prova con un'altra parola.",
  topics: {
    getting_started: "Primi passi",
    channels: "Canali",
    daily_work: "Lavoro quotidiano",
    account: "Account e fatturazione",
  },
  allArticles: "Tutti gli articoli",
  related: "Leggi anche",
  otherLanguage: "Questo articolo non è ancora tradotto, quindi viene mostrato in {language}.",
  pageHelp: "Aiuto per questa pagina",
  drawerTitle: "Aiuto",
  openInCenter: "Apri nel centro assistenza",
  back: "Indietro",
  stillStuck: "Ancora in difficoltà?",
  stillStuckLead: "Scrivici: ti risponde una persona del team.",
  noSupportLead: "Controlla lo stato della piattaforma: se qualcosa non funziona per nessuno, il team ci sta già lavorando.",
  tipsAgain: "Mostra di nuovo i suggerimenti",
  tipsShown: "I suggerimenti verranno mostrati di nuovo nelle pagine Conversazioni, Assistente e Canali.",
  opensInNewTab: "si apre in una nuova scheda",
  support: {
    title: "Aiuto e assistenza",
    center: "Centro assistenza",
    whatsNew: "Novità",
    unread: {
      one: "{count} nuova",
      other: "{count} nuove",
    },
    status: "Stato della piattaforma",
    contact: "Scrivi all'assistenza",
    whatsapp: "WhatsApp",
    telegram: "Telegram",
    email: "E-mail",
  },
};
