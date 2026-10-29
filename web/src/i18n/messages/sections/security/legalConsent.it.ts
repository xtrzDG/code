/** `legalConsent.*` texts of the sign-in consent line and legal documents dialog, in Italian (draft awaiting a native speaker's review). */

import type { Translation } from "../../../translate";
import type { legalConsentEn } from "./legalConsent.en";

export const legalConsentIt: Translation<typeof legalConsentEn> = {
  line: "Continuando, accetti i {terms} e confermi di aver letto l'{privacy}.",
  terms: "Termini di servizio",
  privacy: "Informativa sulla privacy",
  cookies: "Informativa sui cookie",
  documentUpcoming: "Dal {date} si applica una nuova versione.",
  otherLanguage: "Questo testo non è ancora tradotto nella tua lingua; viene mostrato in {language}.",
  loading: "Caricamento del testo…",
};
