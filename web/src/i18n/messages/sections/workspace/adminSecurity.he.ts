/** `adminSecurity.*` in Hebrew (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { adminSecurityEn } from "./adminSecurity.en";

export const adminSecurityHe: Translation<typeof adminSecurityEn> = {
  nav: "מפתחות הצפנה",
  title: "מפתחות הצפנה",
  description: "המפתחות שחותמים את אסימוני הערוצים ולוחות השנה, והעברת כל אסימון שמור למפתח החדש ביותר.",
  ring: {
    title: "צרור המפתחות",
    keyCount: "מפתחות בצרור",
    single: "מפתח אחד חותם ופותח הכול. כדי להחליף אותו, שימו מפתח חדש ראשון ב-ENCRYPTION_KEYS, פרסו, ואז הצפינו מחדש כאן.",
    several: {
      one: "המפתח הראשון חותם כל דבר חדש; מפתח ישן אחד רק פותח את מה שהוא חתם. הצפינו מחדש, ואז הסירו אותו כפי שמדריך התפעול מסביר.",
      other: "המפתח הראשון חותם כל דבר חדש; {count} מפתחות ישנים רק פותחים את מה שהם חתמו. הצפינו מחדש, ואז הסירו אותם כפי שמדריך התפעול מסביר.",
    },
  },
  run: {
    title: "הצפנה מחדש",
    description: "כל אסימון של ערוץ ולוח שנה נחתם מחדש עם המפתח החדש ביותר, ו-webhooks של Telegram נרשמים מחדש עם הסוד שלו.",
    start: "הצפנה מחדש של האסימונים השמורים",
    confirmTitle: "להצפין מחדש כל אסימון שמור?",
    confirmBody:
      "ה-worker ברקע חותם מחדש כל אסימון של ערוץ ולוח שנה עם המפתח החדש ביותר ורושם מחדש את ה-webhooks של Telegram. הלקוחות לא מרגישים כלום. ההרצה נרשמת ביומן הפעולות.",
    confirm: "הצפנה מחדש",
    starting: "מתחילים…",
    started: "ההצפנה מחדש נכנסה לתור",
    alreadyRunning: "הצפנה מחדש כבר רצה.",
    none: "עדיין לא בוצעה הצפנה מחדש",
    noneDescription: "הריצו אותה אחרי שמפתח חדש הוצב ראשון ב-ENCRYPTION_KEYS. עם מפתח אחד היא רק בודקת שכל אסימון נפתח.",
    status: {
      queued: "בתור",
      running: "רצה",
      done: "הסתיימה",
      failed: "נכשלה",
    },
    facts: {
      requested: "התבקשה",
      started: "התחילה",
      finished: "הסתיימה",
      keys: "מפתחות בצרור באותו זמן",
      total: "אסימונים שנבדקו",
      current: "כבר על המפתח החדש ביותר",
      rotated: "נחתמו מחדש",
      unreadable: "לא ניתנים לפתיחה",
      webhooksRenewed: "webhooks של Telegram שנרשמו מחדש",
      webhooksFailed: "webhooks של Telegram שלא נרשמו",
    },
    verdict: {
      working: "ה-worker מצפין מחדש. העמוד מתעדכן מעצמו.",
      clean: "כל אסימון שמור חתום עם המפתח החדש ביותר. מפתחות ישנים יכולים לצאת אחרי שקישורי ההתראות והקלטות השיחות שהם חתמו פגו (ראו מדריך התפעול).",
      cleanSingle: "כל אסימון שמור נפתח עם המפתח היחיד בצרור.",
      unreadable: {
        one: "אסימון אחד לא נפתח עם אף מפתח: הבעלים שלו צריך לחבר מחדש את הערוץ.",
        other: "{count} אסימונים לא נפתחים עם אף מפתח: הבעלים שלהם צריכים לחבר מחדש את הערוצים.",
      },
      webhooks: {
        one: "webhook אחד של Telegram לא נרשם מחדש: הצפינו מחדש שוב מאוחר יותר.",
        other: "{count} webhooks של Telegram לא נרשמו מחדש: הצפינו מחדש שוב מאוחר יותר.",
      },
      failed: "ההרצה נעצרה: {error}. התחילו אותה שוב; אסימונים שכבר הועברו נשארים מועברים.",
      keysChanged: "צרור המפתחות השתנה אחרי ההרצה הזו ({then} מפתחות אז, {now} עכשיו): הצפינו מחדש שוב.",
    },
  },
};
