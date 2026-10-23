/** `providerCircuits.*` in Hebrew (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { providerCircuitsEn } from "./providerCircuits.en";

export const providerCircuitsHe: Translation<typeof providerCircuitsEn> = {
  title: "מפסקי ספקים",
  description:
    "לכל ספק שתהליכי הרקע שולחים דרכו יש מפסק. חמש תקלות בדקה פותחות אותו: הודעות ממתינות בלי לפנות לספק, ואחרי 30 שניות עוברת שליחת ניסיון אחת. ספק אחד תופס לכל היותר מחצית מתהליכי המסירה של תהליך רקע.",
  none: "אף תהליך רקע לא דיווח על המפסקים שלו",
  noneDescription: "תהליכי הרקע מדווחים על המפסקים בכל דופק; תהליך רקע של גרסה קודמת לא מדווח עליהם.",
  circuit: "מפסק",
  state: "מצב",
  workers: "תהליכי רקע שבהם אינו סגור",
  workersOf: "{notClosed} מתוך {total}",
  failures: "תקלות בדקה האחרונה",
  opened: "נפתח",
  states: {
    closed: "סגור",
    half_open: "מנסה שוב",
    open: "פתוח",
  },
  providers: {
    meta: "Meta (WhatsApp, Messenger, Instagram)",
    telegram: "בוטים של Telegram",
    platform_bot: "בוט הפלטפורמה",
    twilio_sms: "SMS (Twilio)",
    smtp: "דואר אלקטרוני (SMTP)",
    flitt: "תשלומים (Flitt)",
    web_push: "התראות דפדפן",
  },
};
