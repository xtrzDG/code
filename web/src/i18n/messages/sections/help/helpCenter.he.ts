/** `helpCenter.*` in Hebrew: the help center and the support panel (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { helpCenterEn } from "./helpCenter.en";

export const helpCenterHe: Translation<typeof helpCenterEn> = {
  title: "עזרה",
  description: "מדריכים קצרים לכל חלק בלוח הבקרה.",
  searchLabel: "חיפוש בעזרה",
  searchPlaceholder: "Telegram, הזמנה, חשבונית…",
  search: "חיפוש",
  clearSearch: "ניקוי החיפוש",
  results: {
    one: "נמצא מאמר אחד",
    other: "נמצאו {count} מאמרים",
  },
  noResults: "לא נמצא דבר עבור „{query}”. נסו מילה אחרת.",
  topics: {
    getting_started: "צעדים ראשונים",
    channels: "ערוצים",
    daily_work: "עבודה יומיומית",
    account: "חשבון וחיוב",
  },
  allArticles: "כל המאמרים",
  related: "לקריאה בהמשך",
  otherLanguage: "המאמר הזה עדיין לא תורגם, ולכן הוא מוצג ב{language}.",
  pageHelp: "עזרה לעמוד הזה",
  drawerTitle: "עזרה",
  openInCenter: "פתיחה במרכז העזרה",
  back: "חזרה",
  stillStuck: "עדיין תקועים?",
  stillStuckLead: "כתבו לנו: אדם מהצוות יענה.",
  noSupportLead: "בדקו את סטטוס הפלטפורמה: כשמשהו לא עובד לכולם, הצוות כבר מטפל בזה.",
  tipsAgain: "להציג שוב את הטיפים",
  tipsShown: "הטיפים יוצגו שוב בעמודי תיבת ההודעות, העוזר והערוצים.",
  opensInNewTab: "נפתח בלשונית חדשה",
  support: {
    title: "עזרה ותמיכה",
    center: "מרכז העזרה",
    whatsNew: "מה חדש",
    unread: {
      one: "{count} חדש",
      other: "{count} חדשים",
    },
    status: "סטטוס הפלטפורמה",
    contact: "כתיבה לתמיכה",
    whatsapp: "WhatsApp",
    telegram: "Telegram",
    email: "דוא״ל",
  },
};
