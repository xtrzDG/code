/** `referrals.*` in Hebrew: inviting a business (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { referralsEn } from "./referrals.en";

export const referralsHe: Translation<typeof referralsEn> = {
  title: "הזמינו עסק — חודש חינם",
  lead: "שתפו את הקישור שלכם עם עסק שאתם מכירים. כשהוא ישלם את החשבונית הראשונה שלו, שניכם תקבלו חודש של המסלולים שלכם חינם.",
  terms: "החודש מגיע כזיכוי בחשבוניות הבאות שלכם. עסקים אחרים שלכם לא נחשבים.",
  menu: "הזמנת עסק",
  menuHint: "חודש חינם לשניכם",
  linkLabel: "קישור ההזמנה שלכם",
  copy: "העתקת הקישור",
  share: "שיתוף",
  shareText: "אנחנו עונים ללקוחות שלנו עם {app}. הירשמו דרך הקישור שלי ושנינו נקבל חודש חינם:",
  showQr: "הצגת קוד QR",
  hideQr: "הסתרת קוד ה-QR",
  qrLabel: "קוד QR של קישור ההזמנה שלכם",
  noLink: "קישור ההזמנה שלכם עדיין לא מוכן. נסו שוב מאוחר יותר.",
  loading: "טוענים את ההזמנה שלכם…",
  statsLabel: "ההזמנות שלכם",
  invited: "נרשמו",
  paid: "שילמו",
  rewarded: "חודשים שהרווחתם",
  close: "סגירה",
  poweredBy: {
    title: "קישור „מופעל על ידי”",
    description: "קישור קטן עם קוד ההזמנה שלכם מתחת לצ׳אט, בעמוד הצ׳אט ובכרטיס המודפס.",
    toggle: "הצגת הקישור „מופעל על ידי”",
    plusOnly: "הסרתו היא חלק ממסלול Plus.",
    hidden: "כבוי: הצ׳אט, העמוד והכרטיס לא מציגים קישור.",
    saved: "נשמר",
    footer: "מופעל על ידי {app}",
  },
  partnerPortal: "פורטל השותפים",
};
