/** `palette.*` in Hebrew: the command palette (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { paletteEn } from "./palette.en";

export const paletteHe: Translation<typeof paletteEn> = {
  title: "חיפוש ומעבר",
  open: "חיפוש",
  openTitle: "חיפוש (Ctrl+K או ⌘K)",
  placeholder: "מצאו לקוח, שיחה, הזמנה או עמוד",
  groups: {
    navigation: "מעבר אל",
    customers: "לקוחות",
    conversations: "שיחות",
    bookings: "הזמנות",
  },
  searching: "מחפשים…",
  noResults: "לא נמצא דבר עבור „{text}”.",
  resultCount: { one: "תוצאה אחת", other: "{count} תוצאות" },
  typeMore: "הקלידו שתי אותיות או יותר כדי לחפש לקוחות, שיחות והזמנות.",
  searchFailed: "החיפוש לא הגיב; העמודים עדיין כאן.",
  keys: "↑ ↓ למעבר · Enter לפתיחה · Esc לסגירה",
  unnamed: "לקוח ללא שם",
  conversationDetail: "{channel} · {date}",
  bookingDetail: "{date} · {guests}",
  partySize: { one: "אורח אחד", two: "שני אורחים", other: "{count} אורחים" },
};
