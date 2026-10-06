/** `adminIncident.*` in Hebrew (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { adminIncidentEn } from "./adminIncident.en";

export const adminIncidentHe: Translation<typeof adminIncidentEn> = {
  title: "רישום תקלה",
  description: "כל עסק מושפע מקבל רשומה ביומן הפעולות שלו. דליפת מידע אישי שולחת גם את ההודעה לפי סעיף 12.1 של הסכם עיבוד הנתונים לכל הבעלים של העסקים האלה.",
  kind: "סוג התקלה",
  severity: "חומרה",
  severityHint: "SEV1: רוב הלקוחות לא מקבלים תשובות, או שנתונים יצאו מהפלטפורמה. SEV2: ערוץ או יכולת לא עובדים עבור רבים. SEV3: עסקים בודדים, או שיש פתרון עוקף.",
  severityBreach: "דליפת מידע אישי היא תמיד SEV1.",
  name: "כותרת",
  nameHint: "שורה אחת ליומן, בלי שמות לקוחות.",
  startedAt: "התחילה",
  detectedAt: "זוהתה",
  detectedHint: "מתי הפלטפורמה נודעה לכך; ריק לעכשיו. בדליפה, תקופת ההודעה של 48 שעות נספרת מכאן.",
  timeZone: "השעות לפי אזור הזמן של המכשיר שלכם.",
  businesses: "עסקים מושפעים",
  businessesHint: "מזהי עסקים (business_…) או קישורים לעמודים שלהם בלקוחות, אחד בכל שורה.",
  scope: {
    legend: "אילו עסקים",
    listed: "העסקים שמופיעים למטה",
    all: "כל העסקים בפלטפורמה",
    allHint:
      "נרשם מיד; לאחר מכן ה-worker עובר על כל העסקים בקבוצות: כל עסק מקבל רשומת ביקורת, ובמקרה של דליפה הבעלים שלו מקבלים את ההודעה. היומן מראה עד היכן הגיע.",
  },
  announcement: {
    offer: "לפרסם גם הודעת סטטוס",
    offerHint: "מוצגת מעכשיו בדף הסטטוס הציבורי ובבאנר של כל קבינט; סגרו אותה בדף הזה כשהתקרית מסתיימת.",
    title: "הודעת סטטוס",
  },
  breach: {
    title: "הודעה לבעלים",
    description:
      "הבעלים מקבלים אותה בדוא״ל, או ב-SMS כשאין כתובת, בשפת לוח הבקרה שלהם. אנגלית היא חובה; הוסיפו גאורגית ורוסית כדי שכל בעלים יקרא אותה בשפה שלו.",
    subjects: "אנשים מושפעים (בקירוב)",
    records: "רשומות מושפעות (בקירוב)",
    language: "שפת ההודעה",
    languages: {
      en: "אנגלית",
      ka: "גאורגית",
      ru: "רוסית",
    },
    complete: "מלאה",
    partial: "חלקית",
    fields: {
      nature: "מה קרה",
      subject_categories: "קטגוריות של אנשים",
      record_categories: "קטגוריות של רשומות",
      likely_consequences: "השלכות סבירות",
      measures: "צעדים שננקטו או מוצעים",
    },
  },
  submit: "רישום התקלה",
  submitBreach: "רישום והודעה לבעלים",
  saving: "רושמים…",
  errors: {
    required: "מלאו את השדה.",
    title: "כתבו 3 עד 160 תווים.",
    future: "השעה הזו בעתיד.",
    order: "זמן הזיהוי לא יכול להיות לפני ההתחלה.",
    businessIds: "לא מזהה עסק: {tokens}",
    tooManyBusinesses: "לכל היותר 1,000 עסקים.",
    count: "מספר שלם מ-0 עד 1,000,000,000.",
    noticeRequired: "ההודעה באנגלית היא חובה.",
    noticeIncomplete: "מלאו את כל חמשת הטקסטים של השפה הזו, או אף אחד.",
  },
};
