/** `auditChain.*` בעברית: בדיקת יומן הפעולות לשינויים. */

import type { Translation } from "../../../translate";
import type { auditChainEn } from "./auditChain.en";

export const auditChainHe: Translation<typeof auditChainEn> = {
  title: "בדיקת שינויים",
  status: {
    unchecked: "עדיין לא נבדק",
    unsealed: "עדיין אין רשומות חתומות",
    intact: "שלם",
    broken: "שונה",
  },
  verdict: {
    unchecked: "כל רשומה חדשה נחתמת יחד עם הרשומה שלפניה. הבדיקה היומית הראשונה תתבצע בתוך יממה.",
    unsealed: "רשומות נחתמות החל מהרשומה הראשונה שנכתבה אחרי שהחתימה הופעלה, והבדיקה האחרונה עוד לא מצאה כאלה. רשומות מוקדמות יותר אינן חתומות.",
    intact: "כל רשומה שנכתבה מאז שהחתימה הופעלה חתומה יחד עם הרשומה שלפניה, והבדיקה היומית מצאה את כולן כפי שנרשמו. רשומות מוקדמות יותר אינן חתומות.",
    broken: "הבדיקה היומית מצאה בעיה ברשומה {position}: {problem}. צוות הפלטפורמה קיבל התראה.",
  },
  problems: {
    hash_mismatch: "היא שונתה",
    link_broken: "רשומה שלפניה שונתה, נמחקה או נוספה",
    position_gap: "היא נמחקה",
    head_lost: "הרשומות האחרונות נקטעו או נכתבו מחדש",
    checkpoint_mismatch: "רשומות שנמחקו בתום תקופת השמירה חזרו",
  },
  checkedAt: "נבדק {when}",
  verifiedThrough: "נבדק עד רשומה {position}",
  purgedThrough: "רשומות עד {position} נמחקו בתום תקופת השמירה",
};
