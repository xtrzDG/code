/** `segments.*` in Hebrew: Customers → Segments (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { segmentsEn } from "./segments.en";

export const segmentsHe: Translation<typeof segmentsEn> = {
  loading: "טוענים פלחים…",
  new: "פלח חדש",
  empty: "עדיין אין פלחים",
  emptyDescription: "שמרו קבוצת לקוחות, למשל לקוחות קבועים שלא חזרו 60 יום, והורידו אותה לקמפיין.",
  limit: "עסק שומר לכל היותר 50 פלחים. מחקו אחד כדי לשמור אחר.",
  members: "לקוחות",
  noMembers: "כרגע אף אחד לא מתאים לפלח הזה.",
  showMore: "להציג עוד לקוחות",
  export: "הורדת CSV",
  exportHint: "הלקוחות של הפלח עם הטלפונים, הערוצים, התגיות וההזמנות שלהם, לקמפיין במקום אחר.",
  edit: "עריכה",
  delete: "מחיקה",
  deleteTitle: "למחוק את הפלח „{name}”?",
  deleteBody: "רק הכללים השמורים נמחקים; אף לקוח לא משתנה.",
  deleted: "הפלח נמחק",
  saved: "הפלח נשמר",
  editor: {
    newTitle: "פלח חדש",
    editTitle: "עריכת הפלח",
    name: "שם",
    namePlaceholder: "למשל: לא חזרו 60 יום",
    rules: "מי שייך",
    rulesHint: "כל כלל שתמלאו חייב להתקיים. לקוחות חסומים ומחוקים לעולם לא שייכים.",
    tag: "תגית",
    anyTag: "כל תגית",
    lastVisit: "ביקור אחרון לפני יותר מ… ימים",
    minBookings: "לפחות … הזמנות",
    maxBookings: "לכל היותר … הזמנות",
    vipOnly: "רק לקוחות VIP",
    save: "שמירת הפלח",
  },
  errors: {
    name: "תנו לפלח שם (עד 60 תווים).",
    days: "מספר הימים הוא מספר שלם בין 1 ל-3650.",
    bookings: "מספר ההזמנות הוא מספר שלם בין 0 ל-10000.",
    minMax: "„לפחות” לא יכול להיות גדול מ„לכל היותר”.",
  },
  preview: {
    counting: "סופרים…",
    count: { one: "לקוח אחד מתאים", other: "{count} לקוחות מתאימים" },
    atLeast: { one: "לפחות לקוח אחד מתאים", other: "לפחות {count} לקוחות מתאימים" },
    none: "עדיין אף אחד לא מתאים.",
  },
  summary: {
    everyone: "כל לקוח",
    tag: "התגית „{tag}”",
    lastVisit: { one: "ביקור אחרון לפני יותר מיום", other: "ביקור אחרון לפני יותר מ-{count} ימים" },
    minBookings: { one: "לפחות הזמנה אחת", other: "לפחות {count} הזמנות" },
    maxBookings: { one: "לכל היותר הזמנה אחת", other: "לכל היותר {count} הזמנות" },
    vipOnly: "רק VIP",
  },
};
