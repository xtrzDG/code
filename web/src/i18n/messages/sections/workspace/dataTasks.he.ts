/** `dataTasks.*` in Hebrew (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { dataTasksEn } from "./dataTasks.en";

export const dataTasksHe: Translation<typeof dataTasksEn> = {
  title: "משימות נתונים אחרי פריסה",
  description: {
    one: "הסבות מסמכים ומילוי עמודות חיפוש שה-worker של האצוות מריץ בעצמו באצוות של שורה אחת. הגרסה הבאה מקודמת רק אחרי שכל המשימות הסתיימו.",
    other: "הסבות מסמכים ומילוי עמודות חיפוש שה-worker של האצוות מריץ בעצמו באצוות של {size} שורות. הגרסה הבאה מקודמת רק אחרי שכל המשימות הסתיימו.",
  },
  open: {
    one: "משימה אחת פתוחה",
    other: "{count} משימות פתוחות",
  },
  allDone: "כל המשימות הסתיימו",
  failed: "{count} נכשלו",
  stalled: "{count} תקועות יותר מיממה",
  settled: "אף worker של גרסה אחרת לא רץ: המשימות רצות עכשיו.",
  waiting: "ממתינים שה-workers של {releases} ייעצרו (בערך {time}).",
  waitingUnnamed: "ממתינים שה-workers של גרסה ללא שם ייעצרו (בערך {time}).",
  none: "לגרסה הזו אין משימות נתונים.",
  openCaption: "משימות נתונים פתוחות",
  doneCaption: "משימות נתונים שהסתיימו",
  showDone: {
    one: "להציג משימה אחת שהסתיימה",
    other: "להציג {count} משימות שהסתיימו",
  },
  hideDone: "להסתיר משימות שהסתיימו",
  columns: {
    task: "משימה",
    status: "סטטוס",
    progress: "התקדמות",
    when: "מתי",
    actions: "פעולות",
  },
  kinds: {
    migrate_documents: "כתיבה מחדש של מסמכים לגרסה {version}",
    backfill_lookup: "מילוי עמודת החיפוש",
  },
  statuses: {
    pending: "ממתינה",
    running: "רצה",
    done: "הסתיימה",
    failed: "נכשלה",
  },
  lists: {
    customers: "רשימת הלקוחות",
    knowledge: "רשימת הידע",
  },
  holdsBack: "מעכבת: {lists}",
  rows: { one: "{scanned} מתוך כשורה אחת", other: "{scanned} מתוך כ-{estimate} שורות" },
  rowsUnknown: { one: "שורה אחת נבדקה", other: "{scanned} שורות נבדקו" },
  changed: { one: "{count} שונו, אצווה אחת", other: "{count} שונו, {batches} אצוות" },
  failedRows: { one: "לא הצלחנו לשדרג שורה אחת: {keys}", other: "לא הצלחנו לשדרג {count} שורות: {keys}" },
  dueSince: "ממתינה מאז {time}",
  doneAt: "הסתיימה {time}",
  lastBatch: "אצווה אחרונה {time}",
  isStalled: "תקועה",
  retry: "מעבר נוסף",
  retried: "המשימה עוברת שוב על הטבלה שלה.",
  indexing: {
    title: "עדיין מתבצע אינדוקס",
    body: "עדכון נתונים אחרי הגרסה האחרונה עדיין רץ, ולכן ייתכן שחלק מהרשומות הישנות יותר יחסרו ברשימה הזו לכמה דקות.",
  },
};
