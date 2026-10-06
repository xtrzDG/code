/** `segments.*` in German: Customers → Segments (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { segmentsEn } from "./segments.en";

export const segmentsDe: Translation<typeof segmentsEn> = {
  loading: "Segmente werden geladen…",
  new: "Neues Segment",
  empty: "Noch keine Segmente",
  emptyDescription: "Speichern Sie eine Kundengruppe, zum Beispiel Stammkunden, die seit 60 Tagen nicht da waren, und laden Sie sie für eine Kampagne herunter.",
  limit: "Ein Unternehmen hat höchstens 50 Segmente. Löschen Sie eines, um ein weiteres zu speichern.",
  members: "Kunden",
  noMembers: "Gerade passt niemand zu diesem Segment.",
  showMore: "Mehr Kunden anzeigen",
  export: "CSV herunterladen",
  exportHint: "Die Kunden des Segments mit Telefon, Kanälen, Tags und Buchungen, für eine Kampagne anderswo.",
  edit: "Bearbeiten",
  delete: "Löschen",
  deleteTitle: "Segment „{name}“ löschen?",
  deleteBody: "Nur die gespeicherten Regeln werden gelöscht; kein Kunde wird verändert.",
  deleted: "Das Segment ist gelöscht",
  saved: "Das Segment ist gespeichert",
  editor: {
    newTitle: "Neues Segment",
    editTitle: "Segment bearbeiten",
    name: "Name",
    namePlaceholder: "z. B. Seit 60 Tagen nicht da",
    rules: "Wer dazugehört",
    rulesHint: "Jede ausgefüllte Regel muss zutreffen. Blockierte und gelöschte Kunden gehören nie dazu.",
    tag: "Tag",
    anyTag: "Beliebiges Tag",
    lastVisit: "Letzter Besuch vor mehr als … Tagen",
    minBookings: "Mindestens … Buchungen",
    maxBookings: "Höchstens … Buchungen",
    vipOnly: "Nur VIP-Kunden",
    save: "Segment speichern",
  },
  errors: {
    name: "Geben Sie dem Segment einen Namen (bis zu 60 Zeichen).",
    days: "Die Tage sind eine ganze Zahl von 1 bis 3650.",
    bookings: "Die Buchungen sind eine ganze Zahl von 0 bis 10000.",
    minMax: "„Mindestens“ darf nicht größer sein als „höchstens“.",
  },
  preview: {
    counting: "Wird gezählt…",
    count: { one: "{count} Kunde passt", other: "{count} Kunden passen" },
    atLeast: { one: "Mindestens {count} Kunde passt", other: "Mindestens {count} Kunden passen" },
    none: "Noch passt niemand.",
  },
  summary: {
    everyone: "Jeder Kunde",
    tag: "Tag „{tag}“",
    lastVisit: { one: "letzter Besuch vor über {count} Tag", other: "letzter Besuch vor über {count} Tagen" },
    minBookings: { one: "mindestens {count} Buchung", other: "mindestens {count} Buchungen" },
    maxBookings: { one: "höchstens {count} Buchung", other: "höchstens {count} Buchungen" },
    vipOnly: "Nur VIP",
  },
};
