/** `topics.*` in Hebrew (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { topicsEn } from "./topics.en";

export const topicsHe: Translation<typeof topicsEn> = {
  title: "על מה לקוחות שואלים",
  description: "ההודעות הראשונות של 30 הימים האחרונים, מקובצות לנושאים בכל לילה.",
  updated: "קובץ ב-{date}",
  waiting: "הנושאים יופיעו אחרי הלילה הראשון עם שיחות.",
  empty: "עדיין אף לקוח לא כתב ב-30 הימים האחרונים.",
  conversations: { one: "שיחה אחת", other: "{count} שיחות" },
  unanswered: { one: "אחת ללא תשובה", other: "{count} ללא תשובה" },
  unansweredHint: "שאלות שהעוזר לא ידע לענות עליהן: הוסיפו תשובה והוא יענה.",
  addAnswer: "הוספת תשובה",
  otherLanguages: "שפות אחרות",
  otherTopic: "שאלות אחרות",
  languageLabel: "שפה",
  loading: "טוענים את הנושאים…",
};
