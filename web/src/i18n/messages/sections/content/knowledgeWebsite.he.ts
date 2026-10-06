/** `knowledgeWebsite.*` in Hebrew: importing from the website (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { knowledgeWebsiteEn } from "./knowledgeWebsite.en";

export const knowledgeWebsiteHe: Translation<typeof knowledgeWebsiteEn> = {
  website: {
    tabsLabel: "מה לייבא",
    tabMenu: "תפריט או מחירון",
    tabWebsite: "מהאתר שלכם",
    title: "ייבוא מהאתר שלכם",
    description:
      "תנו את כתובת האתר. נקרא עד 15 מהעמודים שלו — תפריט, מחירים, שירותים, שאלות ושעות פתיחה — ונראה לכם מה מצאנו לפני שמשהו משתנה.",
    address: "כתובת האתר",
    addressHint: "האתר שלכם, למשל https://my-cafe.ge",
    start: "לקרוא את האתר שלי",
    starting: "מתחילים…",
    safety: "רק עמודים ציבוריים נקראים. שום דבר לא מגיע ללקוחות עד שתבדקו את הפריטים ותוסיפו אותם.",
    progressLabel: "קוראים את האתר שלכם",
    queued: "מתחילים עוד רגע…",
    opening: "פותחים את {host}…",
    reading: "קוראים עמוד {current} מתוך {total}",
    found: { one: "נמצא עד כה פריט אחד", other: "נמצאו עד כה {count} פריטים" },
    leaveHint: "אפשר לעזוב את העמוד: הייבוא ממשיך לרוץ ומה שהוא מוצא מחכה לכם כאן.",
    doneTitle: { one: "נמצא פריט אחד באתר שלכם", other: "נמצאו {count} פריטים באתר שלכם" },
    doneDescription: {
      one: "נקרא עמוד אחד. בדקו את הפריטים לפני שהם יתווספו.",
      other: "נקראו {count} עמודים. בדקו את הפריטים לפני שהם יתווספו.",
    },
    review: "בדיקת מה שנמצא",
    waitingTitle: "פריטים מהאתר שלכם מחכים לכם",
    waitingDescription: { one: "נמצא פריט אחד ב-{host}.", other: "נמצאו {count} פריטים ב-{host}." },
    nothingTitle: "לא נמצא שום דבר לייבוא",
    nothingDescription:
      "בעמודים לא היו תפריט, מחירים, שירותים, שאלות או שעות פתיחה שהצלחנו לקרוא. נסו כתובת אחרת או הוסיפו את הפריטים ידנית.",
    another: "לנסות כתובת אחרת",
    sourcePage: "מ-{page}",
    errors: {
      required: "הזינו את כתובת האתר שלכם",
      address: "הזינו כתובת אינטרנט כמו https://my-cafe.ge",
      failedTitle: "לא הצלחנו לקרוא את האתר",
      notPublic: "זה לא אתר ציבורי. השתמשו בכתובת שלקוחות פותחים בדפדפן.",
      notHttp: "השתמשו בכתובת אינטרנט שמתחילה ב-http:// או ב-https://.",
      port: "אי אפשר לקרוא כתובות עם פורט כמו ‎:8080. השתמשו בכתובת הרגילה של האתר.",
      credentials: "הסירו את שם המשתמש והסיסמה מהכתובת.",
      unknownHost: "לא נמצא אתר בכתובת הזו. בדקו את האיות.",
      timeout: "האתר לקח יותר מדי זמן לענות. נסו שוב בעוד כמה דקות.",
      unreachable: "לא הצלחנו לפתוח את האתר. בדקו את הכתובת ושהאתר פעיל.",
      httpStatus: "האתר ענה עם שגיאה {status}. בדקו את הכתובת.",
      unreadable: "הכתובת נפתחה, אבל לא כעמוד אינטרנט שאנחנו יכולים לקרוא (קובץ, או גדול מדי). נסו את כתובת עמוד הבית.",
      reader: "שירות הקריאה לא זמין כרגע. נסו שוב מאוחר יותר.",
      interrupted: "הייבוא נעצר לפני שהסתיים. התחילו אותו מחדש.",
      running: "האתר שלכם כבר נקרא. חכו עד שהייבוא הזה יסתיים.",
      tooMany: "האתר שלכם יובא 10 פעמים בשעה האחרונה. נסו שוב מאוחר יותר.",
    },
  },
};
