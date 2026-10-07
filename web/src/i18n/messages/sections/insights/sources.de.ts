/** `sources.*` in German (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { sourcesEn } from "./sources.en";

export const sourcesDe: Translation<typeof sourcesEn> = {
  title: "Woher die Kunden kamen",
  description: "Gespräche, Buchungen und ihr Wert je Link, QR-Code, Anzeige und Telefonleitung.",
  periodLabel: "Zeitraum",
  periods: {
    "7d": "7 Tage",
    "30d": "30 Tage",
    "90d": "90 Tage",
  },
  caption: "Kunden je Quelle, {range}",
  columns: {
    source: "Quelle",
    conversations: "Gespräche",
    bookings: "Buchungen",
    requests: "Anfragen",
    value: "Wert",
  },
  untagged: "Ohne Tag",
  other: { one: "{count} weiteres Tag", other: "{count} weitere Tags" },
  phone: "Anruf an {number}",
  ad: "Anzeige",
  adWithId: "Anzeige {id}",
  total: "Gesamt",
  noValue: "—",
  share: "{percent} der Gespräche",
  empty: {
    title: "Keine Gespräche in diesem Zeitraum",
    description: "Quellen erscheinen, sobald Kunden schreiben und anrufen.",
  },
  tagHint: "Geben Sie jedem Link und QR-Code unter Kanäle → Teilen ein eigenes Tag, dann erscheint er hier als eigene Zeile.",
  tagLink: "Ihre Links taggen",
  loading: "Die Quellen werden geladen…",
};
