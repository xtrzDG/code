/** `coachMarks.*` in German (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { coachMarksEn } from "./coachMarks.en";

export const coachMarksDe: Translation<typeof coachMarksEn> = {
  label: "Tipp",
  gotIt: "Verstanden",
  readGuide: "Anleitung lesen",
  inbox: {
    title: "Ihr Team-Posteingang",
    body: "Gespräche, die eine Person brauchen, stehen oben. Öffnen Sie eines, um zu antworten, es einer Kollegin oder einem Kollegen zu geben oder eine Notiz nur für das Team zu hinterlassen.",
  },
  assistant: {
    title: "Testen Sie Ihren Assistenten zuerst hier",
    body: "Schreiben Sie wie ein Kunde. Was Sie dem Assistenten beibringen, erscheint hier, bevor Kunden es bekommen.",
  },
  channels: {
    title: "Verbinden Sie die Kanäle, in denen Ihre Kunden schreiben",
    body: "Beginnen Sie mit dem Kanal, den Ihre Kunden am meisten nutzen. Jede Karte zeigt, ob er funktioniert und wann die letzte Nachricht kam.",
  },
};
