/** `live.*` in German: the live cabinet (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { liveEn } from "./live.en";

export const liveDe: Translation<typeof liveEn> = {
  status: {
    live: "Live",
    connecting: "Verbinden…",
    reconnecting: "Neu verbinden…",
    paused: "Live-Aktualisierung pausiert",
  },
  updatedJustNow: "Gerade aktualisiert",
  updatedMinutesAgo: {
    one: "Vor {count} Minute aktualisiert",
    other: "Vor {count} Minuten aktualisiert",
  },
  updatedAt: "Aktualisiert um {time}",
  updating: "Wird aktualisiert…",
  liveHint: "Diese Seite aktualisiert sich selbst, wenn Kunden schreiben, buchen oder eine Person brauchen.",
  reconnectingHint: "Die Verbindung ist abgebrochen, wir versuchen es weiter. Sie können es auch jetzt versuchen.",
  reconnect: "Jetzt versuchen",
  needsPersonTitle: "Ein Kunde braucht eine Person",
  needsPersonOpen: "Öffnen",
  sound: "Signalton, wenn jemand eine Person braucht",
  soundHint: "Ein kurzer Ton auf diesem Gerät, wenn ein Gespräch an Ihr Team übergeben wird.",
};
