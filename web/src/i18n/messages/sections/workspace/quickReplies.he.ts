/** `quickReplies.*` in Hebrew (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { quickRepliesEn } from "./quickReplies.en";

export const quickRepliesHe: Translation<typeof quickRepliesEn> = {
  description:
    "תשובות שהצוות שלכם שולח לעיתים קרובות, מוכנות בכל אחת משפות העסק. בשיחה, הקלידו / כדי להוסיף אחת: שם הלקוח וההזמנה שלו מתמלאים מעצמם.",
  add: "תשובה מהירה חדשה",
  loading: "טוענים תשובות מהירות…",
  emptyTitle: "עדיין אין תשובות מהירות",
  emptyDescription: "שעות פתיחה, הוראות הגעה, „נחזור אליכם”: כתבו אותן פעם אחת, שלחו בשתי הקשות.",
  listLabel: "תשובות מהירות",
  languages: "שפות",
  variablesUsed: "ממלאת",
  edit: "עריכה",
  editLabel: "עריכת התשובה המהירה „{title}”",
  delete: "מחיקה",
  deleteLabel: "מחיקת התשובה המהירה „{title}”",
  confirmDelete: {
    title: "למחוק את התשובה המהירה הזו?",
    description: "„{title}” תיעלם מהבורר לכל הצוות.",
    confirm: "מחיקה",
  },
  deleted: "התשובה המהירה נמחקה",
  saved: "התשובה המהירה נשמרה",
  editor: {
    newTitle: "תשובה מהירה חדשה",
    editTitle: "עריכת התשובה המהירה",
    description: "כתבו אותה בכל שפה שהלקוחות שלכם משתמשים בה. הצוות רואה את הטקסט בשפת השיחה.",
    title: "שם",
    titleHint: "מה שהצוות רואה בבורר.",
    shortcut: "קיצור",
    shortcutHint: "מוקלד אחרי / בתיבת התשובה: אותיות, ספרות, - ו-_.",
    shortcutInvalid: "השתמשו רק באותיות, ספרות, - ו-_, בלי רווחים.",
    texts: "טקסט",
    textIn: "טקסט ב{language}",
    textHint: "השאירו שפה ריקה אם אין בה צורך. נדרש לפחות טקסט אחד.",
    needOneText: "כתבו את הטקסט בשפה אחת לפחות.",
    insert: "הוספה",
    insertLabel: "הוספת {variable} לטקסט ב{language}",
    preview: "תצוגה מקדימה",
    previewHint: "עם לקוח והזמנה לדוגמה.",
    sample: {
      name: "נועה",
      bookingTime: "שבת, 19:30",
    },
    save: "שמירה",
    saving: "שומרים…",
    cancel: "ביטול",
    length: "{count} / {max}",
  },
  variables: {
    name: "שם הלקוח",
    booking_time: "שעת ההזמנה",
    business_name: "שם העסק",
  },
  errors: {
    shortcut_taken: "תשובה מהירה אחרת כבר משתמשת בקיצור הזה.",
    too_many_quick_replies: "עסק שומר לכל היותר 100 תשובות מהירות. מחקו אחת שאתם כבר לא משתמשים בה.",
    unknown_variable: "אפשר למלא רק את {name}, {booking_time} ו-{business_name}. בדקו את הסוגריים המסולסלים בטקסט.",
    duplicate_language: "לכל שפה יכול להיות טקסט אחד.",
  },
};
