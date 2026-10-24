/** `adminReplyGuard.*` in Hebrew (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { adminReplyGuardEn } from "./adminReplyGuard.en";

export const adminReplyGuardHe: Translation<typeof adminReplyGuardEn> = {
  title: "שומר התשובות, 7 ימים",
  description:
    "תשובות שהשומר עצר כי נתונים, טענות או פרטי קשר לא נתמכו בנתוני העסק, והודעות שניסו לשנות את ההנחיות של העוזר.",
  checked: "תשובות שנבדקו",
  heldBack: "נעצרו",
  heldBackShare: "{share} מהתשובות",
  rewritten: "נוסחו מחדש פעם אחת",
  handedOff: "הועברו לצוות",
  injectionFlags: "ניסיונות הזרקה",
  heldBackNote: "השומר עצר לפחות תשובה אחת מכל שש. בדקו את העובדות והמחירים של העסק: חסר לעוזר משהו שלקוחות שואלים עליו.",
  probedNote: "מישהו מנסה שוב ושוב לשנות את ההנחיות של העוזר. אנשי הקשר נעצרים ליום אחרי שלושה ניסיונות; בדקו את השיחות.",
  empty: "אין תשובות שנבדקו ב-7 הימים האחרונים.",
  issueLabel: "קפיצה בשומר התשובות",
};
