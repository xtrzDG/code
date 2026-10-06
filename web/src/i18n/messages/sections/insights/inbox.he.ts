/** `inbox.*` in Hebrew: the team inbox (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { inboxEn } from "./inbox.en";

export const inboxHe: Translation<typeof inboxEn> = {
  title: "תיבת הודעות",
  viewsLabel: "הצגת שיחות",
  views: {
    needs_person: "צריך אדם",
    requests: "פניות",
    mine: "שלי",
    unassigned: "לא משויכות",
    all: "הכול",
  },
  moreViews: "עוד",
  moreViewsChosen: "עוד: {view}",
  viewCount: {
    one: "שיחה אחת",
    other: "{count} שיחות",
  },
  empty: {
    needs_person: {
      title: "אף אחד לא מחכה לאדם",
      description: "כשהעוזר מעביר שיחה לצוות שלכם, היא מופיעה כאן מיד.",
    },
    requests: {
      title: "אין פניות פתוחות",
      description: "אירועים, ביקורי קבוצות ובקשות אחרות שהעוזר רושם ממתינים כאן עד שמישהו מטפל בהם.",
    },
    mine: {
      title: "שום דבר לא משויך אליכם",
      description: "שיחות שלקחתם, או שהועברו אליכם, ממתינות כאן כל עוד הן צריכות את הצוות.",
    },
    unassigned: {
      title: "לכל שיחה יש מטפל",
      description: "שיחות שצריכות את הצוות ואין מי שיטפל בהן מופיעות כאן.",
    },
    all: {
      title: "עדיין אין שיחות",
      description: "שיחות מופיעות כאן ברגע שלקוחות כותבים לעוזר או מתקשרים אליו.",
    },
  },
  showAll: "לכל השיחות",
  loading: "טוענים את תיבת ההודעות…",
  listLabel: "שיחות",
  searchLabel: "חיפוש בכל השיחות",
  searchPlaceholder: "חיפוש: שם, טלפון או טקסט",
  filters: {
    open: "מסננים",
    openWithCount: "מסננים ({count})",
    title: "מסננים",
    description: "תקופה, סטטוס ושיחות ניסיון חלים על כל השיחות ועל החיפוש.",
    show: "הצגת שיחות",
    clear: "ניקוי המסננים",
    includeTest: "לכלול שיחות ניסיון",
  },
  results: "תוצאות עבור „{search}”",
  clearSearch: "ניקוי החיפוש",
  row: {
    unassigned: "אף אחד לא משויך",
    assignedTo: "בטיפול של {name}",
    you: "אתם",
    notes: {
      one: "הערה אחת",
      other: "{count} הערות",
    },
    request: "פנייה: {type}",
    waiting: "ממתין מאז {time}",
  },
  assign: {
    open: "שיוך",
    menuLabel: "מי מטפל בשיחה הזו",
    handledBy: "בטיפול של {name}",
    handledByYou: "אתם מטפלים בה",
    automatically: "שויכה אוטומטית",
    nobody: "עדיין אף אחד לא מטפל בה",
    takeIt: "לקחת אותה",
    unassign: "ביטול השיוך",
    you: "אתם",
    teammate: "חבר צוות",
    waiting: {
      one: "{count} ממתינה",
      other: "{count} ממתינות",
    },
    loading: "טוענים את הצוות…",
    assigned: "{name} מטפל עכשיו בשיחה הזו",
    taken: "אתם מטפלים עכשיו בשיחה הזו",
    cleared: "עכשיו אף אחד לא משויך",
    conflict: "מישהו אחר שינה לפני רגע מי מטפל בשיחה הזו. כך זה נראה עכשיו.",
    colleague: "עמית מטפל בשיחה הזו. בקשו מאחד הבעלים להעביר אותה.",
    notMember: "האדם הזה כבר לא בצוות.",
  },
};
