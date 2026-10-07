/** `knowledgeOffer.*` in Hebrew: services, rooms and seasonal rates (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { knowledgeOfferEn } from "./knowledgeOffer.en";

export const knowledgeOfferHe: Translation<typeof knowledgeOfferEn> = {
  offer: {
    nightlyPrice: "מחיר ללילה, {currency}",
    nightlyPriceHint: "לילות מחוץ לכל עונה עולים כך. השאירו ריק אם זה תלוי במשהו.",
    durationHint: "5 עד 720 דקות: כמה זמן נמשכת הזמנה.",
    buffer: "הפסקה אחרי, בדקות",
    bufferHint: "מי שמבצע את השירות נשאר תפוס עוד זמן זה אחריו (ניקיון, הכנה).",
    performers: "מי מבצע",
    performersHint: "רק הם מוצעים לשירות הזה. אף אחד לא סומן: כל מי שלא קשור לשירות מסוים יכול לבצע אותו.",
    rooms: "חדרים מהסוג הזה",
    roomsHint: "שהייה מהסוג הזה מוזמנת באחד מהחדרים האלה. אף אחד לא סומן: כל חדר שמוזמן ללילה.",
    noResources: "עדיין אין את מי לבחור: הוסיפו קודם את האנשים או המקומות שמוזמנים לפי זמן.",
    noRooms: "עדיין אין חדרים שמוזמנים ללילה: הוסיפו אותם קודם.",
    toResources: "פתיחת משאבים ושעות",
    resourceOff: "כבוי",
    filter: "חיפוש לפי שם",
    noMatches: "אף אחד לא מתאים ל„{query}”",
    selectedCount: { one: "אחד נבחר", other: "{count} נבחרו" },
    seasons: "מחירים עונתיים",
    seasonsHint: "לילה בתוך עונה עולה לפי המחיר שלה, כל שנה. עונה יכולה לעבור את השנה החדשה; עונות לא יכולות לחפוף.",
    addSeason: "הוספת עונה",
    seasonTitle: "עונה {number}",
    seasonName: "שם",
    seasonNamePlaceholder: "למשל: קיץ",
    from: "מ",
    to: "עד",
    day: "יום",
    month: "חודש",
    seasonRate: "ללילה, {currency}",
    removeSeason: "הסרת עונה {number}",
    noSeasons: "אין עונות: כל לילה עולה לפי המחיר ללילה.",
    performedBy: "עם {names}",
    roomsList: "חדרים: {names}",
    breakValue: "+{count} דק׳ הפסקה",
    perNight: "{price} ללילה",
    seasonsValue: { one: "עונה אחת", two: "שתי עונות", other: "{count} עונות" },
    errors: {
      bufferRange: "0 עד 240 דקות",
      seasonDate: "אין יום כזה בחודש הזה",
      seasonOverlap: "לעונות {first} ו-{second} יש ימים משותפים: ללילה חייב להיות מחיר אחד.",
      tooManySeasons: { one: "לכל היותר עונה אחת", other: "לכל היותר {count} עונות" },
    },
  },
};
