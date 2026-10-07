/** `legalPages.*` in Hebrew: the public legal and contact pages (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { legalPagesEn } from "./legalPages.en";

export const legalPagesHe: Translation<typeof legalPagesEn> = {
  nav: {
    terms: "תנאי השימוש",
    privacy: "מדיניות הפרטיות",
    dpa: "הסכם עיבוד נתונים",
    security: "אבטחה",
    contact: "יצירת קשר",
  },
  descriptions: {
    terms: "התנאים שבהם עסקים משתמשים בפלטפורמת עוזרי ה-AI: השירות, התשלום, תקופת הניסיון, האחריות וסיום ההסכם.",
    privacy: "אילו נתונים אישיים הפלטפורמה מעבדת על בעלי עסקים והצוות שלהם, למה, לכמה זמן ואיך לממש את הזכויות שלכם.",
    dpa: "הסכם עיבוד הנתונים שכל עסק מקבל לפני העלייה לאוויר: איך נתוני הלקוחות מעובדים בשמו, ועל ידי אילו מעבדי משנה.",
    security: "איך הפלטפורמה מגינה על נתונים: הצפנה, בקרת גישה, גיבויים, ניטור ואיך לדווח על פגיעות.",
    contact: "מי מספק את פלטפורמת עוזרי ה-AI ואיך להגיע לאדם: ערוצי תמיכה ופרטי המפעיל.",
  },
  footerLabel: "משפטי ויצירת קשר",
  draftTitle: "טיוטה",
  draftText:
    "עורך דין עדיין לא בדק את הטקסט הזה, והשדות בסוגריים מרובעים עדיין ממתינים למילוי. הוא מתפרסם כדי שתוכלו לקרוא מה השירות יציע; הוא עדיין לא בתוקף בנוסחו הנוכחי.",
  document: {
    upcoming: "גרסה חדשה נכנסת לתוקף ב-{date}; היא כבר פורסמה.",
    otherLanguage: "הטקסט הזה עדיין לא זמין בשפה שלכם; הוא מוצג ב{language}.",
  },
  unavailable: "לא הצלחנו לטעון את הטקסט כרגע. נסו שוב מאוחר יותר.",
  dpaLead: "כל עסק בפלטפורמה מקבל את ההסכם הזה בלוח הבקרה שלו לפני העלייה לאוויר; הוא מסביר איך נתוני הלקוחות מעובדים בשם העסק.",
  related: "מסמכים נוספים",
  contactTitle: "יצירת קשר",
  contactLead: "מי מספק את השירות ואיך להגיע לאדם.",
  operatorTitle: "המפעיל",
  legalName: "שם",
  address: "כתובת",
  taxId: "מספר עוסק",
  country: "מדינה",
  email: "דוא״ל",
  operatorMissing: "הכתובת ופרטי הרישום של המפעיל יפורסמו כאן לפני שהשירות ייפתח ללקוחות.",
  supportTitle: "כתבו לנו",
  supportWhatsApp: "WhatsApp",
  supportTelegram: "Telegram",
  supportEmail: "דוא״ל",
  supportMissing: "פרטי התמיכה יופיעו כאן לפני שהשירות ייפתח ללקוחות.",
  securityReportTitle: "מצאתם פגיעות?",
  securityReportText: "דווחו עליה באופן פרטי; ההסבר איך לעשות זאת נמצא בקובץ security.txt שלנו.",
  securityReportLink: "פתיחת הכללים לחוקרי אבטחה",
};
