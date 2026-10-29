/** `palette.*` in Italian: the command palette (a draft awaiting a native speaker's review). */

import type { Translation } from "../../../translate";
import type { paletteEn } from "./palette.en";

export const paletteIt: Translation<typeof paletteEn> = {
  title: "Cerca e vai",
  open: "Cerca",
  openTitle: "Cerca (Ctrl+K o ⌘K)",
  placeholder: "Cerca un cliente, una conversazione, una prenotazione o una pagina",
  groups: {
    navigation: "Vai a",
    customers: "Clienti",
    conversations: "Conversazioni",
    bookings: "Prenotazioni",
  },
  searching: "Ricerca…",
  noResults: "Nessun risultato per “{text}”.",
  resultCount: { one: "{count} risultato", other: "{count} risultati" },
  typeMore: "Digita almeno due lettere per cercare clienti, conversazioni e prenotazioni.",
  searchFailed: "La ricerca non ha risposto; le pagine sono comunque qui.",
  keys: "↑ ↓ per spostarti · Invio per aprire · Esc per chiudere",
  unnamed: "Cliente senza nome",
  conversationDetail: "{channel} · {date}",
  bookingDetail: "{date} · {guests}",
  partySize: { one: "{count} ospite", other: "{count} ospiti" },
};
