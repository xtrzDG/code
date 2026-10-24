/** `live.*` in Hebrew: the live cabinet (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { liveEn } from "./live.en";

export const liveHe: Translation<typeof liveEn> = {
  status: {
    live: "בזמן אמת",
    connecting: "מתחברים…",
    reconnecting: "מתחברים מחדש…",
    paused: "העדכונים בזמן אמת מושהים",
  },
  updatedJustNow: "עודכן הרגע",
  updatedMinutesAgo: {
    one: "עודכן לפני דקה",
    two: "עודכן לפני שתי דקות",
    other: "עודכן לפני {count} דקות",
  },
  updatedAt: "עודכן ב-{time}",
  updating: "מעדכנים…",
  liveHint: "העמוד מתעדכן מעצמו כשלקוחות כותבים, מזמינים או צריכים נציג.",
  reconnectingHint: "החיבור נקטע ואנחנו ממשיכים לנסות. אפשר גם לנסות עכשיו.",
  reconnect: "לנסות עכשיו",
  needsPersonTitle: "לקוח צריך נציג",
  needsPersonOpen: "פתיחה",
  sound: "צליל כשמישהו צריך נציג",
  soundHint: "צליל קצר במכשיר הזה כששיחה מועברת לצוות שלכם.",
};
