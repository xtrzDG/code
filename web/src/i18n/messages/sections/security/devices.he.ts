/** `devices.*` in Hebrew: Account → Security, signed-in devices (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { devicesEn } from "./devices.en";

export const devicesHe: Translation<typeof devicesEn> = {
  title: "איפה אתם מחוברים",
  description: "כל דפדפן וטלפון שמחוברים לחשבון שלכם. התחברות שאף אחד לא משתמש בה 7 ימים מסתיימת מעצמה.",
  descriptionAdmin:
    "כל דפדפן וטלפון שמחוברים לחשבון שלכם. כמנהלי הפלטפורמה, התחברות מסתיימת אחרי 12 שעות ללא שימוש ויום אחרי הכניסה.",
  thisDevice: "המכשיר הזה",
  kind: {
    desktop: "מחשב",
    phone: "טלפון",
    tablet: "טאבלט",
    unknown: "מכשיר",
  },
  on: "{browser} ב-{system}",
  signedIn: "התחבר {date}",
  lastUsed: "שימוש אחרון {date}",
  from: "מ-{address}",
  twoFactor: "עם אפליקציית האימות",
  oneFactor: "עם קוד כניסה",
  ends: "יסתיים מעצמו {date}",
  end: "התנתקות",
  endLabel: "ניתוק {device}",
  endTitle: "לנתק את המכשיר הזה?",
  endDescription: "מי שמשתמש בו יצטרך להתחבר מחדש.",
  ended: "המכשיר נותק",
  endOthers: "התנתקות מכל המקומות האחרים",
  endOthersTitle: "לנתק את כל המכשירים האחרים?",
  endOthersDescription: "כל דפדפן וטלפון חוץ מהמכשיר הזה יצטרכו להתחבר מחדש.",
  endedOthers: {
    one: "מכשיר אחד נותק",
    other: "{count} מכשירים נותקו",
  },
  onlyThis: "רק המכשיר הזה מחובר.",
  notYou: "לא מזהים מכשיר? נתקו אותו, ואז הפעילו את אפליקציית האימות למעלה.",
};
