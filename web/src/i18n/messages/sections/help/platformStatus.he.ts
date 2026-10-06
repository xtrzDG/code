/** `platformStatus.*` in Hebrew: the status page (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { platformStatusEn } from "./platformStatus.en";

export const platformStatusHe: Translation<typeof platformStatusEn> = {
  title: "סטטוס הפלטפורמה",
  description: "האם צ׳אטים עם לקוחות, ערוצים, שיחות טלפון ולוח הבקרה עובדים כרגע, ואיך עברו 90 הימים האחרונים.",
  overall: {
    operational: "הכול עובד",
    maintenance: "מתבצעת תחזוקה מתוכננת",
    degraded: "חלקים מסוימים איטיים מהרגיל",
    outage: "חלקים מסוימים לא עובדים כרגע",
    no_data: "עדיין לא נמדד דבר",
  },
  levels: {
    operational: "עובד",
    maintenance: "תחזוקה",
    degraded: "איטי",
    outage: "לא עובד",
    no_data: "אין נתונים",
  },
  components: {
    chat: "צ׳אט באתר ועמוד צ׳אט",
    meta: "WhatsApp, Instagram ו-Messenger",
    telegram: "Telegram",
    voice: "שיחות טלפון",
    cabinet: "לוח הבקרה וההתחברות",
  },
  checkedAt: "נבדק {time}",
  monitoringDelayed: {
    title: "הבדיקות של הפלטפורמה עצמה מתעכבות",
    minutesAgo: {
      one: "הבדיקה האחרונה הייתה לפני דקה.",
      two: "הבדיקה האחרונה הייתה לפני שתי דקות.",
      other: "הבדיקה האחרונה הייתה לפני {count} דקות.",
    },
    at: "בדיקה אחרונה: {time}",
    body: "עד שהבדיקות יתעדכנו אף אחד לא יכול להתחייב לרמות שלמטה, ולכן הצ'אטים מוצגים כאיטיים יותר.",
  },
  componentsTitle: "חלקי הפלטפורמה",
  historyLabel: "{component}: 90 הימים האחרונים",
  historyStart: "לפני 90 יום",
  historyEnd: "היום",
  uptime: {
    one: "{share} ללא תקלות ביום אחד",
    other: "{share} ללא תקלות במשך {count} ימים",
  },
  observingSince: "במעקב מאז {date}",
  noHistory: "עדיין לא נמדדו ימים",
  day: "{day}: {level}",
  announcementLevels: {
    info: "הודעה",
    maintenance: "תחזוקה",
    degraded: "איטיות",
    outage: "תקלה",
  },
  activeTitle: "עכשיו",
  scheduled: "מתוכנן",
  starts: "מתחיל {time}",
  since: "מאז {time}",
  expectedEnd: "צפוי להסתיים {time}",
  resolved: "נפתר {time}",
  updated: "עודכן {time}",
  affects: "משפיע על: {components}",
  pastTitle: "תקלות קודמות",
  pastEmpty: "לא היו תקלות ב-90 הימים האחרונים.",
  unreachable: {
    title: "לא ניתן לטעון את הסטטוס",
    body: "העמוד הזה לא מצליח להגיע לפלטפורמה כרגע. אם גם הצ׳אטים לא עובדים, כתבו לתמיכה: הצוות כבר יודע.",
  },
  selfMeasured: "הפלטפורמה בודקת את עצמה כל חמש דקות; הצוות מוסיף את מה שהוא יודע.",
  openCabinet: "פתיחת לוח הבקרה",
  banner: {
    region: "הודעת הפלטפורמה",
    details: "פרטים",
    dismiss: "הסתרה",
  },
};
