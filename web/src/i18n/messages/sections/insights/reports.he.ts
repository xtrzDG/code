/** `reports.*` in Hebrew: Overview → Reports (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { reportsEn } from "./reports.en";

export const reportsHe: Translation<typeof reportsEn> = {
  description: "מה העוזר עשה בכל חודש ושבוע, והסיכומים שאתם מקבלים על כך.",
  loading: "טוענים את הדוחות…",
  opened: "מהסיכום שלכם",
  past: "דוחות קודמים",
  kindLabel: "סוג הדוח",
  kinds: {
    monthly: "חודשי",
    weekly: "שבועי",
    daily: "יומי",
  },
  empty: {
    title: "עדיין אין דוחות",
    monthly: "הדוח החודשי הראשון נוצר ב-1 בחודש, על החודש הקודם.",
    weekly: "סיכומים שבועיים נוצרים בימי שני, על השבוע הקודם.",
    daily: "סיכומים יומיים נוצרים בכל בוקר לבעלים שהפעילו אותם.",
  },
  monthSoFar: {
    title: "החודש עד כה",
    next: "הדוח המלא יגיע ב-{date}",
  },
  summary: {
    bookings: { one: "הזמנה אחת", other: "{count} הזמנות" },
    requests: { one: "פנייה אחת", other: "{count} פניות" },
  },
  delivery: {
    sent: { one: "נשלח לבעלים אחד", other: "נשלח ל-{count} בעלים" },
    quiet: "לא נשלח: תקופה שקטה",
    noRecipients: "לאף אחד זה לא היה מופעל",
  },
  details: {
    toggle: "כל המספרים",
    caption: "המספרים של הדוח מול התקופה הקודמת",
    measure: "מה",
    change: "שינוי",
    before: "לפני: {value}",
    noCheck: "לא נקבע חשבון ממוצע, ולכן אין בדוח הערכה כספית.",
    ownerCheck: "הסכום הוערך לפי החשבון הממוצע שלכם, {money}.",
    typicalCheck: "הסכום הוערך לפי החשבון הטיפוסי לסוג העסק שלכם, {money}.",
    bookedPrices: "הסכום לפי המחירים של מה שהוזמן.",
    mixedCheck: "הסכום לפי המחירים של מה שהוזמן; הזמנות בלי מחיר לפי החשבון הממוצע, {money}.",
  },
  rows: {
    assistantBookings: "הזמנות של העוזר",
    estimate: "שווי (הערכה)",
    staffTime: "זמן צוות שנחסך",
    afterHours: "שיחות אחרי שעות הפעילות",
    conversations: "שיחות",
    customerMessages: "הודעות מלקוחות",
    assistantReplies: "תשובות של העוזר",
    calls: "שיחות טלפון שנענו",
    bookings: "כל ההזמנות",
    requests: "פניות",
    handoffs: "היה צריך אדם",
  },
  duration: {
    hoursMinutes: "{hours} שע׳ {minutes} דק׳",
    minutes: "{minutes} דק׳",
  },
  digests: {
    title: "הסיכומים שלכם",
    description: "מה העוזר עשה, נשלח אליכם בשפה שלכם עם קישור חזרה לכאן.",
    monthly: "דוח חודשי",
    monthlyHint: "ב-1 בחודש ב-9:00, על החודש הקודם",
    weekly: "סיכום שבועי",
    weeklyHint: "בימי שני ב-9:00, על השבוע הקודם",
    daily: "סיכום יומי",
    dailyHint: "בכל בוקר ב-9:00, על היום הקודם",
  },
};
