/** `updates.*` in German: owner checks in an update, drafts and the test chat target (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { updatesEn } from "./updates.en";

export const updatesDe: Translation<typeof updatesEn> = {
  expectation: {
    must_mention: "die Antwort muss „{text}“ erwähnen",
    must_not_mention: "die Antwort darf „{text}“ nicht erwähnen",
    must_hand_off: "die Antwort muss den Kunden an eine Person übergeben",
    must_create_lead: "die Antwort muss eine Anfrage aufnehmen",
  },
  failed: {
    one: "Ihre Prüfung ist nicht bestanden: „{question}“ — {expectation}",
    many: {
      one: "{count} Ihrer Prüfungen ist nicht bestanden",
      other: "{count} Ihrer Prüfungen sind nicht bestanden",
    },
    rest: "Alles andere hat bestanden. Kunden behalten die bisherigen Antworten, bis die Prüfung besteht.",
    result: "Ihre Prüfung ist nicht bestanden",
    openCheck: "Prüfung öffnen",
    fixAnswer: "Antwort korrigieren",
    answered: "Der Assistent antwortete",
    applyAfterFix: "Änderungen übernehmen",
  },
  pending: {
    checksTitle: "Ihre Prüfungen",
    checksHint: "Das Update stellt sie zuerst. Besteht eine nicht, behalten Kunden die bisherigen Antworten.",
    added: "Neue Prüfung: „{question}“",
    changed: "Geänderte Prüfung: „{question}“",
    draftsTitle: "Entwürfe",
    draftsHint: "Von Hand erstellt und nie an Kunden gegeben. Einen zu verwerfen behält Ihre Änderungen.",
    draft: "Entwurf vom {date}",
    open: "Öffnen",
    discard: "Verwerfen",
    discardLabel: "Entwurf vom {date} verwerfen",
    discardTitle: "Diesen Entwurf verwerfen?",
    discardDescription: "Kunden haben ihn nie bekommen. Ihre Änderungen bleiben: Das nächste „Änderungen übernehmen“ baut darauf auf.",
    discarded: "Entwurf verworfen",
    onlyDrafts: "Alles, was Sie geändert haben, erreicht die Kunden. Ein Entwurf ist übrig:",
  },
  checkNow: {
    savedTitle: "Prüfung gespeichert",
    action: "Jetzt prüfen",
    actionLabel: "„{question}“ jetzt prüfen",
    checking: "Wird geprüft…",
    hint: "Ein Testgespräch mit dem, was Kunden jetzt bekommen.",
    passed: "Bestanden mit dem, was Kunden jetzt bekommen.",
    failed: "Nicht bestanden mit dem, was Kunden jetzt bekommen.",
    errored: "Die Prüfung konnte nicht abgeschlossen werden. Versuchen Sie es in einer Minute erneut.",
    notLive: "Noch erreicht nichts die Kunden: Die Prüfung läuft beim ersten „Änderungen übernehmen“.",
    limited: "Sie haben in dieser Stunde viel geprüft. Versuchen Sie es später erneut.",
    checkedAt: "Geprüft {date}",
  },
  language: {
    auto: "Sprache der Frage",
  },
  chat: {
    target: "Sprechen mit",
    live: "Was Kunden jetzt bekommen",
    changes: "Mit Ihren Änderungen",
    history: "Aus dem Verlauf: Update {number}",
    noteLive: "Sie sprechen mit dem, was Kunden jetzt bekommen. Testgespräche erreichen weder Kunden noch Mitarbeitende noch die Abrechnung.",
    noteChanges:
      "Sie sprechen mit dem Assistenten mit Ihren letzten Änderungen, bevor Kunden sie bekommen. Testgespräche erreichen weder Kunden noch Mitarbeitende noch die Abrechnung.",
    noteHistory: "Sie sprechen mit einem Update aus dem Verlauf. Testgespräche erreichen weder Kunden noch Mitarbeitende noch die Abrechnung.",
  },
  publishGate: {
    adminOnly: "Nur für Plattform-Admins",
  },
};
