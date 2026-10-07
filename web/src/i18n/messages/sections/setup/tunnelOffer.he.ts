/** `tunnelOffer.*` in Hebrew: the offer, hours and bookings steps (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { tunnelOfferEn } from "./tunnelOffer.en";

export const tunnelOfferHe: Translation<typeof tunnelOfferEn> = {
  offer: {
    title: "מה אתם מציעים?",
    text: "הוסיפו את מה שאתם מוכרים עם מחירים. העוזר מציין מחירים רק של מה שמופיע כאן.",
    sourcesLabel: "איך להוסיף",
    sources: {
      type: "להקליד",
      website: "מהאתר שלכם",
      menu: "מתמונה או קובץ של תפריט",
    },
    tableLabel: "ההצעה שלכם",
    name: "שם",
    namePlaceholder: "מה לקוחות יכולים להזמין או לקבוע",
    price: "מחיר, {currency}",
    pricePlaceholder: "0",
    suggestion: "דוגמה",
    suggestionsHint: "דוגמאות נשמרות רק אחרי שתתנו להן מחיר. הסירו את אלה שאתם לא מציעים.",
    addRow: "הוספת שורה",
    removeRow: "הסרת {name}",
    removeEmpty: "הסרת השורה הזו",
    rowMenu: "עוד עבור {name}",
    rowSaving: "שומרים…",
    rowSaved: "נשמר",
    rowFailed: "לא נשמר",
    priced: {
      one: "פריט אחד עם מחיר",
      other: "{count} פריטים עם מחיר",
    },
    importedTitle: {
      one: "פריט אחד נוסף מהייבוא שלכם",
      other: "{count} פריטים נוספו מהייבוא שלכם",
    },
    importHint: "אנחנו קוראים אותו ומראים לכם מה מצאנו. שום דבר לא נשמר לפני שתבדקו.",
  },
  hours: {
    title: "מתי אתם פתוחים?",
    text: "הצענו את השעות המקובלות בסוג העסק שלכם. שנו כל מה שאצלכם שונה.",
    hoursLabel: "שעות פתיחה",
    bookingsTitle: "איך עובדות הזמנות?",
    slot: "ביקור נמשך",
    partySize: "מקסימום אנשים בהזמנה אחת",
    notice: "להזמין לפחות",
    noticeNone: "לא צריך התראה מראש",
    cancellation: "מדיניות ביטול",
    cancellationHint: "הלקוחות שומעים אותה כשהם מזמינים או מבטלים.",
    resourceTitle: "מה הלקוחות מזמינים",
    resourceHint: "אפשר להוסיף עוד אחר כך בעוזר → ידע.",
    resourceName: "שם",
    resourceCount: "כמה",
    resourceCapacity: "אנשים בכל אחד",
    minutes: {
      one: "דקה אחת",
      two: "שתי דקות",
      other: "{count} דקות",
    },
    hoursCount: {
      one: "שעה אחת",
      two: "שעתיים",
      other: "{count} שעות",
    },
    noticeHours: {
      one: "שעה מראש",
      two: "שעתיים מראש",
      other: "{count} שעות מראש",
    },
    noticeDays: {
      one: "יום מראש",
      two: "יומיים מראש",
      other: "{count} ימים מראש",
    },
    noticeMinutes: {
      one: "דקה מראש",
      two: "שתי דקות מראש",
      other: "{count} דקות מראש",
    },
    errors: {
      noHours: "פתחו לפחות יום אחד.",
      partySize: "כתבו מספר שלם מ-1 ומעלה.",
      resourceName: "תנו שם למה שהלקוחות מזמינים.",
      capacity: "כתבו מספר שלם מ-1 ומעלה.",
      unitCount: "כתבו מספר שלם מ-1 ומעלה.",
    },
  },
};
