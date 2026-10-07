/** `setupGuide.*` in Hebrew: the setup guide card and milestones (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { setupGuideEn } from "./setupGuide.en";

export const setupGuideHe: Translation<typeof setupGuideEn> = {
  titleSetup: "הגדירו את העוזר שלכם",
  titleLive: "הביאו את הלקוחות הראשונים",
  descriptionSetup: "כל שלב נפתח במקום שבו עצרתם. העוזר עונה ללקוחות אחרי שהוא מתפרסם.",
  liveSince: "עונה ללקוחות מאז {date}",
  minutesLeft: { one: "נשארה בערך דקה", other: "נשארו בערך {count} דקות" },
  continueSetup: "המשך ההגדרה",
  afterLaunchHint: "אחרי ההפעלה: בדיקה מהטלפון, ערוץ שני והקישור ללקוחות.",
  minutes: "{count} דק׳",
  optional: "לא חובה",
  skip: "דילוג",
  unskip: "החזרה",
  skipLabel: "דילוג על „{step}”",
  unskipLabel: "החזרת „{step}”",
  status: {
    next: "הבא",
    skipped: "דולג",
  },
  phone: {
    description: "כוונו את מצלמת הטלפון אל הקוד וכתבו לעוזר כמו שלקוח היה כותב.",
    qrAlt: "קוד QR של {link}",
    copyLink: "העתקת הקישור",
    unavailable: "עמוד הצ׳אט כבוי. הפעילו את הצ׳אט באתר בערוצים, או כתבו מהטלפון למסנג׳ר מחובר.",
    orTelegram: "או ב-Telegram:",
    listening: "ממתינים להודעה שלכם…",
    hint: "השלב יושלם כשההודעה שלכם תגיע.",
    success: "זה עובד: ההודעה שלכם הגיעה לעוזר.",
    hide: "הסתרה",
  },
  finished: {
    title: "הכול מוכן",
    description: "העוזר עונה ללקוחות, והם יודעים איפה למצוא אותו.",
    dismiss: "הסתרת הכרטיס",
  },
  wins: {
    title: "הושג",
    first_conversation: "השיחה הראשונה עם לקוח",
    first_booking: "ההזמנה הראשונה",
    first_after_hours_booking: "ההזמנה הראשונה אחרי שעות הפעילות",
  },
  ring: {
    title: "הגדרה",
    label: "ההגדרה הושלמה ב-{percent}%",
    short: "{percent}%",
  },
  celebrations: {
    first_conversation: {
      title: "הלקוח הראשון כתב",
      description: "העוזר ענה. השיחה נמצאת בתיבת ההודעות.",
    },
    first_booking: {
      title: "ההזמנה הראשונה",
      description: "העוזר הזמין לקוח בעצמו.",
    },
    first_after_hours_booking: {
      title: "הזמנה כשהייתם סגורים",
      description: "לקוח הזמין אחרי שעות הפעילות, ואף אחד לא היה צריך לענות.",
    },
    openInbox: "פתיחת תיבת ההודעות",
    openBookings: "פתיחת ההזמנות",
    close: "סגירה",
  },
};
