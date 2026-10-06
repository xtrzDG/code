/** `digestChannels.*` in Hebrew (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { digestChannelsEn } from "./digestChannels.en";

export const digestChannelsHe: Translation<typeof digestChannelsEn> = {
  title: "לאן הם מגיעים",
  email: "דוא״ל",
  emailTo: "אל {email}",
  emailMissing: "אתם מתחברים עם טלפון, ולכן אין כתובת דוא״ל לשלוח אליה.",
  emailNotReady: "דוא״ל עדיין לא מוגדר בפלטפורמה הזו.",
  push: "מכשירים",
  devices: { one: "במכשיר אחד ההתראות פעילות", other: "ב-{count} מכשירים ההתראות פעילות" },
  noDevices: "עדיין אין מכשיר עם התראות פעילות.",
  manageDevices: "הגדרות ההתראות",
  telegram: "Telegram",
  telegramHint: "הדוח המלא, מהבוט של הפלטפורמה.",
  telegramChat: "צ׳אט Telegram",
  telegramNoChats: "קודם קשרו צ׳אט Telegram: ערוצים → התראות לצוות ב-Telegram.",
  openChannels: "פתיחת ערוצים",
  telegramNotReady: "Telegram עדיין לא מוגדר בפלטפורמה הזו.",
  whatsapp: "WhatsApp",
  whatsappHint: "סיכום קצר עם קישור, מהמספר של הפלטפורמה.",
  whatsappNumber: "מספר ה-WhatsApp שלכם",
  whatsappNumberHint: "עם קידומת המדינה. בחירה ב-WhatsApp היא ההסכמה שלכם להודעות האלה.",
  whatsappNotReady: "סיכומים ב-WhatsApp עדיין לא מוגדרים בפלטפורמה הזו.",
  save: "שמירה",
  saved: "נשמר",
  invalidNumber: "הזינו את המספר עם קידומת המדינה, למשל ‎+972 50 123 4567.",
  refusals: {
    telegramNotAvailable: "סיכומים ב-Telegram עדיין לא מוגדרים בפלטפורמה הזו.",
    telegramChatNotLinked: "הצ׳אט הזה כבר לא מקושר לעסק. בחרו אחר או קשרו אותו מחדש.",
    whatsappNotAvailable: "סיכומים ב-WhatsApp עדיין לא מוגדרים בפלטפורמה הזו.",
    whatsappNumberMissing: "הזינו את מספר ה-WhatsApp שאליו הסיכומים נשלחים.",
  },
};
