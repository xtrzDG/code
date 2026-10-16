/** `adminSpend.*` in Hebrew (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { adminSpendEn } from "./adminSpend.en";

export const adminSpendHe: Translation<typeof adminSpendEn> = {
  title: "הוצאות היום",
  description: "מה הפלטפורמה חייבת לספקים שלה עבור {day} (UTC). עלויות שספק עוד לא דיווח עליהן נספרות לפי המחירים המתוכננים.",
  total: "סה״כ היום",
  weekMean: "ממוצע יומי של 7 הימים שלפני: {amount}",
  spike: "הרבה מעל הרגיל",
  budget: "{percent}% מהתקציב היומי של {amount}",
  budgetLabel: "התקציב היומי שנוצל",
  noBudget: "לא נקבע תקציב יומי (PLATFORM_DAILY_SPEND_BUDGET_USD).",
  providersLabel: "הוצאות לפי ספק",
  providers: {
    language_model: "מודל AI",
    voice: "סוכן קולי",
    telephony: "שיחות טלפון",
    whatsapp: "תבניות WhatsApp",
    transcription: "תמלול הודעות קוליות",
  },
  brakedTitle: "לקוחות שעברו מגבלת הוצאות",
  brakedNone: "אף לקוח לא עבר היום מגבלת הוצאות.",
  levels: {
    soft_limit: "מודל זול יותר",
    hard_limit: "פניות בלבד",
  },
  brakedLine: "{spend} מתוך {limit}, מאז {time}",
};
