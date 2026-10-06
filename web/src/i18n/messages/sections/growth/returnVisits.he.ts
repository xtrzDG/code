/** `returnVisits.*` in Hebrew: Bookings → Return visits (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { returnVisitsEn } from "./returnVisits.en";

export const returnVisitsHe: Translation<typeof returnVisitsEn> = {
  loading: "טוענים ביקורים חוזרים…",
  rules: {
    rebook: "הזמנה לחזור",
    recall: "תזכורת שהגיע מועד בדיקה",
    pre_arrival: "הודעה לפני הגעה",
  },
  ruleHints: {
    rebook: "נשלחת מספר הימים שבחרתם אחרי הביקור האחרון של הלקוח, אלא אם הוא כבר הזמין שוב.",
    recall: "נשלחת מספר הימים שבחרתם אחרי הביקור האחרון, לבדיקה או לטיפול קבוע.",
    pre_arrival: "נשלחת מספר הימים שבחרתם לפני תחילת ההזמנה, עם תזכורת של התאריך.",
  },
  settings: {
    title: "הודעות ביקור חוזר",
    description: "הודעה אחת שמחזירה לקוחות, בערוץ ובשפה שלהם. שום דבר לא נשלח עד שתפעילו אותה.",
    toggle: "שליחת הודעות ביקור חוזר",
    rule: "מה לשלוח",
    daysAfter: "ימים אחרי הביקור האחרון",
    daysBefore: "ימים לפני ההגעה",
    suggested: {
      one: "מקובל בסוג העסק שלכם: „{rule}” אחרי יום אחד.",
      other: "מקובל בסוג העסק שלכם: „{rule}” אחרי {count} ימים.",
    },
    suggestedBefore: {
      one: "מקובל בסוג העסק שלכם: „{rule}” יום אחד לפני.",
      other: "מקובל בסוג העסק שלכם: „{rule}” {count} ימים לפני.",
    },
    useSuggested: "להשתמש בזה",
    audience: "מי יכול לקבל אותה",
    audiences: {
      all_customers: "כל לקוח שהכלל מוצא",
      segment: "רק הלקוחות של פלח אחד",
    },
    segment: "פלח",
    chooseSegment: "בחרו פלח",
    noSegments: "עדיין אין פלחים שמורים.",
    toSegments: "צרו אחד בלקוחות → פלחים",
    cap: "לכל היותר בחודש",
    capHint: "ההודעות נעצרות עד סוף החודש כשמגיעים למספר הזה.",
    monthSent: { one: "הודעה אחת נשלחה החודש, מתוך {cap}", other: "{count} הודעות נשלחו החודש, מתוך {cap}" },
    honours:
      "לקוחות שכתבו STOP, נמצאים ברשימת „לא ליצור קשר” או חסומים לעולם לא יקבלו אותה. לקוח מקבל לכל היותר הודעה אחת כזו בשבועיים, ואף אחת אחרי שהזמין שוב.",
    whatsapp:
      "ב-WhatsApp, לקוח שלא כתב 24 שעות מקבל את התבנית המאושרת של הפלטפורמה להזמנות ולתזכורות; הודעה לפני הגעה ממתינה לשיחה פתוחה.",
    save: "שמירה",
    saved: "הודעות הביקור החוזר נשמרו",
    errors: {
      days: "מספר הימים הוא מספר שלם בין 1 ל-730.",
      cap: "התקרה החודשית היא מספר שלם בין 1 ל-2000.",
      segment: "בחרו פלח, או כתבו לכל לקוח שהכלל מוצא.",
    },
  },
  recent: {
    title: "30 הימים האחרונים",
    sent: "נשלחו",
    booked: "הזמינו שוב",
    skipped: "לא נשלחו",
  },
  preview: {
    title: "מה הלקוחות קוראים",
    description: "ההודעה בכל אחת משפות העסק, עם התאריך כפי שהיה ממולא היום.",
  },
  messages: {
    title: "ההודעות האחרונות",
    description: "מי קיבל הודעה ומי הזמין שוב אחריה.",
    empty: "עדיין אין הודעות",
    emptyDescription: "כשההודעות מופעלות, בדיקה שעתית כותבת ללקוחות שהגיע זמנם.",
    customer: "לקוח",
    status: {
      sent: "נשלחה",
      booked: "הזמין שוב",
      skipped: "לא נשלחה",
    },
    skipReasons: {
      opted_out: "הלקוח ביקש שלא יכתבו לו",
      no_contact: "הלקוח לא ידוע או שנמחק",
      no_channel: "אין ערוץ שדרכו אפשר להגיע אליו",
      window_closed: "חלון 24 השעות סגור ואין תבנית",
    },
    notSentBecause: "לא נשלחה: {reason}",
    sentAt: "נשלחה {time}",
    bookedAt: "הזמין {time}",
    openConversation: "פתיחת השיחה",
    showMore: "להציג עוד",
  },
};
