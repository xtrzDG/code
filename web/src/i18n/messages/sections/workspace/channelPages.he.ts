/** `channelPages.*` in Hebrew (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { channelPagesEn } from "./channelPages.en";

export const channelPagesHe: Translation<typeof channelPagesEn> = {
  heading: "הגדרה",
  back: "כל הערוצים",
  website: {
    title: "צ׳אט באתר",
    hint: "צבע, כפתור, הקוד לאתר שלכם והיכן הוא יכול להופיע",
  },
  calls: {
    title: "הפניית שיחות",
    hint: "קודים ששולחים לעוזר את השיחות שאתם מפספסים",
  },
  share: {
    title: "שיתוף",
    hint: "קישורים, קוד QR וכרטיס שולחן",
  },
  off: {
    website: "הצ׳אט באתר כבוי. הפעילו אותו בין הערוצים כדי לבחור את המראה שלו ולהציב אותו באתר שלכם.",
    calls: "ערוץ הטלפון לא מחובר. חברו אותו בין הערוצים כדי לקבל את קודי ההפניה שלכם.",
  },
};
