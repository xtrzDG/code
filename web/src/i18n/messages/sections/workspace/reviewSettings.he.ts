/** `reviewSettings.*` in Hebrew (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { reviewSettingsEn } from "./reviewSettings.en";

export const reviewSettingsHe: Translation<typeof reviewSettingsEn> = {
  description: "שאלו לקוחות איך היה הביקור, הזמינו את כולם לכתוב עליכם ביקורת ב-Google, וראו מה הם ענו.",
  stats: {
    title: "30 הימים האחרונים",
    description: "לקוחות שנשאלו על הביקור שלהם, ומה הם ענו.",
    asked: "נשאלו",
    answered: "ענו",
    answeredShare: "{percent} מאלה שנשאלו",
    average: "דירוג ממוצע",
    averageValue: "{score} מתוך 5",
    noAverage: "עדיין אין דירוגים",
    opened: "פתחו את קישור הביקורת",
    notTracked: "לא נספר בפלטפורמה הזו",
    scores: "דירוגים",
    scoreRow: { one: "כוכב {score}: {count}", other: "{score} כוכבים: {count}" },
    notAsked: "לא נשאלו: {count}",
    notDelivered: "לא נמסרו: {count}",
  },
  feedback: {
    title: "משוב אחרי ביקורים",
    description:
      "אחרי ביקור שהושלם אנחנו מבקשים מהלקוח לדרג אותו מ-1 עד 5, במסנג׳ר שבו השתמש ובשפה שלו. הפלטפורמה עונה לדירוג בעצמה: מודה לו ושולחת את קישור הביקורת שלכם.",
    toggle: "לשאול לקוחות איך היה הביקור",
    turnedOff: "כבר לא שואלים לקוחות על הביקור שלהם",
    delay: "מתי לשאול",
    delayHint: "נספר מסוף ההזמנה.",
    delayMinutes: { one: "דקה אחרי הביקור", other: "{count} דקות אחרי הביקור" },
    delayHours: { one: "שעה אחרי הביקור", two: "שעתיים אחרי הביקור", other: "{count} שעות אחרי הביקור" },
    delayDays: { one: "יום אחרי הביקור", two: "יומיים אחרי הביקור", other: "{count} ימים אחרי הביקור" },
    template: "שם תבנית ה-WhatsApp",
    templateHint: "ללקוחות WhatsApp שלא כתבו 24 שעות: תבנית השירות המאושרת במספר שלכם (אותיות לטיניות קטנות, ספרות וקווים תחתונים).",
    templateInvalid: "השתמשו רק באותיות לטיניות קטנות, ספרות וקווים תחתונים.",
    readiness: {
      off: "בקשות המשוב כבויות.",
      everywhere: "לקוחות נשאלים ב-Telegram, ב-WhatsApp, ב-Messenger וב-Instagram; לקוחות WhatsApp ששתקו יום מקבלים את התבנית שלכם.",
      window: "לקוחות נשאלים בתוך 24 שעות מההודעה האחרונה שלהם; לקוחות WhatsApp ששתקו יותר מזה מדולגים עד שהתבנית תוגדר.",
    },
    whatsappMissing: "WhatsApp לא מחובר.",
    connectWhatsapp: "חיבור WhatsApp",
    rules:
      "על כל ביקור שואלים פעם אחת, וכל לקוח לכל היותר פעם ביום. לקוחות שענו STOP לא מקבלים בקשות. דירוג של 3 ומטה עובר גם לתיבת הודעות → צריך אדם, כדי שמישהו ייצור קשר.",
  },
  link: {
    title: "קישור לביקורת ב-Google",
    description: "כל מי שעונה מקבל את הקישור הזה עם התודה, בלי קשר לדירוג: הזמנת לקוחות מרוצים בלבד נוגדת את הכללים של Google.",
    label: "קישור לעמוד הביקורות שלכם ב-Google",
    hint: "ב-Google Business Profile, בחרו „בקשת ביקורות” והעתיקו את הקישור.",
    invalid: "הזינו קישור מלא שמתחיל ב-https://",
    tracked: "אנחנו שולחים אותו דרך הכתובת הקצרה של הפלטפורמה כדי לספור כמה לקוחות פותחים אותו.",
    missing: "בלי קישור, הלקוחות רק מקבלים תודה.",
  },
  template: {
    title: "טקסט התבנית",
    description:
      "צרו ב-Meta Business Manager תבנית שירות של WhatsApp עם הטקסט הזה, תרגום אחד לכל שפה; הפרמטר היחיד שלה הוא שם העסק שלכם. הלקוחות מקבלים אותה בשפה שלהם, או באנגלית כשאין תרגום.",
    body: "הטקסט לתבנית",
    example: "מה הלקוחות קוראים",
  },
  requests: {
    title: "הבקשות האחרונות",
    description: "20 הביקורים האחרונים ששאלנו עליהם, ומה הלקוחות ענו.",
    empty: "עדיין אין בקשות",
    emptyDescription: "לקוחות נשאלים אחרי הביקורים שלהם ברגע שהמשוב מופעל.",
    customer: "לקוח",
    visitEnded: "הביקור הסתיים {time}",
    rating: "דירג {score} מתוך 5",
    openedLink: "פתח את קישור הביקורת",
    openConversation: "פתיחת השיחה",
    notAskedBecause: "לא נשאל: {reason}",
    statuses: {
      sent: "ממתין לתשובה",
      answered: "ענה",
      skipped: "לא נשאל",
      failed: "לא נמסר",
    },
    skipReasons: {
      opted_out: "הלקוח ענה STOP",
      no_contact: "הפרטים של הלקוח נמחקו",
      no_channel: "אין מסנג׳ר לכתוב בו",
      window_closed: "WhatsApp דורש את התבנית המאושרת אחרי 24 שעות",
      already_asked: "כבר נשאל היום",
      daily_limit: "המגבלה היומית של הודעות הושגה",
    },
  },
};
