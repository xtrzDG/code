/** `legalPages.*` in German: the public legal and contact pages (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { legalPagesEn } from "./legalPages.en";

export const legalPagesDe: Translation<typeof legalPagesEn> = {
  nav: {
    terms: "Nutzungsbedingungen",
    privacy: "Datenschutzerklärung",
    dpa: "Auftragsverarbeitungsvertrag",
    security: "Sicherheit",
    contact: "Kontakt",
  },
  descriptions: {
    terms: "Die Bedingungen, zu denen Unternehmen die Plattform für KI-Assistenten nutzen: der Dienst, Zahlung, Testphase, Haftung und Beendigung des Vertrags.",
    privacy: "Welche personenbezogenen Daten die Plattform über Unternehmensinhaber und ihr Team verarbeitet, warum, wie lange und wie Sie Ihre Rechte ausüben.",
    dpa: "Der Auftragsverarbeitungsvertrag, den jedes Unternehmen vor dem Start akzeptiert: wie Kundendaten in seinem Auftrag verarbeitet werden und von welchen Unterauftragsverarbeitern.",
    security: "Wie die Plattform Daten schützt: Verschlüsselung, Zugriffskontrolle, Backups, Überwachung und wie Sie eine Schwachstelle melden.",
    contact: "Wer die Plattform für KI-Assistenten anbietet und wie Sie eine Person erreichen: Support-Kanäle und Angaben zum Betreiber.",
  },
  footerLabel: "Rechtliches und Kontakt",
  draftTitle: "Entwurf",
  draftText:
    "Ein Anwalt hat diesen Text noch nicht geprüft, und die Felder in eckigen Klammern sind noch auszufüllen. Er wird veröffentlicht, damit Sie lesen können, was der Dienst bieten wird; in dieser Fassung gilt er noch nicht.",
  document: {
    upcoming: "Eine neue Version gilt ab {date}; sie ist bereits veröffentlicht.",
    otherLanguage: "Dieser Text ist in Ihrer Sprache noch nicht verfügbar; er wird auf {language} angezeigt.",
  },
  unavailable: "Der Text konnte gerade nicht geladen werden. Bitte versuchen Sie es später erneut.",
  dpaLead:
    "Jedes Unternehmen auf der Plattform akzeptiert diesen Vertrag in seinem Dashboard vor dem Start; er regelt, wie Kundendaten im Auftrag des Unternehmens verarbeitet werden.",
  related: "Weitere Dokumente",
  contactTitle: "Kontakt",
  contactLead: "Wer den Dienst anbietet und wie Sie eine Person erreichen.",
  operatorTitle: "Betreiber",
  legalName: "Name",
  address: "Adresse",
  taxId: "Steuernummer",
  country: "Land",
  email: "E-Mail",
  operatorMissing: "Adresse und Registrierungsdaten des Betreibers werden hier veröffentlicht, bevor der Dienst für Kunden öffnet.",
  supportTitle: "Schreiben Sie uns",
  supportWhatsApp: "WhatsApp",
  supportTelegram: "Telegram",
  supportEmail: "E-Mail",
  supportMissing: "Die Support-Kontakte erscheinen hier, bevor der Dienst für Kunden öffnet.",
  securityReportTitle: "Eine Schwachstelle gefunden?",
  securityReportText: "Bitte melden Sie sie vertraulich; wie das geht, steht in unserer security.txt.",
  securityReportLink: "Regeln für Sicherheitsforschende öffnen",
};
