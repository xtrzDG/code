/** `customerMemory.*` in German (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { customerMemoryEn } from "./customerMemory.en";

export const customerMemoryDe: Translation<typeof customerMemoryEn> = {
  title: "Kundengedächtnis",
  description:
    "Der Assistent erkennt Kunden, die wiederkommen: Er begrüßt sie, kennt ihre anstehenden Buchungen und offenen Anfragen und erinnert sich, worum es in früheren Gesprächen ging.",
  remember: {
    label: "Wiederkehrende Kunden merken",
    hint: "Zwei Stunden, nachdem ein Gespräch verstummt ist, wird eine kurze Zusammenfassung gespeichert. Ausgeschaltet werden keine Zusammenfassungen geschrieben, und jedes Gespräch beginnt von vorn.",
  },
  notes: {
    label: "Notizen des Teams mit dem Assistenten teilen",
    hint: "Interne Notizen zu den letzten Gesprächen des Kunden kommen ins Gedächtnis. Der Assistent zitiert sie dem Kunden nie.",
    needsMemory: "Schalten Sie zuerst das Kundengedächtnis ein.",
  },
  remembers: {
    title: "Was der Assistent sich merkt",
    visits: "Wie oft der Kunde geschrieben hat und wann er zuletzt da war",
    summaries: "Worum es in seinen drei letzten Gesprächen ging",
    bookings: "Seine anstehenden Buchungen und die Anfragen, die Ihr Team noch nicht abgeschlossen hat",
  },
  bookingsQuestion: "In jedem Kanal können Kunden auch fragen „Um wie viel Uhr ist meine Buchung?“: Der Assistent sieht ihre eigenen Buchungen nach.",
  privacy:
    "Das Gedächtnis geht nie an ein anderes Unternehmen. Wenn Sie die Daten eines Kunden unter Einstellungen → Datenschutz löschen, wird auch gelöscht, was der Assistent sich über ihn gemerkt hat.",
  ownerOnly: "Nur Inhaber können das ändern.",
  turnedOn: "Der Assistent merkt sich wiederkehrende Kunden",
  turnedOff: "Das Kundengedächtnis ist aus",
  notesShared: "Der Assistent liest jetzt die Notizen des Teams",
  notesHidden: "Die Notizen des Teams bleiben beim Team",
  loadError: "Die Einstellungen des Kundengedächtnisses konnten nicht geladen werden.",
};
