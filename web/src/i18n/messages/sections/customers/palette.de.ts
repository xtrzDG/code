/** `palette.*` in German: the command palette (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { paletteEn } from "./palette.en";

export const paletteDe: Translation<typeof paletteEn> = {
  title: "Suchen und springen",
  open: "Suchen",
  openTitle: "Suchen (Strg+K oder ⌘K)",
  placeholder: "Kunden, Gespräch, Buchung oder Seite finden",
  groups: {
    navigation: "Gehe zu",
    customers: "Kunden",
    conversations: "Gespräche",
    bookings: "Buchungen",
  },
  searching: "Wird gesucht…",
  noResults: "Nichts gefunden für „{text}“.",
  resultCount: { one: "{count} Ergebnis", other: "{count} Ergebnisse" },
  typeMore: "Geben Sie mindestens zwei Buchstaben ein, um Kunden, Gespräche und Buchungen zu suchen.",
  searchFailed: "Die Suche hat nicht geantwortet; die Seiten sind trotzdem da.",
  keys: "↑ ↓ bewegen · Enter öffnen · Esc schließen",
  unnamed: "Kunde ohne Namen",
  conversationDetail: "{channel} · {date}",
  bookingDetail: "{date} · {guests}",
  partySize: { one: "{count} Gast", other: "{count} Gäste" },
};
