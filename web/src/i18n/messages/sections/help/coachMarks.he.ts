/** `coachMarks.*` in Hebrew (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { coachMarksEn } from "./coachMarks.en";

export const coachMarksHe: Translation<typeof coachMarksEn> = {
  label: "טיפ",
  gotIt: "הבנתי",
  readGuide: "לקריאת המדריך",
  inbox: {
    title: "תיבת ההודעות של הצוות",
    body: "שיחות שצריכות נציג מופיעות ראשונות. פתחו שיחה כדי לענות, להעביר אותה לעמית או להשאיר הערה שרק הצוות רואה.",
  },
  assistant: {
    title: "נסו את העוזר כאן קודם",
    body: "כתבו כמו שלקוח היה כותב. מה שאתם מלמדים את העוזר מופיע כאן לפני שהלקוחות מקבלים אותו.",
  },
  channels: {
    title: "חברו את המקומות שבהם הלקוחות כותבים",
    body: "התחילו בערוץ שהלקוחות שלכם משתמשים בו הכי הרבה. כל כרטיס מראה אם הוא עובד ומתי הגיעה ההודעה האחרונה.",
  },
};
