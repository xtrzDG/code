/** `growthValue.*` in Hebrew (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { growthValueEn } from "./growthValue.en";

export const growthValueHe: Translation<typeof growthValueEn> = {
  label: "הזמנות שהעוזר החזיר",
  waitlist: { one: "הזמנה אחת מרשימת ההמתנה", other: "{count} מרשימת ההמתנה" },
  campaign: { one: "הזמנה אחת אחרי הודעת ביקור חוזר", other: "{count} אחרי הודעות ביקור חוזר" },
  worth: "≈ {money}",
  waitlistHint: "מקומות שהתפנו ונתפסו על ידי לקוחות שחיכו.",
  campaignHint: "לקוחות שהזמינו שוב אחרי ההודעה.",
  rows: {
    waitlistBookings: "הזמנות מרשימת ההמתנה",
    waitlistValue: "שווי ההזמנות מרשימת ההמתנה",
    campaignBookings: "הזמנות אחרי הודעות ביקור חוזר",
    campaignValue: "שווי ההזמנות אחרי הודעות ביקור חוזר",
  },
};
