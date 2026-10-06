/** `adminTeam.*` in Hebrew (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { adminTeamEn } from "./adminTeam.en";

export const adminTeamHe: Translation<typeof adminTeamEn> = {
  nav: "צוות",
  title: "צוות הניהול",
  description: "מי יכול לפתוח את עמודי הניהול ומה כל תפקיד רשאי לעשות. כל שינוי נרשם ביומן הפעולות.",
  roles: {
    super: "מנהל-על",
    support_readonly: "תמיכה (קריאה בלבד)",
    billing: "חיוב",
  },
  roleHints: {
    super: "הכול: לקוחות, תפעול, מדדים, הצוות; שינויים בלוח הבקרה של לקוח כשהבעלים מאשרים.",
    support_readonly: "לקוחות ובריאות הפלטפורמה; פותח את לוח הבקרה של לקוח לשעה, לקריאה בלבד.",
    billing: "לקוחות, החשבון שלהם (תקופת ניסיון, הנחות, זיכוי, תשלומים ידניים, מסלול), הערות ומדדי הצמיחה; אף פעם לא פותח את לוח הבקרה של לקוח.",
  },
  you: "אתם",
  notSignedIn: "עדיין לא התחבר",
  addedBy: "נוסף על ידי {name} {date}",
  addedOn: "נוסף בעמוד הצוות {date}",
  bootstrapped: "מרשימות PLATFORM_ADMIN_* {date}",
  role: "תפקיד",
  roleFor: "התפקיד של {name}",
  changed: "התפקיד שונה",
  remove: "הסרה",
  removeLabel: "הסרת {name} מהצוות",
  removeTitle: "להסיר את {name} מצוות הניהול?",
  removeDescription: "הגישה לעמודי הניהול תיחסם בבקשה הבאה שלו.",
  removed: "הוסר מהצוות",
  add: "הוספת אדם",
  addTitle: "הוספת אדם לצוות הניהול",
  addDescription: "הוא יקבל את עמודי הניהול בפעם הבאה שיתחבר עם מספר הטלפון או הדוא״ל הזה, וחייב להגדיר אפליקציית אימות.",
  by: "מתחבר באמצעות",
  byPhone: "מספר טלפון",
  byEmail: "דוא״ל",
  phone: "מספר טלפון",
  email: "דוא״ל",
  added: "נוסף לצוות",
  lastSuper: "בצוות חייב להיות לפחות מנהל-על אחד: קודם תנו את התפקיד למישהו אחר.",
};
