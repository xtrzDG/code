/** `tunnel.*` in Hebrew: the setup tunnel's frame (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { tunnelEn } from "./tunnel.en";

export const tunnelHe: Translation<typeof tunnelEn> = {
  pageTitle: "יצירת עוזר AI",
  newAssistant: "עוזר חדש",
  railLabel: "שלבי ההגדרה",
  steps: {
    business: "העסק שלכם",
    place: "איפה אתם",
    offer: "מה אתם מציעים",
    hours: "שעות והזמנות",
    people: "מי עוזר",
    channels: "איפה הלקוחות כותבים",
    try: "ניסיון",
    launch: "הפעלה",
  },
  stepOf: "שלב {number} מתוך {total}",
  stepState: {
    done: "הושלם",
    skipped: "דולג",
    current: "אתם כאן",
    todo: "עדיין לא",
  },
  announce: "שלב {number} מתוך {total}: {title}",
  announceFinale: "העוזר שלכם באוויר",
  back: "חזרה",
  continue: "המשך",
  skip: "לדלג בינתיים",
  enterHint: "או הקישו Enter",
  exit: "שמירה ויציאה",
  saving: "שומרים…",
  saved: "נשמר",
  saveFailed: "עדיין לא נשמר",
  ownerOnlyTitle: "הבעלים יוצרים את העוזר",
  ownerOnlyText: "רק בעלים של {business} יכולים להגדיר אותו. שיחות, הזמנות ופניות יופיעו בלוח הבקרה ברגע שהוא יעלה לאוויר.",
  openCabinet: "פתיחת לוח הבקרה",
};
