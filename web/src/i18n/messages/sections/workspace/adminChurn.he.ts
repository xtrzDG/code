/** `adminChurn.*` in Hebrew (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { adminChurnEn } from "./adminChurn.en";

export const adminChurnHe: Translation<typeof adminChurnEn> = {
  title: "למה בעלים מבטלים",
  description:
    "ביטולים בתקופה לפי הסיבה שהבעלים בחרו, ההצעות שהתקבלו במקום, הפסקות עונתיות וההודעות שנשלחו 14 ו-30 יום אחרי ביטול.",
  empty: "אין ביטולים, הצעות או הפסקות בתקופה הזו.",
  stats: {
    cancellations: "ביטלו",
    saved: "נשארו עם הצעה",
    pausesScheduled: "הפסקות שתוכננו",
    pausesEnded: "הפסקות שהסתיימו",
    winBackSent: "הודעות החזרה",
    returned: "חזרו אחרי הודעה",
  },
  reason: "סיבה",
  cancelled: "ביטלו",
  tookOffer: "קיבלו את ההצעה במקום",
  noReason: "לא נשאלו (לפני השאלה)",
  offersTitle: "הצעות שהתקבלו",
  commentsTitle: "במילים של הבעלים",
  openClient: "פתיחת הלקוח",
};
