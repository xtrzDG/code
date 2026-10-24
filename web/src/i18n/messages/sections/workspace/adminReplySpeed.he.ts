/** `adminReplySpeed.*` in Hebrew (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { adminReplySpeedEn } from "./adminReplySpeed.en";

export const adminReplySpeedHe: Translation<typeof adminReplySpeedEn> = {
  title: "מהירות התשובה, 7 ימים",
  description: "כמה זמן לקוחות חיכו, מההודעה הראשונה שלא נענתה ועד התשובה של העוזר.",
  median: "המתנה טיפוסית (חציון)",
  p95: "19 מתוך 20 תשובות בתוך",
  replies: "תשובות שנמדדו",
  slowNote: "יותר מתשובה אחת מכל עשרים לקחה יותר מ-15 שניות. בדקו את ספק המודל ואת הכלים של העסק.",
  empty: "אין תשובות שנמדדו ב-7 הימים האחרונים. צ׳אטים נמדדים מהגרסה הזו והלאה; שיחות טלפון וצ׳אט הניסיון לא נמדדים.",
  tableCaption: "מהירות התשובה לפי ערוץ",
  channel: "ערוץ",
  channelReplies: "תשובות",
  channelMedian: "חציון",
  channelP95: "95%",
  seconds: "{value} שנ׳",
  minutes: "{value} דק׳",
  issueLabel: "תשובות איטיות",
};
