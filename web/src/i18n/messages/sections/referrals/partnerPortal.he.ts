/** `partnerPortal.*` in Hebrew (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { partnerPortalEn } from "./partnerPortal.en";

export const partnerPortalHe: Translation<typeof partnerPortalEn> = {
  title: "פורטל השותפים",
  description: "הקישורים שלכם, העסקים שהם הביאו ומה הרווחתם.",
  rate: "העמלה שלכם: {rate} מכל חשבונית שהעסקים האלה משלמים, לפני מס.",
  paused: "השותפות שלכם מושהית: תשלומים חדשים לא מזכים בעמלה עד שצוות הפלטפורמה יחדש אותה.",
  legal: "החוזה שלכם והדרך שבה התשלומים מגיעים אליכם מוסכמים עם צוות הפלטפורמה.",
  links: {
    title: "הקישורים שלכם",
    description: "צרו קישור לכל מקום שבו אתם משתפים אותו: התגית מראה מאיפה הגיעו ההרשמות.",
    none: "עדיין אין לכם קודים: צוות הפלטפורמה מוסיף אותם.",
    source: "איפה אתם משתפים אותו",
    sourcePlaceholder: "Instagram",
    sourceHint: "לא חובה. אותיות לטיניות, ספרות, נקודות, מקפים וקווים תחתונים.",
    sourceInvalid: "השתמשו רק באותיות לטיניות, ספרות, נקודות, מקפים וקווים תחתונים.",
    code: "קוד",
    qrLabel: "קוד QR של הקישור עם {code}",
    showQr: "קוד QR",
    hideQr: "הסתרת קוד ה-QR",
  },
  totals: {
    title: "עמלות",
    businesses: "עסקים שהבאתם",
    paying: "כבר שילמו",
    accrued: "לתשלום",
    paid: "שולם",
  },
  businesses: {
    title: "עסקים שהבאתם",
    empty: "עדיין אין עסקים. שתפו את הקישור שלכם כדי להביא את הראשון.",
    signedUp: "נרשם",
    firstPaid: "תשלום ראשון",
    notYet: "עדיין לא",
    unnamed: "עסק",
  },
  commissions: {
    title: "עמלה לפי חשבונית",
    empty: "עדיין אין עמלות: הן מופיעות כשעסק שהבאתם משלם.",
    base: "חשבונית לפני מס",
    status: "סטטוס",
    statuses: {
      accrued: "לתשלום",
      paid: "שולם",
    },
  },
  showMore: "להציג עוד",
  loading: "טוענים…",
};
