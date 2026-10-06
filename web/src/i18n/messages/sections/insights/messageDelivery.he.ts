/** `messageDelivery.*` in Hebrew (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { messageDeliveryEn } from "./messageDelivery.en";

export const messageDeliveryHe: Translation<typeof messageDeliveryEn> = {
  label: "מסירה",
  states: {
    sending: "שולחים…",
    retrying: "עדיין לא נמסרה, מנסים שוב",
    delivered: "נמסרה",
    failed: "לא נמסרה",
  },
  nextAttempt: "ניסיון הבא ב-{time}",
  reasons: {
    rate_limited: "המסנג׳ר ביקש להמתין",
    provider_unavailable: "המסנג׳ר לא ענה",
    recipient_refused: "המסנג׳ר דחה אותה (ייתכן שהלקוח חסם את העסק, או שחלון 24 השעות נסגר)",
    template_rejected: "WhatsApp לא קיבל את תבנית ההודעה",
    channel_disconnected: "הערוץ כבר לא מחובר",
    credential_rejected: "הגישה של הערוץ הפסיקה לעבוד: חברו אותו מחדש בערוצים",
    not_configured: "אין דרך להעביר את ההודעה הזו",
    expired: "הרגע שלה עבר לפני שהספיקה לצאת",
  },
};
