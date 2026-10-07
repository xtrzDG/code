/** `assistantChat.*` in German: the test chat (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { assistantChatEn } from "./assistantChat.en";

export const assistantChatDe: Translation<typeof assistantChatEn> = {
  chat: {
    newConversation: "Neues Gespräch",
    logLabel: "Testgespräch",
    emptyTitle: "Testgespräch beginnen",
    emptyDescription: "Fragen Sie, was Ihre Kunden fragen, in jeder Sprache. Oder probieren Sie eines davon:",
    suggestions: {
      hours: "Wie sind Ihre Öffnungszeiten?",
      price: "Was kostet das?",
      booking: "Ich möchte für morgen um 19 Uhr für 4 Personen buchen",
      human: "Kann ich mit einer Person sprechen?",
    },
    typing: "Der Assistent schreibt…",
    choicesLabel: "Antworten zum Antippen",
    inputLabel: "Nachricht",
    placeholder: "Nachricht schreiben…",
    inputHint: {
      one: "Enter sendet, Umschalt+Enter fügt eine Zeile hinzu. Bis zu {count} Zeichen.",
      other: "Enter sendet, Umschalt+Enter fügt eine Zeile hinzu. Bis zu {count} Zeichen.",
    },
    send: "Senden",
    failed: "Nicht gesendet.",
    silent: "Der Assistent schweigt: Das Gespräch wurde an eine Person übergeben.",
    handedOffTitle: "An eine Person übergeben",
    handedOffDescription:
      "In einem echten Chat würde jetzt Ihr Team antworten, deshalb schweigt der Assistent. Beginnen Sie ein neues Gespräch, um weiter zu testen.",
    guardRewritten: "Zahlen geprüft und korrigiert",
    guardHandedOff: "Weitergegeben: unsicher bei einer Zahl",
    handedOff: "An eine Person übergeben",
    bookingsCreated: { one: "Testbuchung angelegt", other: "{count} Testbuchungen angelegt" },
    leadsCreated: { one: "Testanfrage angelegt", other: "{count} Testanfragen angelegt" },
    toolCalls: { one: "{count} Werkzeugaufruf", other: "{count} Werkzeugaufrufe" },
    toolError: "Fehler",
    toolInput: "Eingabe",
    toolResult: "Ergebnis",
    noVersionsTitle: "Noch nichts zu testen",
    noVersionsDescription: "Übernehmen Sie Ihre Änderungen, um das erste Update des Assistenten vorzubereiten, und sprechen Sie dann hier mit ihm.",
    errors: {
      service: "Das Sprachmodell ist gerade nicht verfügbar. Versuchen Sie es in einer Minute erneut.",
    },
  },
};
