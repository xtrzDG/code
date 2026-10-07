/** `insightsCommon.*` in Hebrew (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { insightsCommonEn } from "./common.en";

export const insightsCommonHe: Translation<typeof insightsCommonEn> = {
  loadingMore: "טוענים…",
  showMore: "להציג עוד",
  includeTest: "לכלול פעילות ניסיון",
  includeTestHint: "מצ׳אט הניסיון ומהבדיקות",
  testBadge: "ניסיון",
  afterHours: "אחרי שעות הפעילות",
  unknownCustomer: "לקוח ללא שם",
  callPhone: "חיוג ל-{phone}",
  openConversation: "פתיחת השיחה",
  noMatchesTitle: "שום דבר לא מתאים למסננים",
  noMatchesDescription: "שנו או נקו את המסננים כדי לראות עוד.",
  copy: "העתקה",
  copied: "הועתק ללוח",
  copyFailed: "לא הצלחנו להעתיק. סמנו את הטקסט והעתיקו ידנית.",
  customerMessage: {
    title: "הודעה ללקוח",
    description: "כאן העוזר לא שולח את הטקסט הזה בעצמו. שלחו אותו ללקוח בערוץ שבו אתם מדברים.",
  },
  channels: {
    phone: "טלפון",
    whatsapp: "WhatsApp",
    instagram: "Instagram",
    messenger: "Messenger",
    telegram: "Telegram",
    web_chat: "צ׳אט באתר",
    viber: "Viber",
    owner_test: "צ׳אט ניסיון",
  },
};
