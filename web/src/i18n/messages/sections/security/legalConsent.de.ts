/** `legalConsent.*` in German (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { legalConsentEn } from "./legalConsent.en";

export const legalConsentDe: Translation<typeof legalConsentEn> = {
  line: "Wenn Sie fortfahren, akzeptieren Sie die {terms} und bestätigen, dass Sie die {privacy} gelesen haben.",
  terms: "Nutzungsbedingungen",
  privacy: "Datenschutzerklärung",
  cookies: "Cookie-Hinweise",
  documentUpcoming: "Ab {date} gilt eine neue Version.",
  otherLanguage: "Dieser Text ist noch nicht in Ihre Sprache übersetzt; er wird auf {language} angezeigt.",
  loading: "Der Text wird geladen…",
};
