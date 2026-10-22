/** `metaConnect.*` in Hebrew (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { metaConnectEn } from "./metaConnect.en";

export const metaConnectHe: Translation<typeof metaConnectEn> = {
  continue: "המשך עם Facebook",
  intro: {
    whatsapp:
      "התחברו עם Facebook, ובחלון שלו בחרו או צרו חשבון WhatsApp Business ומספר. את המספר נחבר בעצמנו.",
    instagram: "התחברו עם Facebook ובחרו את הדף שחשבון ה-Instagram המקצועי שלכם מקושר אליו. את השאר נעשה אנחנו.",
    messenger: "התחברו עם Facebook ובחרו את הדף שהעוזר יענה בצ'אטים של ה-Messenger שלו.",
  },
  orManual: "כבר יש לכם את המזהים והמפתח? עדיין אפשר להזין אותם ידנית.",
  preparing: "מכינים את Facebook…",
  starting: "מתחילים…",
  openWindow: "פתיחת החלון של Facebook",
  openHint: "הדפדפן מבקש לחכות ללחיצה: ההתחברות ל-Facebook תיפתח בחלון חדש.",
  waiting: "סיימו בחלון של Facebook. החלון הזה ימתין.",
  finishing: "מתחברים…",
  notices: {
    cancelled: "החלון של Facebook נסגר לפני הסוף. נסו שוב כשתהיו מוכנים.",
    failed: "Facebook לא הצליח לסיים את החיבור. נסו שוב או הזינו את הפרטים ידנית.",
    unavailable: "ההתחברות עם Facebook לא נטענה (ייתכן שחוסם פרסומות עוצר אותה). נסו מאוחר יותר או הזינו את הפרטים ידנית.",
  },
  pages: {
    title: "בחירת דף",
    hint: "הדפים שאתם מנהלים ב-Facebook.",
    instagramHint: "אפשר לחבר Instagram רק דרך דף שמקושר אליו חשבון Instagram מקצועי.",
    none: "Facebook לא הציג אף דף שאתם מנהלים. התחילו מחדש וסמנו את דף העסק בחלון של Facebook.",
    instagram: "Instagram: @{username}",
    instagramNoName: "Instagram מקושר",
    noInstagram: "אין Instagram מקושר",
    connect: "חיבור הדף הזה",
    connecting: "מתחברים…",
  },
  refusals: {
    meta_link_expired: "ההתחברות הזו עם Facebook הסתיימה. התחילו מחדש.",
    meta_not_configured: "ההתחברות עם Facebook לא הוגדרה בשרת הזה. הזינו את הפרטים ידנית.",
    meta_permission_missing: "Facebook לא נתן את כל ההרשאות הדרושות. התחילו מחדש והשאירו את כל התיבות מסומנות.",
    whatsapp_account_missing: "לא חזר מ-Facebook חשבון WhatsApp Business. התחילו מחדש ובחרו או צרו חשבון.",
    whatsapp_number_missing: "לחשבון ה-WhatsApp Business הזה עדיין אין מספר טלפון. הוסיפו מספר בחלון של Facebook.",
    whatsapp_pin_mismatch: "במספר הזה מופעל אימות דו-שלבי עם קוד PIN אחר. כבו אותו ב-WhatsApp Manager ונסו שוב.",
    meta_page_not_found: "Facebook לא נתן גישה לדף הזה. התחילו מחדש וסמנו אותו בחלון של Facebook.",
    instagram_account_missing:
      "לדף הזה לא מקושר חשבון Instagram מקצועי. קשרו חשבון בהגדרות של Instagram או בחרו דף אחר.",
  },
  commentReplies: {
    title: "תשובות לתגובות",
    toggle: "מענה ב-Direct לתגובות עם מילת מפתח",
    description:
      "כשמישהו כותב אחת ממילות המפתח שלכם בתגובה מתחת לפוסט, העוזר שולח לו הודעה אחת ב-Direct. לכל היותר אחת ביום לכל אדם ו-60 בשעה.",
    unavailable: "התשובות לתגובות יתחילו לפעול בעדכון הבא של השירות. עד אז ההגדרות נשמרות.",
    summaryOn: "פעיל, למילים: {keywords}",
    summaryOff: "כבוי",
    keywords: "מילות מפתח",
    keywordsHint: "מילה או ביטוי קצר; לחצו Enter אחרי כל אחד. עד 20.",
    keywordInput: "מילת מפתח חדשה",
    addKeyword: "הוספה",
    removeKeyword: "הסרת „{keyword}”",
    replyText: "הודעה ב-Direct",
    replyHint: "עד 1000 תווים. הלקוח יכול להשיב, והעוזר ימשיך את השיחה.",
    save: "שמירה",
    saving: "שומרים…",
    savedToast: "התשובות לתגובות נשמרו",
    errors: {
      keywordsMissing: "הוסיפו לפחות מילת מפתח אחת",
      replyMissing: "כתבו את ההודעה",
      keyword: "עד 50 תווים, בשורה אחת",
      tooMany: "עד 20 מילות מפתח",
    },
  },
  tunnel: {
    title: "WhatsApp, Instagram ו-Messenger",
    text: "חברו אותם עם חשבון ה-Facebook שלכם עכשיו, או מאוחר יותר בדף הערוצים.",
    connect: "חיבור {channel}",
    connected: "מחובר",
  },
};
