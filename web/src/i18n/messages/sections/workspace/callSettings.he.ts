/** `callSettings.*` in Hebrew (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { callSettingsEn } from "./callSettings.en";

export const callSettingsHe: Translation<typeof callSettingsEn> = {
  description: "מה קורה אחרי כל שיחה: סיכום לצוות, והודעה למתקשרים שלא הצליחו לעבור.",
  summaries: {
    title: "סיכומי שיחות",
    description:
      "אחרי כל שיחה, צ׳אטי הצוות ב-Telegram וב-WhatsApp מקבלים מי התקשר, מה רצה, איך השיחה הסתיימה וכל דבר שהעוזר אמר שלא מופיע בנתונים שלכם. על מתקשרים שלא הצליחו לעבור מדווח בכל ערוץ, כדי שמישהו יחזור אליהם.",
    toggle: "שליחת סיכום אחרי כל שיחה",
    contactsHint: "מי מקבל אותם: אנשי הקשר בצוות בהגדרות → התראות.",
    openContacts: "אנשי קשר בצוות",
    turnedOff: "סיכומי השיחות כבויים",
  },
  textBack: {
    title: "הודעה חוזרת למתקשרים שפספסתם",
    description:
      "כשמתקשר לא מצליח לעבור (הקו תפוס, אף אחד לא עונה, הוא מנתק מוקדם, העוזר לא יכול לקבל את השיחה, או שאף אחד לא עונה להעברה), אנחנו כותבים לו תוך דקה או שתיים, בשפה שלו. התשובה שלו ממשיכה כשיחת WhatsApp בתיבת ההודעות.",
    toggle: "שליחת הודעה למתקשרים שלא הצליחו לעבור",
    template: "שם תבנית ה-WhatsApp",
    templateHint: "השם של תבנית השירות המאושרת במספר ה-WhatsApp שלכם: אותיות לטיניות קטנות, ספרות וקווים תחתונים.",
    templateInvalid: "השתמשו רק באותיות לטיניות קטנות, ספרות וקווים תחתונים.",
    sms: "שליחת SMS כש-WhatsApp לא אפשרי",
    smsHint: "משולח ה-SMS של הפלטפורמה, כשלמספר אין WhatsApp או שהתבנית נדחית.",
    smsNeedsTextBack: "קודם הפעילו הודעות למתקשרים שלא הצליחו לעבור.",
    rules: "כל מתקשר מקבל הודעה לכל היותר פעם ביום. לקוחות שביקשו לא לקבל הודעות, או שכבר כותבים לכם, לא מקבלים הודעה.",
    turnedOff: "ההודעות למתקשרים שלא הצליחו לעבור כבויות",
    smsTurnedOff: "SMS למתקשרים שלא הצליחו לעבור כבוי",
    readiness: {
      whatsapp: "המתקשרים מקבלים את תבנית ה-WhatsApp שלכם.",
      sms: "המתקשרים מקבלים SMS.",
      none: "עדיין אי אפשר לשלוח כלום: חברו את WhatsApp ותנו שם לתבנית, או אפשרו SMS.",
      off: "ההודעות החוזרות כבויות.",
    },
    whatsappMissing: "WhatsApp לא מחובר.",
    connectWhatsapp: "חיבור WhatsApp",
    smsMissing: "SMS לא מוגדר בפלטפורמה הזו.",
  },
  template: {
    title: "טקסט התבנית",
    description:
      "צרו ב-Meta Business Manager תבנית שירות של WhatsApp עם הטקסט הזה, תרגום אחד לכל שפה; הפרמטר היחיד שלה הוא שם העסק שלכם. המתקשרים מקבלים אותה בשפה שלהם, או באנגלית כשאין תרגום.",
    body: "הטקסט לתבנית",
    example: "מה המתקשרים קוראים",
  },
  history: {
    title: "ההודעות החוזרות האחרונות",
    description: "20 המתקשרים האחרונים שלא הצליחו לעבור, ומה נשלח אליהם.",
    empty: "עדיין אין שיחות שלא נענו",
    emptyDescription: "מתקשרים שלא מצליחים לעבור יופיעו כאן.",
    hiddenNumber: "מספר חסוי",
    openConversation: "פתיחת השיחה",
    notSentBecause: "לא נשלחה: {reason}",
    statuses: {
      queued: "שולחים",
      sent: "נשלחה",
      failed: "לא נמסרה",
      skipped: "לא נשלחה",
    },
    channels: {
      whatsapp: "WhatsApp",
      sms: "SMS",
    },
    reasons: {
      no_answer: "אין מענה",
      busy: "הקו תפוס",
      abandoned: "ניתק לפני המענה",
      line_failed: "השיחה לא חוברה",
      not_started: "העוזר לא יכול היה לקבל את השיחה",
      no_speech: "ניתק בלי לדבר",
      transfer_unanswered: "ההעברה לא נענתה",
    },
    skipReasons: {
      turned_off: "ההודעות החוזרות היו כבויות",
      opted_out: "הלקוח ביקש לא לקבל הודעות",
      already_texted: "כבר נשלחה הודעה היום",
      daily_limit: "המגבלה היומית הושגה",
      in_conversation: "הוא כבר כותב לכם",
      no_channel: "אין ערוץ לשלוח ממנו",
      not_live: "העוזר לא היה באוויר",
      no_caller_number: "המספר היה חסוי",
      too_late: "על השיחה דווח מאוחר מדי",
    },
  },
};
