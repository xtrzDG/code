/** `tunnelOffer.*` in German: the offer, hours and bookings steps (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { tunnelOfferEn } from "./tunnelOffer.en";

export const tunnelOfferDe: Translation<typeof tunnelOfferEn> = {
  offer: {
    title: "Was bieten Sie an?",
    text: "Fügen Sie hinzu, was Sie verkaufen, mit Preisen. Der Assistent nennt nur Preise von dem, was hier steht.",
    sourcesLabel: "Wie Sie es hinzufügen",
    sources: {
      type: "Eintippen",
      website: "Von Ihrer Website",
      menu: "Aus einem Foto oder einer Datei der Speisekarte",
    },
    tableLabel: "Ihr Angebot",
    name: "Name",
    namePlaceholder: "Was Kunden bestellen oder buchen können",
    price: "Preis, {currency}",
    pricePlaceholder: "0",
    suggestion: "Beispiel",
    suggestionsHint: "Beispiele werden erst gespeichert, wenn Sie ihnen einen Preis geben. Entfernen Sie die, die Sie nicht anbieten.",
    addRow: "Zeile hinzufügen",
    removeRow: "{name} entfernen",
    removeEmpty: "Diese Zeile entfernen",
    rowMenu: "Mehr zu {name}",
    rowSaving: "Wird gespeichert…",
    rowSaved: "Gespeichert",
    rowFailed: "Nicht gespeichert",
    priced: {
      one: "{count} Eintrag mit Preis",
      other: "{count} Einträge mit Preis",
    },
    importedTitle: {
      one: "{count} Eintrag aus Ihrem Import hinzugefügt",
      other: "{count} Einträge aus Ihrem Import hinzugefügt",
    },
    importHint: "Wir lesen es und zeigen Ihnen, was wir gefunden haben. Nichts wird gespeichert, bevor Sie es geprüft haben.",
  },
  hours: {
    title: "Wann haben Sie geöffnet?",
    text: "Wir haben die üblichen Zeiten für Ihre Branche vorgeschlagen. Ändern Sie alles, was bei Ihnen anders ist.",
    hoursLabel: "Öffnungszeiten",
    bookingsTitle: "Wie funktionieren Buchungen?",
    slot: "Ein Besuch dauert",
    partySize: "Höchstens Personen pro Buchung",
    notice: "Mindestens buchen",
    noticeNone: "Keine Vorlaufzeit nötig",
    cancellation: "Stornoregel",
    cancellationHint: "Kunden hören sie, wenn sie buchen oder stornieren.",
    resourceTitle: "Was Kunden buchen",
    resourceHint: "Weitere können Sie später unter Assistent → Wissen hinzufügen.",
    resourceName: "Name",
    resourceCount: "Wie viele",
    resourceCapacity: "Personen pro Einheit",
    minutes: {
      one: "{count} Minute",
      other: "{count} Minuten",
    },
    hoursCount: {
      one: "{count} Stunde",
      other: "{count} Stunden",
    },
    noticeHours: {
      one: "{count} Stunde im Voraus",
      other: "{count} Stunden im Voraus",
    },
    noticeDays: {
      one: "{count} Tag im Voraus",
      other: "{count} Tage im Voraus",
    },
    noticeMinutes: {
      one: "{count} Minute im Voraus",
      other: "{count} Minuten im Voraus",
    },
    errors: {
      noHours: "Öffnen Sie mindestens einen Tag.",
      partySize: "Geben Sie eine ganze Zahl ab 1 ein.",
      resourceName: "Benennen Sie, was Kunden buchen.",
      capacity: "Geben Sie eine ganze Zahl ab 1 ein.",
      unitCount: "Geben Sie eine ganze Zahl ab 1 ein.",
    },
  },
};
