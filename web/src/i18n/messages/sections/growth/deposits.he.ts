/** `deposits.*` in Hebrew: the deposit that holds a booking until it is paid on the owner's page. */

import type { Translation } from "../../../translate";
import type { depositsEn } from "./deposits.en";

export const depositsHe: Translation<typeof depositsEn> = {
  chip: "פיקדון",
  status: {
    awaiting: "ממתין לתשלום",
    paid: "שולם",
    expired: "לא שולם בזמן",
    cancelled: "בוטל",
    refund_due: "להחזרה",
    kept: "נשאר אצלכם",
  },
  booking: {
    label: "פיקדון",
    heldUntil: "המקום שמור עד {time}",
    reference: "קוד תשלום: {reference}",
    markPaid: "שולם",
    confirmTitle: "לסמן את הפיקדון כשולם?",
    confirmDescription:
      "סמנו כשתראו {amount} עם הקוד {reference} בחשבון הסליקה שלכם. ההזמנה תאושר לאחר מכן.",
    confirm: "כן, שולם",
    marked: "הפיקדון סומן כשולם",
    refundDue: "ההזמנה בוטלה בזמן: החזירו את הפיקדון דרך חשבון הסליקה שלכם.",
  },
  policy: {
    title: "פיקדון",
    description: "הלקוח משלם אותו בעמוד התשלום שלכם בעת ההזמנה. הסכום תמיד נלקח מכאן, והעוזר אף פעם לא בוחר אותו.",
    rule: "פיקדון",
    rules: {
      none: "בלי פיקדון",
      fixed: "סכום קבוע להזמנה",
      per_guest: "סכום לכל אורח",
      percent_of_value: "אחוז משווי ההזמנה",
    },
    amount: "סכום, {currency}",
    amountPerGuest: "סכום לכל אורח, {currency}",
    percent: "אחוז מהשווי",
    minParty: "מכמה אורחים",
    minPartyHint: "השאירו ריק כדי לבקש פיקדון בכל הזמנה.",
    page: "עמוד תשלום",
    defaultPage: "עמוד ברירת המחדל",
    pageHint: "עמוד עם סכום קבוע אחד מתאים רק לפיקדון קבוע באותו סכום.",
    save: "שמירת הפיקדון",
    saved: "הפיקדון נשמר",
    removed: "מעכשיו לא מבקשים פיקדון",
    off: "הפיקדונות כבויים, לכן עדיין לא מבקשים מאף אחד.",
    noPage: "הוסיפו קודם עמוד תשלום.",
    openSettings: "הגדרות פיקדונות",
    summary: {
      fixed: "פיקדון {amount}",
      per_guest: "פיקדון {amount} לכל אורח",
      percent_of_value: "פיקדון {percent}% מהשווי",
    },
    fromGuests: { one: "מאורח {count}", two: "מ-{count} אורחים", other: "מ-{count} אורחים" },
    errors: {
      percent: "הזינו אחוז בין 1 ל-100.",
      minParty: "הזינו מספר שלם של אורחים, 1 ומעלה.",
    },
  },
  settings: {
    title: "פיקדונות",
    description:
      "שמרו הזמנה עד שהלקוח משלם פיקדון בעמוד התשלום שלכם. העוזר שולח את הקישור שלכם עם הסכום שקבעתם; הוא אף פעם לא בוחר סכום או קישור.",
    toggle: "לבקש פיקדונות",
    toggleHint: "שולחנות, חדרים, אנשי מקצוע ושירותים עם פיקדון מבקשים אותו בעת ההזמנה.",
    turnedOff: "הפיקדונות כובו",
    holdMinutes: "המתנה לתשלום, בדקות",
    holdHint:
      "מ-15 דקות ועד יממה. בהמתנה של 30 דקות ומעלה הלקוח מקבל תזכורת אחת באמצע; מקום שלא שולם משתחרר אחר כך והלקוח מקבל הודעה.",
    refundHours: "החזר בביטול, כמה שעות לפני הביקור",
    refundHint: "בוטל מוקדם יותר: אתם מחזירים את הפיקדון. מאוחר יותר, או שהלקוח לא הגיע: הפיקדון נשאר אצלכם.",
    manual:
      "את התשלום מאשרים ידנית: כשהכסף מופיע בחשבון הסליקה, פתחו את ההזמנה ולחצו „שולם“. אישור אוטומטי מספק התשלומים לא מחובר.",
    errors: {
      hold: "הזינו בין 15 ל-1440 דקות.",
      refund: "הזינו בין 0 ל-720 שעות.",
    },
  },
  pages: {
    title: "עמודי תשלום",
    description:
      "העמודים שלכם שבהם לקוחות משלמים: Flitt, Stripe Payment Links, TBC, בנק ג׳ורג׳יה או כל ספק עם קישור, בכל מדינה ובכל מטבע.",
    empty: "עדיין אין עמוד תשלום",
    emptyDescription: "הוסיפו את הקישור לעמוד התשלום שלכם. העוזר שולח אותו יחד עם הפיקדון.",
    add: "הוספת העמוד",
    label: "שם",
    labelPlaceholder: "Flitt, פיקדונות לשולחנות",
    kind: "סוג",
    kinds: {
      template: "ממלא את הסכום",
      static: "סכום קבוע אחד",
    },
    kindHints: {
      template: "שימו {amount} במקום שבו בא הסכום ו-{reference} במקום שבו בא קוד התשלום.",
      static: "עמוד שתמיד גובה את אותו סכום: מתאים רק לפיקדון קבוע.",
    },
    address: "קישור",
    addressHint: "https בלבד. קישור שמכיל מפתח נשמר מוצפן ומוצג בלעדיו.",
    sealed: "המפתח מוסתר",
    default: "ברירת מחדל",
    makeDefault: "להגדיר כברירת מחדל",
    defaultHint: "העמוד שהפיקדונות משתמשים בו, אלא אם שולחן, חדר, איש מקצוע או שירות בוחרים עמוד אחר.",
    removeLabel: "הסרת {label}",
    removeTitle: "להסיר את עמוד התשלום הזה?",
    removeDescription: "פיקדונות שכבר נשלחו שומרים על הקישור שלהם. פיקדונות שהוגדרו לעמוד הזה ישתמשו בעמוד ברירת המחדל.",
    added: "עמוד התשלום נוסף",
    removed: "עמוד התשלום הוסר",
    defaultSet: "עמוד ברירת המחדל השתנה",
    errors: {
      label: "הזינו שם.",
      address: "הזינו את הקישור.",
    },
    refusals: {
      linkNotHttps: "הקישור חייב להתחיל ב-https://.",
      linkInvalid: "אי אפשר להשתמש בקישור הזה: בדקו את הכתובת.",
      templateInvalid:
        "עמוד שממלא את הסכום צריך {amount} בקישור, ורק {amount}, {amount_minor}, {currency} ו-{reference} ממולאים.",
      noPaymentLink: "בחרו אחד מעמודי התשלום שלכם שממלא את הסכום.",
      depositsOff: "הפיקדונות כבויים.",
      currencyMismatch: "הפיקדון חייב להיות במטבע של העסק.",
      statusChanged: "הפיקדון הזה השתנה בינתיים: הוא כבר לא ממתין לתשלום.",
    },
  },
  banquet: {
    title: "בקשות לאירועים",
    description: "הפיקדון שבקשה לאירוע מבקשת לפני שהצוות חוזר ללקוח. השאירו כבוי כדי לא לבקש.",
  },
  report: {
    title: "פיקדונות",
    description:
      "30 הימים האחרונים: פיקדונות שהתבקשו ושולמו, הכסף שנגבה, וכמה פעמים אורחים לא הגיעו עם פיקדון ששולם ובלעדיו.",
    requested: "התבקשו",
    paid: "שולמו",
    awaiting: "ממתינים",
    expired: "לא שולמו בזמן",
    collected: "נגבה",
    refundDue: "להחזרה",
    noShowWith: "אי-הגעה עם פיקדון ששולם",
    noShowWithout: "אי-הגעה בלי פיקדון",
    noShowCounts: "{noShows} מתוך {finished} ביקורים",
    notEnoughData: "עדיין אין מספיק נתונים: {finished} מתוך {min} ביקורים שהסתיימו",
    off: "הפיקדונות כבויים. הפעילו אותם בהגדרות ← פיקדונות.",
    openSettings: "הגדרות פיקדונות",
    loading: "טוענים פיקדונות…",
  },
};
