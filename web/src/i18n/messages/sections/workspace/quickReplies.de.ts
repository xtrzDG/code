/** `quickReplies.*` in German (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { quickRepliesEn } from "./quickReplies.en";

export const quickRepliesDe: Translation<typeof quickRepliesEn> = {
  description:
    "Antworten, die Ihr Team oft sendet, bereit in jeder Sprache Ihres Unternehmens. Tippen Sie im Gespräch /, um eine einzufügen: Name und Buchung des Kunden werden von selbst ausgefüllt.",
  add: "Neue Schnellantwort",
  loading: "Schnellantworten werden geladen…",
  emptyTitle: "Noch keine Schnellantworten",
  emptyDescription: "Öffnungszeiten, Wegbeschreibung, „wir rufen Sie zurück“: einmal schreiben, mit zwei Tipps senden.",
  listLabel: "Schnellantworten",
  languages: "Sprachen",
  variablesUsed: "Füllt aus",
  edit: "Bearbeiten",
  editLabel: "Schnellantwort „{title}“ bearbeiten",
  delete: "Löschen",
  deleteLabel: "Schnellantwort „{title}“ löschen",
  confirmDelete: {
    title: "Diese Schnellantwort löschen?",
    description: "„{title}“ verschwindet für das ganze Team aus der Auswahl.",
    confirm: "Löschen",
  },
  deleted: "Schnellantwort gelöscht",
  saved: "Schnellantwort gespeichert",
  editor: {
    newTitle: "Neue Schnellantwort",
    editTitle: "Schnellantwort bearbeiten",
    description: "Schreiben Sie sie in jeder Sprache, die Ihre Kunden verwenden. Das Team sieht den Text in der Sprache des Gesprächs.",
    title: "Name",
    titleHint: "Was das Team in der Auswahl sieht.",
    shortcut: "Kürzel",
    shortcutHint: "Wird nach / im Antwortfeld getippt: Buchstaben, Ziffern, - und _.",
    shortcutInvalid: "Verwenden Sie nur Buchstaben, Ziffern, - und _, ohne Leerzeichen.",
    texts: "Text",
    textIn: "Text auf {language}",
    textHint: "Lassen Sie eine Sprache leer, wenn Sie sie nicht brauchen. Mindestens ein Text ist nötig.",
    needOneText: "Schreiben Sie den Text in mindestens einer Sprache.",
    insert: "Einfügen",
    insertLabel: "{variable} in den Text auf {language} einfügen",
    preview: "Vorschau",
    previewHint: "Mit einem Beispielkunden und einer Beispielbuchung.",
    sample: {
      name: "Lena",
      bookingTime: "Sa., 19:30",
    },
    save: "Speichern",
    saving: "Wird gespeichert…",
    cancel: "Abbrechen",
    length: "{count} / {max}",
  },
  variables: {
    name: "Name des Kunden",
    booking_time: "Buchungszeit",
    business_name: "Name des Unternehmens",
  },
  errors: {
    shortcut_taken: "Eine andere Schnellantwort verwendet dieses Kürzel bereits.",
    too_many_quick_replies: "Ein Unternehmen hat höchstens 100 Schnellantworten. Löschen Sie eine, die Sie nicht mehr verwenden.",
    unknown_variable: "Nur {name}, {booking_time} und {business_name} können ausgefüllt werden. Prüfen Sie die geschweiften Klammern im Text.",
    duplicate_language: "Jede Sprache kann einen Text haben.",
  },
};
