/** `phoneNumbers.*` texts of a phone number rented from the platform, in Hebrew. */

import type { Translation } from "../../../translate";
import type { phoneNumbersEn } from "./phoneNumbers.en";

export const phoneNumbersHe: Translation<typeof phoneNumbersEn> = {
  panel: {
    noNumber: "אין עדיין מספר טלפון לשיחות? קחו אחד מאיתנו: העוזר שלכם עונה בו מיד.",
    getNumber: "קבלת מספר",
    rentedTitle: "המספר שלכם מאיתנו",
    monthly: "{price} לחודש",
    answering: "העוזר שלכם עונה בו",
    connecting: "מחברים לעוזר שלכם…",
    waitsForPublish: "עדיין לא עונה: פרסמו את העוזר עם שיחות טלפון מופעלות, והוא יענה במספר הזה.",
    releasing: "מוחזר לספק",
    giveBackHint: "כדי להחזיר את המספר, נתקו את ערוץ הטלפון. החיוב עליו ייפסק והמספר יחזור לספק.",
    requestTitle: "המספר התבקש",
    requestText: "מספר ({type}) במדינה {country}. הצוות שלנו ידאג לו ויכתוב לכם; זה עשוי לקחת כמה ימי עבודה.",
    requestTextCity: "מספר ({type}) במדינה {country}, ליד {city}. הצוות שלנו ידאג לו ויכתוב לכם; זה עשוי לקחת כמה ימי עבודה.",
    cancelRequest: "ביטול הבקשה",
    requestCancelled: "הבקשה בוטלה",
    ownerOnly: "רק בעלים יכולים לקחת מספר.",
    loading: "טוענים את המספר שלכם…",
    disconnectReleases: "בניתוק, המספר {number} יחזור לספק לצמיתות: החיוב עליו ייפסק, וייתכן שלא תוכלו לקבל שוב את אותו מספר.",
  },
  tunnel: {
    title: "שיחות טלפון",
    text: "קחו מאיתנו מספר והעוזר יענה לשיחות בו בשפת הלקוחות שלכם. אפשר לעשות זאת גם מאוחר יותר בעמוד הערוצים.",
  },
  dialog: {
    title: "קבלת מספר טלפון",
    description: "מספר במדינה שתבחרו, בחיוב חודשי יחד עם המסלול שלכם.",
    country: "מדינה",
    countriesNow: "זמין עכשיו",
    countriesTeam: "הצוות שלנו מסדר",
    type: "סוג המספר",
    city: "עיר או אזור",
    cityHint: "לא חובה: נחפש מספרים בקרבת מקום.",
    search: "חיפוש מספרים",
    searching: "מחפשים מספרים…",
    close: "סגירה",
  },
  types: {
    local: "מקומי",
    mobile: "נייד",
    toll_free: "חיוג חינם",
  },
  typeOptions: {
    local: "מקומי (קו עירוני)",
    mobile: "נייד",
    toll_free: "חיוג חינם",
  },
  offers: {
    title: "מספרים שאפשר לקחת עכשיו",
    price: "{price} לחודש לכל אחד מהם",
    none: "אין כרגע מספרים פנויים מהסוג הזה שם. נסו בלי עיר, סוג אחר, או פנו לצוות שלנו.",
    take: "לקחת",
    takeLabel: "לקחת את {number}",
  },
  confirm: {
    title: "לקחת את {number}?",
    price: "העלות היא {price} לחודש, בחיוב עם המסלול שלכם החל מהיום.",
    channel: "הוא יהפוך לערוץ הטלפון שלכם, והעוזר שלכם יענה בו.",
    giveBack: "אפשר להחזיר אותו בכל עת על ידי ניתוק ערוץ הטלפון.",
    take: "לקחת את המספר",
    back: "חזרה לרשימה",
    done: "{number} שלכם",
  },
  request: {
    requires_documents: "במדינה זו הרגולטור מבקש את מסמכי העסק לפני הנפקת מספר. הצוות שלנו יסדר זאת יחד איתכם.",
    on_request: "מספרים מהסוג הזה כאן הצוות שלנו מסדר ידנית.",
    ask: "פנייה לצוות שלנו",
    sent: "הבקשה נשלחה: הצוות שלנו יכתוב לכם",
  },
  refusals: {
    numberTaken: "מישהו לקח את המספר הזה זה עתה. חפשו שוב ובחרו מספר אחר.",
    priceChanged: "המחיר של סוג המספר הזה השתנה. חפשו שוב כדי לראות את המחיר החדש.",
  },
};
