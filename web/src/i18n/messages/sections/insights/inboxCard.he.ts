/** `inboxCard.*` in Hebrew: the conversation card in the inbox (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { inboxCardEn } from "./inboxCard.en";

export const inboxCardHe: Translation<typeof inboxCardEn> = {
  back: "חזרה לתיבת ההודעות",
  openDetails: "פרטים",
  openDetailsOf: "פרטי השיחה עם {name}",
  openNotes: "הערות",
  openNotesCount: {
    one: "הערות ({count})",
    other: "הערות ({count})",
  },
  panelLabel: "על השיחה הזו",
  panelTabs: "לוח",
  messageContext: {
    story_reply: "תגובה לסטורי שלכם",
    story_mention: "אזכור בסטורי של הלקוח",
  },
  offeredChoices: "אפשרויות שהוצעו",
  actions: {
    label: "פעולות מהירות",
    resolve: "סימון כטופל",
    resolveHint: "העוזר עונה ללקוח הזה שוב",
    call: "חיוג",
    callLabel: "חיוג ל-{phone}",
    book: "הזמנה",
  },
  work: {
    needsPerson: "צריך אדם",
    request: "פנייה",
    requestStatus: "סטטוס הפנייה",
    since: "מאז {time}",
  },
  details: {
    customer: "לקוח",
    channel: "ערוץ",
    language: "שפה",
    started: "התחילה",
    lastMessage: "הודעה אחרונה",
  },
  technical: {
    title: "פרטים טכניים",
    hint: "מה עומד מאחורי התשובות: העדכון של העוזר שנתן אותן והבקשות המדויקות שלו לנתונים שלכם.",
    tokens: "טוקנים",
    cost: "עלות AI",
    version: "גרסת העוזר",
    message: "פרטים טכניים של ההודעה הזו",
  },
  notes: {
    title: "הערות",
    hint: "רק הצוות שלכם רואה את זה",
    description: "הערות נשארות בתוך הצוות: הלקוח והעוזר אף פעם לא רואים אותן.",
    placeholder: "מה הובטח, מי חוזר ללקוח, מה לזכור…",
    add: "הוספת הערה",
    adding: "שומרים…",
    added: "ההערה נשמרה. רק הצוות שלכם רואה אותה.",
    unknownAuthor: "חבר צוות לשעבר",
    delete: "מחיקת ההערה",
    confirmDelete: {
      title: "למחוק את ההערה הזו?",
      description: "היא תיעלם לכל הצוות.",
      confirm: "מחיקה",
    },
    deleted: "ההערה נמחקה",
    empty: "עדיין אין הערות. הערה עוזרת למי שבא אחריכם: מה הובטח, מי חוזר ללקוח.",
    loading: "טוענים הערות…",
    length: "{count} / {max}",
  },
  quickReplies: {
    open: "תשובות מהירות",
    hint: "הקלידו / לתשובות מהירות",
    listLabel: "תשובות מהירות",
    loading: "טוענים תשובות מהירות…",
    empty: "עדיין אין תשובות מהירות.",
    emptyOwner: "צרו תשובות שאתם שולחים לעיתים קרובות בהגדרות → תשובות מהירות.",
    manage: "ניהול תשובות מהירות",
    noMatch: "אין תשובה מהירה שמתאימה ל„/{query}”.",
    missing: "מלאו לפני השליחה:",
    fillLabel: "ערך עבור {variable}",
    fill: "מילוי",
    placeholdersLeft: "מלאו את החלקים שבסוגריים המסולסלים לפני השליחה: {variables}.",
    variables: {
      name: "שם הלקוח",
      booking_time: "שעת ההזמנה",
      business_name: "שם העסק",
    },
  },
  composer: {
    placeholder: "כתבו ללקוח…",
    sendLabel: "שליחה",
  },
  request: {
    updated: "פנייה: {status}",
  },
  resolveConfirm: {
    title: "לסמן כטופל?",
    description: "{name}: העוזר מתחיל לענות ללקוח הזה שוב.",
    confirm: "סימון כטופל",
  },
  resolved: "סומן כטופל. העוזר עונה ללקוח הזה שוב.",
  reopened: "ההעברה פתוחה שוב. העוזר שותק עד שהיא תטופל.",
};
