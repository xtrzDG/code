/** `sources.*` in Hebrew (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { sourcesEn } from "./sources.en";

export const sourcesHe: Translation<typeof sourcesEn> = {
  title: "מאיפה הגיעו הלקוחות",
  description: "שיחות, הזמנות והשווי שלהן לפי קישור, קוד QR, מודעה וקו טלפון.",
  periodLabel: "תקופה",
  periods: {
    "7d": "7 ימים",
    "30d": "30 ימים",
    "90d": "90 ימים",
  },
  caption: "לקוחות לפי מקור, {range}",
  columns: {
    source: "מקור",
    conversations: "שיחות",
    bookings: "הזמנות",
    requests: "פניות",
    value: "שווי",
  },
  untagged: "ללא תגית",
  other: { one: "עוד תגית אחת", other: "עוד {count} תגיות" },
  phone: "שיחה ל-{number}",
  ad: "מודעה",
  adWithId: "מודעה {id}",
  total: "סה״כ",
  noValue: "—",
  share: "{percent} מהשיחות",
  empty: {
    title: "אין שיחות בתקופה הזו",
    description: "המקורות מופיעים כשלקוחות כותבים ומתקשרים.",
  },
  tagHint: "תנו לכל קישור ולכל קוד QR תגית משלו בערוצים → שיתוף, והוא יופיע כאן כשורה נפרדת.",
  tagLink: "תיוג הקישורים שלכם",
  loading: "טוענים את המקורות…",
  chip: "מקור: {source}",
};
