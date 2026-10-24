/** `dataExports.*` in Hebrew (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { dataExportsEn } from "./dataExports.en";

export const dataExportsHe: Translation<typeof dataExportsEn> = {
  csv: {
    button: "ייצוא CSV",
    bookingsHint: "ההזמנות שהמסננים מציגים, כגיליון (CSV)",
    inboxLabel: "ייצוא השיחות האלה כ-CSV",
    inboxHint: "התצוגה והערוץ שנבחרו, כולל כל ההודעות",
    tableLabel: "הורדת {table} כ-CSV",
    saved: "הקובץ הורד",
    tables: {
      bookings: "הזמנות",
      leads: "פניות",
      contacts: "לקוחות",
      conversations: "שיחות",
      audit_log: "יומן פעולות",
    },
  },
  full: {
    title: "ייצוא הנתונים שלכם",
    description:
      "כל מה שנשמר עבור העסק שלכם בקובץ ZIP אחד: לקוחות, שיחות עם כל ההודעות, שיחות טלפון, הזמנות, פניות, שירותים, שיחות שלא נענו, משובים ויומן הפעולות, כ-JSON וכגיליונות (CSV).",
    start: "הכנת ייצוא מלא",
    started: "הייצוא בהכנה",
    working: "מכינים את הארכיון. זה לוקח כמה דקות; אפשר לעזוב את העמוד ולחזור.",
    history: "ייצואים אחרונים",
    empty: "עדיין אין ייצואים. הכינו אחד בכל פעם שתצטרכו עותק של הנתונים שלכם.",
    requested: "התבקש {date}",
    readyUntil: "נשמר עד {date}",
    download: "הורדת ZIP",
    downloadLabel: "הורדת הייצוא שהתבקש {date}",
    downloadStarted: "ההורדה התחילה",
    downloadsLeft: { one: "נשארה הורדה {count} מתוך {total}", other: "נשארו {count} הורדות מתוך {total}" },
    usedUp: "הייצוא הזה הורד שלוש פעמים. הכינו חדש לעותק נוסף.",
    gone: "הייצוא הזה כבר לא נשמר. הכינו חדש.",
    sizeKb: "{size} KB",
    sizeMb: "{size} MB",
    records: { one: "רשומה אחת", other: "{count} רשומות" },
    failed: "לא הצלחנו ליצור את הארכיון. הכינו אותו שוב; אם זה נכשל שוב, כתבו לתמיכה.",
    status: {
      queued: "ממתין",
      running: "בהכנה",
      ready: "מוכן",
      expired: "נמחק",
      failed: "נכשל",
    },
    linkNote:
      "כל הורדה יוצרת קישור חד-פעמי שעובד 10 דקות ורק עבורכם. אפשר להוריד ייצוא שלוש פעמים בתוך יממה, וכל הבעלים מקבלים הודעה מי הוריד אותו, מאיזה מכשיר ומאיזו כתובת.",
    erasedNote: "לקוחות שהנתונים שלהם נמחקו לא מופיעים באף ייצוא.",
  },
  tables: {
    title: "טבלאות כגיליונות",
    description: "טבלה אחת כ-CSV, ל-Excel, ל-Numbers או ל-Google Sheets. הזמנות ותיבת ההודעות מיוצאות גם עם המסננים שתבחרו שם.",
  },
};
