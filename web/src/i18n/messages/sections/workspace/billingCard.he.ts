/** `billingCard.*` texts of Settings → Billing: the card on file, the retries of a declined payment and the trial's "Save card" prompt, in Hebrew. */

import type { Translation } from "../../../translate";
import type { billingCardEn } from "./billingCard.en";

export const billingCardHe: Translation<typeof billingCardEn> = {
  title: "כרטיס לתשלום",
  description: "התשלומים האוטומטיים של המינוי מחויבים בכרטיס הזה.",
  endingIn: "כרטיס שמסתיים בספרות {digits}",
  expires: "בתוקף עד {date}",
  noExpiry: "תוקף הכרטיס לא דווח",
  expiryStates: {
    expired: "פג תוקף",
    expiring: "התוקף פג בקרוב",
  },
  facts: {
    provider: "שירות התשלומים",
    savedAt: "נשמר בתאריך",
  },
  noCard: "עדיין לא נשמר כרטיס",
  noCardTrial: "שמרו כרטיס והמינוי ימשיך מעצמו כשתקופת הניסיון תסתיים.",
  noCardPaid: "שמרו כרטיס כדי שהתשלומים הבאים יעברו מעצמם.",
  cardWithoutDetails: "כרטיס שמור אצל {provider}. הפרטים שלו יופיעו כאן אחרי התשלום הבא.",
  expiredHint: "תוקף הכרטיס הזה פג. שמרו כרטיס חדש לפני התשלום הבא.",
  expiringHint: "תוקף הכרטיס הזה פג בקרוב. שמרו כרטיס חדש כדי שהתשלום הבא יעבור.",
  noCharge: "שמירת כרטיס לא מחייבת דבר: שירות התשלומים רק בודק אותו.",
  payToSave: "תשלום החשבון הפתוח שומר את הכרטיס שבו אתם משלמים.",
  save: "שמירת כרטיס",
  update: "עדכון כרטיס",
  opening: "פותחים…",
  retry: {
    title: "התשלום האוטומטי לא עבר",
    declined: "הכרטיס סירב לחיוב. ננסה שוב בעצמנו.",
    outcomes: {
      claimed: "ניסיון {attempt} מתוך {total} מתבצע.",
      approved: "ניסיון {attempt} מתוך {total} עבר. התשלום בתהליך אישור.",
      declined: "ניסיון {attempt} מתוך {total} נדחה.",
      processing: "ניסיון {attempt} מתוך {total} בעיבוד.",
      failed: "ניסיון {attempt} מתוך {total} לא הגיע לשירות התשלומים.",
      not_possible: "ניסיון {attempt} מתוך {total} לא התאפשר: אין כרטיס שמור לחיוב.",
      skipped: "ניסיון {attempt} מתוך {total} דולג.",
    },
    next: "הניסיון הבא: {date}",
    noMore: "לא יהיו ניסיונות נוספים. מ-{date} העוזר רק מקבל פניות.",
  },
  trialPrompt: {
    title: { one: "נותר יום אחד לתקופת הניסיון", two: "נותרו יומיים לתקופת הניסיון", other: "נותרו {count} ימים לתקופת הניסיון" },
    body: "עד {date} לא מחויב דבר: שמרו כרטיס עכשיו והעוזר ימשיך לענות אחרי תקופת הניסיון.",
  },
  returned: {
    title: "שומרים את הכרטיס",
    pending: "הכרטיס יופיע כאן ברגע ששירות התשלומים יאשר אותו, בדרך כלל תוך דקה.",
    savedTitle: "הכרטיס נשמר",
    saved: "מעכשיו התשלומים האוטומטיים מחויבים בכרטיס הזה.",
  },
  errors: {
    cannotSave: "אי אפשר לשמור כרטיס כרגע. שלמו את החשבון הפתוח: זה שומר את הכרטיס שבו אתם משלמים.",
  },
};
