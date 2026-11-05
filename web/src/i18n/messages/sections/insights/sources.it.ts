/** `sources.*` in Italian (a draft awaiting a native speaker's review). */

import type { Translation } from "../../../translate";
import type { sourcesEn } from "./sources.en";

export const sourcesIt: Translation<typeof sourcesEn> = {
  title: "Da dove arrivano i clienti",
  description: "Conversazioni, prenotazioni e il loro valore per link, codice QR, annuncio e linea telefonica.",
  periodLabel: "Periodo",
  periods: {
    "7d": "7 giorni",
    "30d": "30 giorni",
    "90d": "90 giorni",
  },
  caption: "Clienti per fonte, {range}",
  columns: {
    source: "Fonte",
    conversations: "Conversazioni",
    bookings: "Prenotazioni",
    requests: "Richieste",
    value: "Valore",
  },
  untagged: "Senza tag",
  other: { one: "{count} altro tag", other: "altri {count} tag" },
  phone: "Chiamata al {number}",
  ad: "Annuncio",
  adWithId: "Annuncio {id}",
  total: "Totale",
  noValue: "—",
  share: "{percent} delle conversazioni",
  empty: {
    title: "Nessuna conversazione in questo periodo",
    description: "Le fonti compaiono man mano che i clienti scrivono e chiamano.",
  },
  tagHint: "Assegna a ogni link e codice QR un tag in Canali → Condividi: qui comparirà come riga a sé.",
  tagLink: "Aggiungi un tag ai tuoi link",
  loading: "Caricamento delle fonti…",
};
