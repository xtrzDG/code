/** `tunnel.*` in German: the setup tunnel's frame (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { tunnelEn } from "./tunnel.en";

export const tunnelDe: Translation<typeof tunnelEn> = {
  pageTitle: "KI-Assistenten erstellen",
  newAssistant: "Neuer Assistent",
  railLabel: "Einrichtungsschritte",
  steps: {
    business: "Ihr Unternehmen",
    place: "Wo Sie sind",
    offer: "Was Sie anbieten",
    hours: "Zeiten und Buchungen",
    people: "Wer hilft",
    channels: "Wo Kunden schreiben",
    try: "Testen",
    launch: "Start",
  },
  stepOf: "Schritt {number} von {total}",
  stepState: {
    done: "erledigt",
    skipped: "übersprungen",
    current: "Sie sind hier",
    todo: "noch offen",
  },
  announce: "Schritt {number} von {total}: {title}",
  announceFinale: "Ihr Assistent ist live",
  back: "Zurück",
  continue: "Weiter",
  skip: "Vorerst überspringen",
  enterHint: "oder Enter drücken",
  exit: "Speichern und beenden",
  saving: "Wird gespeichert…",
  saved: "Gespeichert",
  saveFailed: "Noch nicht gespeichert",
  ownerOnlyTitle: "Der Inhaber erstellt den Assistenten",
  ownerOnlyText:
    "Nur ein Inhaber von {business} kann ihn einrichten. Gespräche, Buchungen und Anfragen erscheinen im Dashboard, sobald er live ist.",
  openCabinet: "Dashboard öffnen",
};
