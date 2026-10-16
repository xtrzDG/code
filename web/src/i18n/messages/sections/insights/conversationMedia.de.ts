/** `conversationMedia.*` in German (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { conversationMediaEn } from "./conversationMedia.en";

export const conversationMediaDe: Translation<typeof conversationMediaEn> = {
  label: "Anhänge",
  kinds: {
    audio: "Sprachnachricht",
    image: "Foto",
    location: "Standort",
    contact: "Kontaktkarte",
    sticker: "Sticker",
    file: "Datei",
  },
  voice: {
    transcript: "Transkript",
    play: "Abspielen",
    playLabel: "Sprachnachricht abspielen",
    playerLabel: "Sprachnachricht des Kunden",
    playerUnsupported: "Ihr Browser kann hier kein Audio abspielen.",
    loading: "Wird geladen…",
    missing: "Diese Sprachnachricht ist nicht mehr verfügbar: Sie wurde nach der Aufbewahrungsfrist oder mit den Daten des Kunden gelöscht.",
    error: "Die Sprachnachricht konnte nicht geladen werden. Versuchen Sie es in einer Minute erneut.",
    retry: "Erneut versuchen",
  },
  photo: {
    alt: "Vom Kunden gesendetes Foto",
    altWithCaption: "Vom Kunden gesendetes Foto: {caption}",
    open: "Foto öffnen",
    viewerTitle: "Foto des Kunden",
    unavailable: "Das Foto kann nicht angezeigt werden: Es wurde gelöscht, oder Ihre Sitzung ist abgelaufen.",
  },
  place: {
    openMap: "In Karten öffnen",
    openMapLabel: "{place} in Karten öffnen (öffnet sich in einem neuen Tab)",
    unnamed: "Geteilter Standort",
  },
  deleted: "Die Datei wurde nach der Aufbewahrungsfrist gelöscht.",
  problems: {
    unsupported_kind: "Der Assistent kann das nicht lesen und hat den Kunden gebeten, stattdessen zu schreiben.",
    too_large: "Zu groß zum Öffnen: Der Kunde wurde gebeten, stattdessen zu schreiben.",
    too_long: "Zu lang zum Transkribieren: Der Kunde wurde gebeten, stattdessen zu schreiben.",
    unavailable: "Der Messenger hatte diese Datei nicht mehr: Der Kunde wurde gebeten, stattdessen zu schreiben.",
    unrecognized_format: "Kein Format, das der Assistent liest: Der Kunde wurde gebeten, stattdessen zu schreiben.",
    not_understood: "Es waren keine Wörter zu erkennen: Der Kunde wurde gebeten, stattdessen zu schreiben.",
  },
};
