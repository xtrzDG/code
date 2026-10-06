/** `roi.*` in Hebrew: the missed-requests calculator (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { roiEn } from "./roi.en";

export const roiHe: Translation<typeof roiEn> = {
  title: "כמה עולות לכם הפניות שאתם מפספסים?",
  subtitle: "ספרו רק את מה שמגיע כשאף אחד לא יכול לענות. השאר הוא חשבון פשוט, עם המספרים שלכם.",
  niche: "סוג העסק שלכם",
  missed: "שיחות והודעות שאתם מפספסים או עונים עליהן מאוחר מדי, בחודש",
  missedHint: "שיחה שאף אחד לא ענה לה, הודעה שנענתה אחרי שעות",
  afterHours: "מתוכן, מחוץ לשעות העבודה",
  check: "חשבון ממוצע",
  checkHint: "חשבון טיפוסי לסוג העסק הזה; שנו אותו לשלכם",
  checkUnknown: "החשבונות כאן משתנים מאוד: הזינו את שלכם",
  conversion: "פניות שהופכות להזמנה",
  plan: "השוואה למסלול",
  percent: "{value}%",
  resultLabel: "העוזר היה מביא בערך",
  bookings: {
    one: "עוד הזמנה אחת בחודש",
    other: "עוד {count} הזמנות בחודש",
  },
  bookingsUnderOne: "פחות מהזמנה נוספת אחת בחודש",
  perMonth: "{value} בחודש",
  multiple: "פי {multiple} מהמחיר של {plan} ({price} בחודש)",
  belowPrice: "פחות מהמחיר של {plan} ({price} בחודש): חשבו גם את הזמן שהצוות שלכם חוסך על תשובות.",
  breakEven: {
    one: "הזמנה אחת בחודש משלמת על המסלול",
    other: "{count} הזמנות בחודש משלמות על המסלול",
  },
  noCheck: "הזינו חשבון ממוצע כדי לראות את הסכום.",
  breakdown: {
    label: "איך זה מצטבר",
    answered: "תשובות מחוץ לשעות העבודה",
    bookings: "הזמנות מתוכן",
    check: "חשבון ממוצע",
  },
  note: "הערכה לפי המספרים שלכם, לא הבטחה. בלוח הבקרה תראו את הנתונים האמיתיים: פניות שנענו, הזמנות ומה הן הביאו.",
  currency: "ב-{currency}",
};
