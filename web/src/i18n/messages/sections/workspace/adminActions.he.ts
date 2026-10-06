/** `adminActions.*` in Hebrew (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { adminActionsEn } from "./adminActions.en";

export const adminActionsHe: Translation<typeof adminActionsEn> = {
  menu: "פעולות בחשבון",
  reasonLabel: "למה",
  reasonHint: "יומן הפעולות של הלקוח שומר את זה, עם השם שלכם.",
  reasonShort: "כתבו למה, לפחות 8 תווים.",
  done: "נשמר בחשבון של הלקוח",
  autoDebitNote:
    "הלקוח הזה משלם אוטומטית: הכרטיס ממשיך להיות מחויב בסכום שסוכם בתשלום. הנחות וזיכויים חלים על חשבונות שמשולמים בלוח הבקרה או בהעברה בנקאית.",
  extend: {
    action: "הארכת תקופת הניסיון",
    title: "הארכת תקופת הניסיון של {name}",
    description:
      "תקופת ניסיון פעילה מסתיימת מאוחר יותר; תקופת ניסיון שהסתיימה בלי תשלום מתחילה מחדש מהיום, החשבונות שלה מבוטלים והשירות המלא חוזר.",
    days: "ימים נוספים",
    daysHint: "מ-1 עד 60 ימים.",
    daysInvalid: "הזינו מספר שלם של ימים מ-1 עד 60.",
    confirm: "הארכה",
  },
  discount: {
    action: "מתן הנחה",
    title: "הנחה עבור {name}",
    description: "תקופות שמתחילות עד היום האחרון כולל מחויבות בהנחה הזו מהמחיר, לפני מס. הנחה חדשה מחליפה את הנוכחית.",
    percent: "הנחה, %",
    percentInvalid: "הזינו אחוז שלם מ-1 עד 100.",
    lastDay: "היום האחרון",
    lastDayHint: "לפי אזור הזמן של הלקוח; לכל היותר שלוש שנים קדימה.",
    lastDayInvalid: "בחרו יום מהיום והלאה.",
    confirm: "מתן ההנחה",
  },
  credit: {
    action: "מתן זיכוי",
    title: "זיכוי עבור {name}",
    description: "הזיכוי יורד ממחיר החשבונות הבאים לפני מס עד שהוא מנוצל. חשבון מבוטל מחזיר את הזיכוי שלו.",
    amount: "סכום, {currency}",
    amountInvalid: "הזינו סכום גדול מאפס (לכל היותר שתי ספרות אחרי הנקודה).",
    confirm: "מתן הזיכוי",
  },
  waive: {
    action: "ויתור על דמי ההקמה",
    title: "לוותר על דמי ההקמה של {name}?",
    description: "חשבון דמי ההקמה שלא שולם מבוטל, ודמי הקמה לא יחויבו שוב. דמי הקמה ששולמו כבר מוחזרים דרך ספק התשלומים, לא כאן.",
    confirm: "ויתור על הדמים",
  },
  payment: {
    action: "רישום תשלום",
    title: "רישום תשלום מ-{name}",
    description: "כסף שהגיע מחוץ לתשלום בכרטיס משלם עכשיו חשבון פתוח. תקופה ששולמה מחזירה את השירות המלא, כמו תשלום בכרטיס.",
    invoice: "חשבון",
    noOpenInvoices: "ללקוח אין חשבונות פתוחים.",
    method: "איך זה הגיע",
    methods: {
      bank_transfer: "העברה בנקאית",
      cash: "מזומן",
    },
    reference: "אסמכתה",
    referenceHint: "האסמכתה מדף הבנק או מספר קבלת המזומן.",
    referenceInvalid: "הזינו את האסמכתה (עד 120 תווים).",
    confirm: "סימון כמשולם",
  },
  plan: {
    action: "שינוי המסלול",
    title: "שינוי המסלול של {name}",
    description:
      "החשבון הבא משתמש במחיר ממחירון, בלי תהליך תשלום. אם מה שמחויב משתנה, התשלומים האוטומטיים נעצרים וחשבונות שלא שולמו במחיר הישן מבוטלים; מסלול בלי קול מכבה את הסוכן הקולי.",
    plan: "מסלול",
    period: "חיוב",
    confirm: "שינוי המסלול",
  },
  account: {
    title: "ניתן ללקוח",
    description: "מה שצוות הפלטפורמה נתן לחשבון הזה: תקופת ניסיון, הנחה, זיכוי ודמי הקמה.",
    trialEnds: "תקופת הניסיון מסתיימת",
    noTrial: "אין תקופת ניסיון פעילה",
    discount: "הנחה",
    discountActive: "{percent} הנחה על תקופות שמתחילות עד {date}",
    discountEnded: "{percent}, הסתיימה {date}",
    noDiscount: "אין",
    credit: "זיכוי שנותר",
    setupFee: "דמי הקמה",
    setupFeeWaived: "בוטלו",
    setupFeeCharged: "מחויבים כשהם חלים",
    noSubscription: "ללקוח עדיין אין מינוי: פעולות החשבון ממתינות למינוי.",
  },
  onboarding: {
    title: "התבקשה הגדרה שנעשית בשביל הלקוח",
    description: "ב-{date} הבעלים ביקשו מצוות הפלטפורמה להגדיר את העסק ({plan}).",
    markDone: "סימון כהושלם",
    marked: "ההגדרה שנעשתה בשביל הלקוח סומנה כהושלמה",
    doneTitle: "ההגדרה שנעשתה בשביל הלקוח הסתיימה",
  },
};
