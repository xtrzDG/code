/** `privacyRetention.*` in Hebrew (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { privacyRetentionEn } from "./privacyRetention.en";

export const privacyRetentionHe: Translation<typeof privacyRetentionEn> = {
  title: "כמה זמן נשמרים הנתונים",
  description: "הנתונים של הלקוחות נמחקים אוטומטית כשהתקופות האלה עוברות. הודעת הפרטיות של הצ׳אט שלכם מציינת ללקוחות את אותן תקופות.",
  conversations: {
    label: "שיחות",
    hint: "נספר מההודעה האחרונה של השיחה. אחר כך ההודעות, הערות הצוות, תמלולי השיחות וההקלטות נמחקים; הזמנות ופניות שומרות רק את מה שאינו אישי.",
  },
  modelRecords: {
    label: "רישומים של קריאות ה-AI של העוזר",
    hint: "הטקסט המדויק שנשלח למודל ה-AI, נשמר לבדיקת תשובות. נמחק כאן וביומן האיכות (Langfuse). לכל היותר 30 יום.",
  },
  periods: {
    days: { one: "יום אחד", two: "יומיים", other: "{count} ימים" },
    months: { one: "חודש אחד", two: "חודשיים", other: "{count} חודשים" },
    years: { one: "שנה אחת", two: "שנתיים", other: "{count} שנים" },
    recommended: "{period} (מומלץ)",
    maximum: "{period} (מקסימום)",
  },
  recordings: "הקלטות שיחות נשמרות {period}.",
  changeRecordings: "שינוי בכללי",
  processorsTitle: "עותקים אצל מעבדי המשנה שלנו",
  processors: {
    langfuse: "Langfuse: יומנים של קריאות ה-AI של העוזר",
    elevenlabs: "ElevenLabs: שיחות טלפון (אודיו ותמלול)",
  },
  processorsDeleted: "נמחקים יחד עם שלנו, לפי התקופות האלה וכשאתם מוחקים נתונים של לקוח:",
  processorsNone: "בפלטפורמה הזו לא משתמשים ב-Langfuse וב-ElevenLabs, ולכן הם לא שומרים עותקים של נתוני הלקוחות שלכם.",
  messagingApps: "צ׳אטים ב-WhatsApp, Messenger, Instagram ו-Telegram נשארים באפליקציה של הלקוח: הפלטפורמות האלה מאפשרות רק ללקוח למחוק אותם.",
  lastCleanupTitle: "הניקוי האחרון",
  lastCleanup: "{date}",
  nothingDue: "לא היה מה למחוק.",
  noCleanupYet: "הניקוי הראשון ירוץ הלילה.",
  removed: { one: "רשומה אחת הוסרה", other: "{count} רשומות הוסרו" },
  counts: {
    deleted_messages: "הודעות",
    deleted_llm_turns: "רישומי קריאות AI",
    deleted_notes: "הערות צוות",
    deleted_media: "קבצים של לקוחות",
    deleted_missed_calls: "שיחות שלא נענו",
    erased_calls: "שיחות טלפון",
    anonymized_leads: "פניות",
    anonymized_bookings: "הזמנות",
    anonymized_handoffs: "בקשות",
  },
  shorterTitle: "למחוק הלילה נתונים ישנים יותר?",
  shorterDescription:
    "עם תקופות קצרות יותר, הניקוי של הלילה ימחק לצמיתות כל מה שחורג מהן (שיחות: {conversations}; רישומי קריאות AI: {modelRecords}). אי אפשר לבטל את זה.",
  shorterConfirm: "קיצור ומחיקה",
  qualitySampling: {
    label: "בדיקות איכות של שיחות אמיתיות",
    hint: "בכל לילה מדגם קטן של שיחות שהסתיימו (בלי צ׳אטים של ניסיון) מקבל ציון מאותו ספק AI שכותב את התשובות, כך שתשובות חלשות מופיעות באיכות של העוזר. כבו את זה כדי להשאיר את השיחות של הלקוחות שלכם מחוץ לבדיקות האלה.",
  },
};
