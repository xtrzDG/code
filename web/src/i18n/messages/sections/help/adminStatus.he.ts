/** `adminStatus.*` in Hebrew: the admin's status announcements (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { adminStatusEn } from "./adminStatus.en";

export const adminStatusHe: Translation<typeof adminStatusEn> = {
  title: "הודעות בעמוד הסטטוס",
  description: "מה שעמוד הסטטוס הציבורי והבאנר מעל כל לוח בקרה אומרים. כל שינוי נרשם ביומן הפעולות.",
  create: "הודעה חדשה",
  openPage: "פתיחת עמוד הסטטוס",
  none: "עדיין אין הודעות",
  noneDescription: "כתבו הודעה כשחלק מהפלטפורמה לא עובד, איטי, או עומד לעבור תחזוקה.",
  status: {
    active: "פעילה",
    resolved: "נפתרה",
  },
  edit: "עדכון",
  resolve: "סימון כנפתרה",
  resolveTitle: "לסמן את ההודעה כנפתרה?",
  resolveBody: "הבאנר ייעלם מכל לוחות הבקרה, ועמוד הסטטוס יציג אותה תחת תקלות קודמות.",
  published: "ההודעה פורסמה",
  saved: "ההודעה עודכנה",
  resolvedToast: "ההודעה סומנה כנפתרה",
  form: {
    createTitle: "הודעה חדשה",
    editTitle: "עדכון ההודעה",
    description: "הבעלים רואים אותה מיד בעמוד הסטטוס ומעל לוח הבקרה שלהם.",
    level: "רמה",
    levelHints: {
      info: "הודעה בלבד: אף חלק בפלטפורמה לא מסומן כמושפע.",
      maintenance: "עבודה מתוכננת: ציינו שעת התחלה כדי להודיע עליה מראש.",
      degraded: "עובד, אבל לאט יותר או עם חלק מהכשלים.",
      outage: "לא עובד. הבעלים לא יכולים להסתיר את הבאנר הזה.",
    },
    components: "חלקים מושפעים",
    componentsHint: "כל עוד ההודעה פעילה, כל חלק שנבחר מציג את הרמה הזו בעמוד הסטטוס.",
    textLabel: "טקסט ב{language}",
    textHint: "אנגלית היא חובה. בעלים שהשפה שלהם נשארה ריקה קוראים את הטקסט באנגלית.",
    startsAt: "התחלה",
    startsAtHint: "ריק: עכשיו. שעה מאוחרת יותר מודיעה על עבודה מתוכננת.",
    expectedEnd: "סיום צפוי",
    timeZone: "השעות לפי אזור הזמן של המכשיר הזה.",
    publish: "פרסום",
    save: "שמירה",
    saving: "שומרים…",
    errors: {
      textRequired: "כתבו את הטקסט באנגלית: לפחות 3 תווים.",
      textShort: "לפחות 3 תווים, או השאירו ריק.",
      componentsRequired: "בחרו לפחות חלק מושפע אחד.",
      time: "הזינו תאריך ושעה.",
      endBeforeStart: "הסיום חייב להיות אחרי ההתחלה ובעתיד.",
      startTooLate: "ההתחלה יכולה להיות לכל היותר 60 יום קדימה.",
    },
  },
};
