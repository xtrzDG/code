/** `updates.*` in Hebrew: owner checks in an update, drafts and the test chat target (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { updatesEn } from "./updates.en";

export const updatesHe: Translation<typeof updatesEn> = {
  expectation: {
    must_mention: "התשובה חייבת להזכיר „{text}”",
    must_not_mention: "התשובה לא יכולה להזכיר „{text}”",
    must_hand_off: "התשובה חייבת להעביר את הלקוח לאדם",
    must_create_lead: "התשובה חייבת לרשום פנייה",
  },
  failed: {
    one: "הבדיקה שלכם לא עברה: „{question}” — {expectation}",
    many: {
      one: "בדיקה אחת שלכם לא עברה",
      other: "{count} מהבדיקות שלכם לא עברו",
    },
    rest: "כל השאר עבר. הלקוחות ממשיכים לקבל את התשובות הקודמות עד שהבדיקה תעבור.",
    result: "הבדיקה שלכם לא עברה",
    openCheck: "פתיחת הבדיקה",
    fixAnswer: "תיקון התשובה",
    answered: "העוזר ענה",
    applyAfterFix: "החלת שינויים",
  },
  pending: {
    checksTitle: "הבדיקות שלכם",
    checksHint: "העדכון שואל אותן קודם. אם אחת לא עוברת, הלקוחות ממשיכים לקבל את התשובות הקודמות.",
    added: "בדיקה חדשה: „{question}”",
    changed: "בדיקה ששונתה: „{question}”",
    draftsTitle: "טיוטות",
    draftsHint: "נבנו ידנית ומעולם לא הגיעו ללקוחות. מחיקת טיוטה שומרת את השינויים שלכם.",
    draft: "טיוטה מ-{date}",
    open: "פתיחה",
    discard: "מחיקה",
    discardLabel: "מחיקת הטיוטה מ-{date}",
    discardTitle: "למחוק את הטיוטה הזו?",
    discardDescription: "הלקוחות מעולם לא קיבלו אותה. השינויים שלכם נשארים: „החלת שינויים” הבאה תיבנה מהם.",
    discarded: "הטיוטה נמחקה",
    onlyDrafts: "כל מה ששיניתם מגיע ללקוחות. נשארה טיוטה:",
  },
  checkNow: {
    savedTitle: "הבדיקה נשמרה",
    action: "לבדוק עכשיו",
    actionLabel: "לבדוק עכשיו את „{question}”",
    checking: "בודקים…",
    hint: "שיחת ניסיון אחת עם מה שהלקוחות מקבלים עכשיו.",
    passed: "עברה עם מה שהלקוחות מקבלים עכשיו.",
    failed: "לא עברה עם מה שהלקוחות מקבלים עכשיו.",
    errored: "הבדיקה לא הצליחה להסתיים. נסו שוב בעוד דקה.",
    notLive: "עדיין שום דבר לא מגיע ללקוחות: הבדיקה תרוץ ב„החלת שינויים” הראשונה.",
    limited: "בדקתם הרבה בשעה הזו. נסו שוב מאוחר יותר.",
    checkedAt: "נבדק {date}",
  },
  language: {
    auto: "שפת השאלה",
  },
  chat: {
    target: "שיחה עם",
    live: "מה שהלקוחות מקבלים עכשיו",
    changes: "עם השינויים שלכם",
    history: "מההיסטוריה: עדכון {number}",
    noteLive: "אתם מדברים עם מה שהלקוחות מקבלים עכשיו. שיחות ניסיון לא מגיעות ללקוחות, לצוות או לחיוב.",
    noteChanges: "אתם מדברים עם העוזר עם השינויים האחרונים שלכם, לפני שהלקוחות מקבלים אותם. שיחות ניסיון לא מגיעות ללקוחות, לצוות או לחיוב.",
    noteHistory: "אתם מדברים עם עדכון מההיסטוריה. שיחות ניסיון לא מגיעות ללקוחות, לצוות או לחיוב.",
  },
  publishGate: {
    adminOnly: "למנהלי הפלטפורמה בלבד",
  },
};
