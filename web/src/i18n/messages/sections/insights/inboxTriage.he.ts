/** `inboxTriage.*` in Hebrew: density, keys and bulk actions in the inbox (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { inboxTriageEn } from "./inboxTriage.en";

export const inboxTriageHe: Translation<typeof inboxTriageEn> = {
  density: {
    label: "שורות",
    comfortable: "מרווחות",
    compact: "צפופות",
  },
  resize: {
    label: "רוחב רשימת השיחות",
    hint: "גררו, או השתמשו במקשי החצים. לחיצה כפולה מחזירה לרוחב הרגיל.",
  },
  keys: {
    open: "קיצורי מקלדת",
    title: "קיצורי מקלדת",
    description: "עבדו על הרשימה בלי עכבר. המקשים עובדים כל עוד אתם לא מקלידים.",
    listHint: "J ו-K זזים ברשימה, E מסמן כטופל, A לוקח את השיחה, X בוחר אותה, סימן שאלה מציג את כל המקשים.",
    resolveNote: "טופל: העברה חוזרת לעוזר, ופנייה פתוחה מסומנת כנסגרה בהצלחה. ביטול נמצא בהודעה שמופיעה אחר כך.",
    actions: {
      next: "השיחה הבאה",
      previous: "השיחה הקודמת",
      open: "פתיחת השיחה",
      resolve: "סימון כטופל",
      assign: "לקחת אותה: אתם מטפלים בה",
      select: "בחירה לפעולה מרוכזת",
      search: "חיפוש",
      help: "הצגת המקשים האלה",
      clear: "ניקוי הבחירה",
    },
  },
  select: {
    row: "בחירת השיחה עם {name}",
    all: "בחירת כל השיחות שיש בהן משהו לסגור",
    count: {
      one: "אחת נבחרה",
      other: "{count} נבחרו",
    },
    resolve: "סימון כטופל",
    clear: "ניקוי הבחירה",
  },
  resolved: {
    one: "שיחה אחת טופלה",
    other: "{count} שיחות טופלו",
  },
  resolvedPartly: "{done} מתוך {total} טופלו. מישהו שינה את האחרות רגע קודם; הרשימה מציגה אותן כפי שהן עכשיו.",
  undone: "חזר למה שהיה",
  undonePartly: "חלק לא הצליחו לחזור: מישהו שינה אותן בינתיים. הרשימה מציגה אותן כפי שהן עכשיו.",
  nothingToResolve: "אין מה לסגור בשיחה הזו: אין העברה או פנייה פתוחות.",
  alreadyYours: "אתם כבר מטפלים בשיחה הזו.",
  age: {
    now: "עכשיו",
    minutes: "{count} דק׳",
    hours: "{count} שע׳",
    days: "{count} ימ׳",
  },
  details: {
    label: "על השיחה הזו",
    source: "הגיע מ",
    assignee: "בטיפול של",
    lastMessage: "הודעה אחרונה",
  },
};
