/** `dpaNotice.*` in Hebrew: a new data processing agreement (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { dpaNoticeEn } from "./dpaNotice.en";

export const dpaNoticeHe: Translation<typeof dpaNoticeEn> = {
  label: "הסכם עיבוד נתונים חדש",
  title: "להסכם עיבוד הנתונים יש גרסה חדשה ({version})",
  due: "היא מחליפה את הגרסה שאישרתם. קראו ואשרו אותה עד {date}: כדי להחיל שינויים על העוזר נדרשת הגרסה הנוכחית.",
  overdue:
    "היא מחליפה את הגרסה שאישרתם, והמועד לאישורה היה {date}: כדי להחיל שינויים על העוזר נדרשת הגרסה הנוכחית, לכן קראו ואשרו אותה עכשיו.",
  action: "קריאה ואישור",
};
