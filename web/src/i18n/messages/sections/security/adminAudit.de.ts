/** `adminAudit.*` auf Deutsch: die Seite „Audit“ des Plattform-Admins. */

import type { Translation } from "../../../translate";
import type { adminAuditEn } from "./adminAudit.en";

export const adminAuditDe: Translation<typeof adminAuditEn> = {
  nav: "Audit",
  title: "Audit",
  description: "Die tägliche Manipulationsprüfung aller Aktivitätsprotokolle und das eigene Protokoll der Plattform: fehlgeschlagene Anmeldungen, Sperren, Abmeldungen und Schlüsselwechsel.",
  chains: {
    title: "Manipulationsprüfung",
    platform: "Plattform-Protokoll",
    intact: "Unveränderte Protokolle",
    broken: "Veränderte Protokolle",
    allIntact: "Die letzten Prüfungen fanden das Protokoll jedes Unternehmens so vor, wie es geschrieben wurde.",
    brokenList: "Als verändert gefundene Protokolle",
    business: "Unternehmen",
    entry: "Eintrag",
    problem: "Problem",
    checked: "Geprüft",
    platformName: "Plattform",
  },
  log: {
    title: "Plattform-Protokoll",
    description: "Einträge ohne Unternehmen, die neuesten zuerst. Die Adresse eines Anmeldecodes erscheint nur als schlüsselbasierter Fingerabdruck, nie die Adresse selbst.",
    filters: "Plattform-Protokoll filtern",
    event: "Ereignis",
    allEvents: "Alle Ereignisse",
    when: "Wann",
    what: "Was",
    who: "Wer",
    address: "Netzwerkadresse",
    entry: "Eintrag",
    empty: "Noch keine Einträge",
    emptyFiltered: "Keine Einträge für dieses Ereignis",
    unknownPerson: "Unbekannte Person",
    system: "System",
    restricted: "Das Plattformprotokoll zeigt die Anmeldungen aller Personen mit ihren Netzwerkadressen, daher sehen es nur Admins mit der Berechtigung für das Sicherheitsprotokoll.",
  },
  events: {
    login_failed: "Falscher Code",
    otp_locked: "Code gesperrt",
    mfa_locked: "Zweiter Schritt gesperrt",
    logout: "Abgemeldet",
    key_rotation: "Schlüsselwechsel",
  },
};
