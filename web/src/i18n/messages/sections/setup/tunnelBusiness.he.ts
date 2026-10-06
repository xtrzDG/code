/** `tunnelBusiness.*` in Hebrew: the tunnel's first two steps (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { tunnelBusinessEn } from "./tunnelBusiness.en";

export const tunnelBusinessHe: Translation<typeof tunnelBusinessEn> = {
  business: {
    title: "איך נקרא העסק שלכם?",
    text: "ניצור עוזר שעונה ללקוחות שלכם במקומכם, יומם ולילה.",
    name: "שם העסק",
    namePlaceholder: "למשל, סלון שחר",
    kindTitle: "במה אתם עוסקים?",
    kindHint: "בחרו את האפשרות הקרובה ביותר. היא קובעת מה העוזר שואל, מזמין ויודע.",
    kindFixed: "בחרתם בזה כשהעוזר נוצר; אי אפשר לשנות את זה.",
    legalReview: "עסקים מהסוג הזה עוברים בדיקה משפטית קצרה לפני שהעוזר עולה לאוויר.",
    detailsTitle: "עוד דבר אחד שלקוחות תמיד שואלים",
    errors: {
      name: "כתבו את שם העסק.",
      kind: "בחרו במה העסק שלכם עוסק.",
    },
  },
  place: {
    title: "איפה אתם?",
    text: "המדינה קובעת את המטבע, את אזור הזמן ואת השפות של הלקוחות. מילאנו את מה שיכולנו.",
    country: "מדינה",
    countryHint: "מחירים ב-{currency}",
    countryFixed: "אי אפשר לשנות את המדינה אחרי שהעוזר נוצר.",
    city: "עיר",
    cityPlaceholder: "למשל, תל אביב",
    address: "כתובת",
    addressPlaceholder: "רחוב ומספר",
    addressHint: "העוזר מסביר ללקוחות איך למצוא אתכם.",
    addressOptional: "לא חובה",
    languages: "השפות שבהן הלקוחות שלכם כותבים",
    languagesHint: "העוזר עונה לכל לקוח בשפה שלו, מבין השפות האלה.",
    defaultLanguage: "הברכה הראשונה ב",
    timezone: "אזור זמן",
    creating: "יוצרים את העוזר שלכם…",
    errors: {
      country: "בחרו את המדינה שלכם.",
      languages: "בחרו לפחות שפה אחת.",
      address: "כתבו את הכתובת: הלקוחות צריכים אותה כדי למצוא אתכם.",
      restricted: "עדיין אי אפשר ליצור עסקים מהמדינה הזו.",
    },
  },
};
