/** `publicDemo.*` in Hebrew: the public demo chat (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { publicDemoEn } from "./publicDemo.en";

export const publicDemoHe: Translation<typeof publicDemoEn> = {
  label: "הדגמה חיה של העוזר",
  badge: "הדגמה חיה",
  sampleBadge: "דוגמה",
  sandbox: "סביבת ניסיון: שום דבר לא מוזמן באמת",
  pick: "סוג העסק",
  place: "{niche} · {city}",
  greeting: "שלום! אני עוזר ה-AI של {business}. שאלו אותי מה שהלקוחות שלכם היו שואלים: מחירים, שעות פתיחה, הזמנה.",
  starters: "נסו לשאול",
  genericStarters: {
    hours: "מה שעות הפתיחה שלכם?",
    prices: "כמה זה עולה?",
    place: "איפה אתם נמצאים?",
  },
  inputLabel: "ההודעה שלכם לעוזר ההדגמה",
  placeholder: "כתבו כמו שלקוח היה כותב…",
  send: "שליחה",
  typing: "העוזר מקליד…",
  restart: "להתחיל מחדש",
  you: "אתם",
  assistant: "עוזר",
  outcomes: {
    booking: "כאן הייתה נוצרת הזמנה",
    request: "כאן הפנייה הייתה עוברת למנהל שלכם",
    handoff: "כאן השיחה הייתה עוברת לאדם",
  },
  messagesLeft: {
    one: "נשארה הודעה אחת בשעה הזו",
    other: "נשארו {count} הודעות בשעה הזו",
  },
  failures: {
    limit: "ההדגמה קיבלה הרבה הודעות. נסו שוב מעט מאוחר יותר, או צרו עוזר משלכם: זה לוקח כעשר דקות.",
    unavailable: "ההדגמה הזו נחה כרגע. נסו סוג עסק אחר.",
    offline: "אין חיבור. בדקו את האינטרנט ונסו שוב.",
    failed: "ההודעה לא נשלחה. נסו שוב.",
  },
  privacy: "הדגמה ציבורית: אנא אל תשתפו פרטים אישיים.",
  cta: "ליצור עוזר משלי",
};
