/** `setup.*` in Hebrew: creating the assistant before it exists (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { setupEn } from "./setup.en";

export const setupHe: Translation<typeof setupEn> = {
  navEntry: "יצירת עוזר AI",
  navEntryHint: "צעד אחר צעד, כ-20 דקות",
  eyebrow: "{business}",
  title: "בואו ניצור את עוזר ה-AI שלכם",
  description:
    "ספרו לנו על העסק בכמה צעדים פשוטים. נכין עוזר שעונה ללקוחות שלכם יומם ולילה, מקבל הזמנות וקורא לכם כשצריך אדם.",
  start: "יצירת עוזר AI",
  continue: "המשך היצירה",
  progress: "{done} מתוך {total} צעדים הושלמו",
  duration: "כ-20 דקות. אפשר לעצור ולחזור בכל זמן.",
  stagesLabel: "איך זה עובד",
  stages: {
    business: {
      title: "ספרו על העסק",
      description: "פרטי קשר, שעות פתיחה ומה אתם מציעים.",
    },
    rules: {
      title: "למדו אותו את הכללים שלכם",
      description: "הזמנות, תשובות לשאלות נפוצות ומתי לקרוא לכם.",
    },
    meet: {
      title: "הכירו את העוזר שלכם",
      description: "נסו אותו בצ׳אט, ואז הפעילו אותו עבור הלקוחות.",
    },
  },
  staffTitle: "העוזר בתהליך יצירה",
  staffDescription: "הבעלים של {business} מגדירים אותו. שיחות, הזמנות ופניות יופיעו כאן ברגע שהוא יהיה מוכן.",
  create: "יצירת העוזר שלי",
};
