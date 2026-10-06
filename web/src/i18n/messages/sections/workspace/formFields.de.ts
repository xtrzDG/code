/** `formFields.*` in German (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { formFieldsEn } from "./formFields.en";

export const formFieldsDe: Translation<typeof formFieldsEn> = {
  time: {
    hours: "Stunden",
    minutes: "Minuten",
    dayPeriod: "Vormittags oder nachmittags",
    empty: "Nicht festgelegt",
  },
  date: {
    placeholder: "Datum wählen",
    open: "Kalender öffnen",
    calendar: "Kalender",
    previousMonth: "Vorheriger Monat",
    nextMonth: "Nächster Monat",
    today: "Heute",
    clear: "Löschen",
    date: "Datum",
    time: "Uhrzeit",
  },
  autosave: {
    hint: "Änderungen speichern sich selbst.",
    saving: "Wird gespeichert…",
    saved: "Gespeichert",
    failed: "Nicht gespeichert",
    retry: "Erneut versuchen",
    retryLater: "Nicht gespeichert: keine Verbindung. Wir versuchen es gleich noch einmal.",
    stale: "Jemand anderes hat das inzwischen geändert. Das Feld zeigt jetzt, was gespeichert ist.",
    leaveWarning: "Eine Änderung wird noch gespeichert.",
  },
};
