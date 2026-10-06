/** `publicPricing.*` in Hebrew: prices on the public site (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { publicPricingEn } from "./publicPricing.en";

export const publicPricingHe: Translation<typeof publicPricingEn> = {
  converted: "{price} לחודש במטבע שלכם",
  billedIn: "מסלולים למדינה הזו מחויבים ב-{currency}.",
  conversionNote: "סכומים עם ≈ הם להתמצאות בלבד: הומרו מאירו לפי {source} נכון ל-{date}; התשלום הוא באירו.",
  rateSources: {
    nbg: "השער הרשמי של הבנק הלאומי של גאורגיה",
    ecb: "שער הייחוס של הבנק המרכזי האירופי",
    official: "השערים הרשמיים של הבנקים המרכזיים",
    planning: "שער התכנון של הפלטפורמה (לא שער של בנק)",
  },
  setup: {
    title: "להגדיר בעצמכם, או לתת לנו לעשות את זה",
    subtitle: "אותו עוזר בכל מקרה. אתם בוחרים כשאתם נרשמים למסלול.",
    selfTitle: "בעצמכם",
    selfPrice: "חינם",
    selfPoints: {
      guide: "מדריך של שמונה צעדים קצרים, עם תשובות מוכנות לסוג העסק שלכם",
      test: "צ׳אט ניסיון ובדיקות אוטומטיות לפני ההפעלה",
      channels: "אתם מחברים את הערוצים עם עזרה צעד אחר צעד",
    },
    doneTitle: "אנחנו עושים בשבילכם",
    donePrice: "{price} חד-פעמי",
    donePoints: {
      knowledge: "אנחנו ממלאים את המחירים, התפריט והכללים שלכם מהאתר או מהקבצים",
      channels: "אנחנו מחברים את הערוצים ואת הפניית השיחות",
      launch: "אנחנו בודקים את העוזר יחד איתכם ומפעילים אותו ביחד",
    },
  },
  testimonials: {
    title: "מה אומרים בעלי עסקים",
  },
};
