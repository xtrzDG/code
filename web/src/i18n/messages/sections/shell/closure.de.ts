/** `closure.*` auf Deutsch (siehe closure.en.ts). */

import type { Translation } from "../../../translate";
import type { closureEn } from "./closure.en";

export const closureDe: Translation<typeof closureEn> = {
  banner: {
    label: "Unternehmen wird geschlossen",
    title: "Dieses Unternehmen wird geschlossen",
    countdown: {
      one: "Alles darin wird in {count} Tag endgültig gelöscht, am {date}",
      other: "Alles darin wird in {count} Tagen endgültig gelöscht, am {date}",
    },
    due: "Die 30 Tage sind vorbei: Die Löschung beginnt innerhalb einer Stunde.",
    deleting: "Das Unternehmen wird gelöscht. Das lässt sich nicht mehr aufhalten.",
    unpaid: "Es wurde geschlossen, weil das Abo unbezahlt endete.",
    keep: "Unternehmen behalten",
    pay: "Bezahlen und behalten",
    open: "Details zur Schließung",
    kept: "Das Unternehmen ist wieder geöffnet",
  },
  zone: {
    title: "Dieses Unternehmen schließen",
    description:
      "Für den Fall, dass das Unternehmen den Assistenten nicht mehr nutzt. 30 Tage lang kann ein Inhaber es sich anders überlegen; danach wird das Unternehmen endgültig gelöscht.",
    willPause: "Der Assistent antwortet Kunden nicht mehr, und alle Kanäle werden getrennt.",
    willStopCharges: "Automatische Abbuchungen enden: Es wird nichts mehr berechnet.",
    willDelete:
      "Nach 30 Tagen wird alles im Unternehmen endgültig gelöscht: Unterhaltungen, Kunden, Buchungen, Aufnahmen, Dateien und Wissen.",
    willKeep: "Ausgestellte Rechnungen und das Aktivitätsprotokoll bleiben so lange erhalten, wie das Gesetz es verlangt.",
    exportFirst: "Laden Sie zuerst eine vollständige Kopie der Daten herunter",
    action: "Unternehmen schließen…",
    dialogTitle: "Das Unternehmen schließen?",
    dialogDescription:
      "Der Assistent antwortet ab sofort nicht mehr, und die Kanäle werden getrennt. In 30 Tagen wird das Unternehmen endgültig gelöscht, wenn kein Inhaber es behält.",
    confirm: "Unternehmen schließen",
    closing: "Wird geschlossen…",
    closed: "Das Unternehmen wird geschlossen",
    pendingTitle: "Das Unternehmen wird geschlossen",
    closedBy: "{name} hat es am {date} geschlossen",
    closedOn: "Geschlossen am {date}",
    unpaidHint: "Es wurde geschlossen, weil das Abo unbezahlt endete: Bezahlen Sie unter Abrechnung und behalten Sie das Unternehmen dann hier.",
    keepHint: "Wenn Sie es behalten, werden die Kanäle wieder verbunden; schalten Sie den Assistenten wieder ein, sobald Sie bereit sind.",
    keep: "Unternehmen behalten",
    billing: "Abrechnung öffnen",
    export: "Daten herunterladen",
    deletingTitle: "Das Unternehmen wird gelöscht",
    deletingDescription:
      "Die Löschung hat begonnen und lässt sich nicht mehr aufhalten. Die Inhaber finden die Löschbescheinigung unter Konto → Sicherheit.",
  },
  account: {
    title: "Konto löschen",
    description:
      "Meldet Sie überall ab und löscht Ihre Anmeldemethoden (Passkeys, Authenticator-App, Wiederherstellungscodes), Ihre Benachrichtigungseinstellungen und App-Benachrichtigungen. Sie verlassen jedes Unternehmen, dem Sie angehören; dessen eigene Daten bleiben dort.",
    ownerNote: "Der letzte Inhaber eines Unternehmens schließt es zuerst (Einstellungen → Unternehmen) oder macht ein anderes Mitglied zum Inhaber.",
    platformNote: "Mitglieder des Plattformteams verlassen zuerst das Team (Admin → Team) und löschen danach ihr Konto.",
    action: "Konto löschen…",
    dialogTitle: "Ihr Konto löschen?",
    dialogDescription: "Das lässt sich nicht rückgängig machen. Sie können sich später mit derselben E-Mail-Adresse oder Telefonnummer neu registrieren, als neues Konto.",
    confirm: "Konto löschen",
    deleting: "Wird gelöscht…",
    lastOwner: "Sie sind der letzte Inhaber von {names}. Schließen Sie das Unternehmen zuerst unter dessen Einstellungen → Unternehmen oder machen Sie ein anderes Mitglied zum Inhaber.",
    lastBrandOwner: "Sie sind der einzige Inhaber der Marke {names}. Machen Sie zuerst eine andere Person zum Markeninhaber.",
    lastOwnerUnnamed: "Sie sind der letzte Inhaber eines Unternehmens oder einer Marke. Schließen Sie es zuerst oder machen Sie eine andere Person zum Inhaber.",
    platformTeam: "Mitglieder des Plattformteams verlassen zuerst das Team (Admin → Team) und löschen danach ihr Konto.",
  },
  deletions: {
    title: "Gelöschte Unternehmen",
    description: "Unternehmen, die Ihnen gehörten und die geschlossen und gelöscht wurden. Jede Bescheinigung nennt, was wann gelöscht wurde und was das Gesetz aufbewahrt.",
    reasonOwner: "Von einem Inhaber geschlossen",
    reasonUnpaid: "Nach unbezahltem Abo-Ende geschlossen",
    inProgress: "Wird gelöscht",
    completedOn: "Gelöscht am {date}",
    startedOn: "Löschung begonnen am {date}",
    certificate: "Bescheinigung (PDF)",
    downloading: "Wird heruntergeladen…",
  },
};
