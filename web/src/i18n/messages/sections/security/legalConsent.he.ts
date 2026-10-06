/** `legalConsent.*` in Hebrew (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { legalConsentEn } from "./legalConsent.en";

export const legalConsentHe: Translation<typeof legalConsentEn> = {
  line: "בהמשך אתם מקבלים את {terms} ומאשרים שקראתם את {privacy}.",
  terms: "תנאי השימוש",
  privacy: "מדיניות הפרטיות",
  cookies: "הצהרת העוגיות",
  documentUpcoming: "החל מ-{date} חלה גרסה חדשה.",
  otherLanguage: "הטקסט הזה עדיין לא תורגם לשפה שלכם; הוא מוצג ב{language}.",
  loading: "טוענים את הטקסט…",
};
