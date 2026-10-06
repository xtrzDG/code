/** `publicDemo.*` in German: the public demo chat (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { publicDemoEn } from "./publicDemo.en";

export const publicDemoDe: Translation<typeof publicDemoEn> = {
  label: "Live-Demo des Assistenten",
  badge: "Live-Demo",
  sampleBadge: "Beispiel",
  sandbox: "Testumgebung: Nichts wird wirklich gebucht",
  pick: "Branche",
  place: "{niche} · {city}",
  greeting: "Hallo! Ich bin der KI-Assistent von {business}. Fragen Sie mich, was Ihre Kunden fragen würden: Preise, Öffnungszeiten, eine Buchung.",
  starters: "Fragen Sie zum Beispiel",
  genericStarters: {
    hours: "Wie sind Ihre Öffnungszeiten?",
    prices: "Was kostet das?",
    place: "Wo befinden Sie sich?",
  },
  inputLabel: "Ihre Nachricht an den Demo-Assistenten",
  placeholder: "Schreiben Sie wie ein Kunde…",
  send: "Senden",
  typing: "Der Assistent schreibt…",
  restart: "Neu beginnen",
  you: "Sie",
  assistant: "Assistent",
  outcomes: {
    booking: "Hier würde eine Buchung angelegt",
    request: "Hier ginge die Anfrage an Ihre Führungskraft",
    handoff: "Hier ginge das Gespräch an eine Person",
  },
  messagesLeft: {
    one: "Noch {count} Nachricht in dieser Stunde",
    other: "Noch {count} Nachrichten in dieser Stunde",
  },
  failures: {
    limit: "Die Demo hat viele Nachrichten bekommen. Versuchen Sie es etwas später oder erstellen Sie Ihren eigenen Assistenten: Das dauert etwa zehn Minuten.",
    unavailable: "Diese Demo ruht gerade. Probieren Sie eine andere Branche.",
    offline: "Keine Verbindung. Prüfen Sie das Internet und versuchen Sie es erneut.",
    failed: "Die Nachricht ist nicht angekommen. Versuchen Sie es erneut.",
  },
  privacy: "Eine öffentliche Demo: Bitte geben Sie keine persönlichen Daten ein.",
  cta: "Meinen eigenen erstellen",
};
