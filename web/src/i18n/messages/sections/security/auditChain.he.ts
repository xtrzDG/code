/** `auditChain.*` בעברית: בדיקת יומן הפעולות לשינויים. */

import type { Translation } from "../../../translate";
import type { auditChainEn } from "./auditChain.en";

export const auditChainHe: Translation<typeof auditChainEn> = {
  title: "בדיקת שינויים",
  status: {
    unchecked: "עדיין לא נבדק",
    intact: "שלם",
    broken: "שונה",
  },
  verdict: {
    unchecked: "כל רשומה חתומה יחד עם הרשומה שלפניה. הבדיקה היומית הראשונה תתבצע בתוך יממה.",
    intact: "כל רשומה חתומה יחד עם הרשומה שלפניה, והבדיקה היומית מצאה את כל הרשומות כפי שנרשמו.",
    broken: "הבדיקה היומית מצאה שרשומה {position} אינה כפי שנרשמה: {problem}. צוות הפלטפורמה קיבל התראה.",
  },
  problems: {
    hash_mismatch: "היא שונתה",
    link_broken: "רשומה שלפניה שונתה, נמחקה או נוספה",
    position_gap: "רשומה שלפניה נמחקה",
    head_lost: "הרשומות האחרונות נקטעו או נכתבו מחדש",
    checkpoint_mismatch: "רשומות שנמחקו בתום תקופת השמירה חזרו",
  },
  checkedAt: "נבדק {when}",
  verifiedThrough: "נבדק עד רשומה {position}",
  purgedThrough: "רשומות עד {position} נמחקו בתום תקופת השמירה",
};
