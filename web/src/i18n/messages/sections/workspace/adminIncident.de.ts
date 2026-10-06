/** `adminIncident.*` in German (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { adminIncidentEn } from "./adminIncident.en";

export const adminIncidentDe: Translation<typeof adminIncidentEn> = {
  title: "Störung erfassen",
  description:
    "Jedes betroffene Unternehmen bekommt einen Eintrag im Protokoll. Eine Verletzung des Schutzes personenbezogener Daten sendet außerdem die Mitteilung nach Ziffer 12.1 des Auftragsverarbeitungsvertrags an jeden Inhaber dieser Unternehmen.",
  kind: "Art der Störung",
  severity: "Schweregrad",
  severityHint: "SEV1: Die meisten Kunden bekommen keine Antworten, oder Daten haben die Plattform verlassen. SEV2: Ein Kanal oder eine Funktion ist für viele ausgefallen. SEV3: wenige Unternehmen, oder es gibt eine Umgehung.",
  severityBreach: "Eine Datenschutzverletzung ist immer SEV1.",
  name: "Titel",
  nameHint: "Eine Zeile für das Protokoll, ohne Kundennamen.",
  startedAt: "Begonnen",
  detectedAt: "Erkannt",
  detectedHint: "Wann die Plattform davon erfahren hat; leer für jetzt. Bei einer Datenschutzverletzung läuft die 48-Stunden-Frist ab hier.",
  timeZone: "Die Zeiten gelten in der Zeitzone Ihres Geräts.",
  businesses: "Betroffene Unternehmen",
  businessesHint: "Unternehmens-IDs (business_…) oder Links zu ihren Seiten unter Kunden, eine pro Zeile.",
  breach: {
    title: "Mitteilung an die Inhaber",
    description:
      "Inhaber bekommen sie per E-Mail, ohne Adresse per SMS, in der Sprache ihres Dashboards. Englisch ist Pflicht; ergänzen Sie Georgisch und Russisch, damit jeder Inhaber sie in seiner Sprache liest.",
    subjects: "Betroffene Personen (ca.)",
    records: "Betroffene Datensätze (ca.)",
    language: "Sprache der Mitteilung",
    languages: {
      en: "Englisch",
      ka: "Georgisch",
      ru: "Russisch",
    },
    complete: "vollständig",
    partial: "unvollständig",
    fields: {
      nature: "Was passiert ist",
      subject_categories: "Kategorien von Personen",
      record_categories: "Kategorien von Datensätzen",
      likely_consequences: "Wahrscheinliche Folgen",
      measures: "Ergriffene oder vorgeschlagene Maßnahmen",
    },
  },
  submit: "Störung erfassen",
  submitBreach: "Erfassen und Inhaber benachrichtigen",
  saving: "Wird erfasst…",
  errors: {
    required: "Füllen Sie dieses Feld aus.",
    title: "Schreiben Sie 3 bis 160 Zeichen.",
    future: "Diese Zeit liegt in der Zukunft.",
    order: "Erkannt kann nicht vor Begonnen liegen.",
    businessIds: "Keine Unternehmens-ID: {tokens}",
    tooManyBusinesses: "Höchstens 1.000 Unternehmen.",
    count: "Eine ganze Zahl von 0 bis 1.000.000.000.",
    noticeRequired: "Die englische Mitteilung ist Pflicht.",
    noticeIncomplete: "Füllen Sie alle fünf Texte dieser Sprache aus oder keinen.",
  },
};
