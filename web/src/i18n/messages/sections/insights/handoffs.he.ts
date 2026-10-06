/** `handoffs.*` in Hebrew: conversations that need a person (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { handoffsEn } from "./handoffs.en";

export const handoffsHe: Translation<typeof handoffsEn> = {
  loading: "טוענים…",
  tabsLabel: "הצגה",
  tabs: {
    open: "ממתינות",
    resolved: "טופלו",
    all: "הכול",
  },
  urgency: {
    critical: "קריטי",
    high: "דחוף",
    normal: "רגיל",
    low: "נמוך",
  },
  reason: {
    customer_request: "ביקש אדם",
    complaint: "תלונה",
    vip_guest: "אורח VIP",
    non_standard_request: "בקשה לא שגרתית",
    unknown_answer: "העוזר לא ידע את התשובה",
    emergency: "מקרה חירום",
    sensitive_topic: "נושא רגיש",
    profile_rule: "אחד הכללים שלכם",
    unverified_numbers: "מחירים או נתונים לא מאומתים",
  },
  status: {
    pending: "מודיעים לצוות",
    notified: "הצוות קיבל הודעה",
    notification_failed: "ההודעה נכשלה",
    resolved: "טופל",
  },
  notificationFailedHint: "הצוות לא קיבל את ההודעה. התקשרו ללקוח בחזרה ובדקו את אנשי הקשר בהגדרות.",
  resolvedAt: "טופל {date}",
  resolve: "סימון כטופל",
  confirmResolve: {
    title: "לסמן כטופל?",
    description: "{name}: העוזר מתחיל לענות ללקוח הזה שוב.",
    confirm: "סימון כטופל",
  },
  resolved: "סומן כטופל",
  emptyOpenTitle: "אף אחד לא מחכה לאדם",
  emptyOpenDescription: "כשהעוזר מעביר שיחה לאדם, היא ממתינה כאן עם סיכום קצר.",
  emptyTitle: "עדיין אין כאן כלום",
  summaryCodes: {
    model_declined: "העוזר לא הסכים לענות על ההודעה הזו.",
    model_unavailable: "העוזר לא היה זמין לרגע ולא הצליח לענות.",
    answer_unfinished: "העוזר לא הצליח לסיים את התשובה שלו.",
    unverified_values: "העוזר עצר תשובה עם נתונים או טענות שלא מופיעים בפרטי העסק שלכם.",
    call_booking_unverified_values: "בשיחה העוזר ציין נתונים שלא מופיעים בפרטי העסק שלכם. בדקו את ההזמנה מהשיחה הזו מול התמלול.",
    call_request_unverified_values: "בשיחה העוזר ציין נתונים שלא מופיעים בפרטי העסק שלכם. בדקו את הפנייה מהשיחה הזו מול התמלול.",
    reply_undelivered: "התשובה של העוזר לא הגיעה ללקוח. צרו איתו קשר בדרך אחרת.",
    data_erased: "הפרטים נמחקו לבקשת הלקוח.",
  },
  summaryCodesWithValues: {
    unverified_values: "העוזר עצר תשובה עם נתונים או טענות שלא מופיעים בפרטי העסק שלכם ({values}).",
    call_booking_unverified_values:
      "בשיחה העוזר ציין נתונים שלא מופיעים בפרטי העסק שלכם ({values}). בדקו את ההזמנה מהשיחה הזו מול התמלול.",
    call_request_unverified_values:
      "בשיחה העוזר ציין נתונים שלא מופיעים בפרטי העסק שלכם ({values}). בדקו את הפנייה מהשיחה הזו מול התמלול.",
  },
  quote: {
    customer: "ההודעה של הלקוח",
    reply: "התשובה שלא הגיעה",
  },
};
