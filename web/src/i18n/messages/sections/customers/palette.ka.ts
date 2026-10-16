/** `palette.*` texts: the command palette (Cmd/Ctrl+K), in Georgian. */

import type { Translation } from "../../../translate";
import type { paletteEn } from "./palette.en";

export const paletteKa: Translation<typeof paletteEn> = {
  title: "ძიება და გადასვლა",
  open: "ძიება",
  openTitle: "ძიება (Ctrl+K ან ⌘K)",
  placeholder: "კლიენტი, საუბარი, ჯავშანი ან გვერდი",
  groups: {
    navigation: "გადასვლა",
    customers: "კლიენტები",
    conversations: "საუბრები",
    bookings: "ჯავშნები",
  },
  searching: "ვეძებთ…",
  noResults: "„{text}“ ვერ მოიძებნა.",
  resultCount: { one: "{count} შედეგი", other: "{count} შედეგი" },
  typeMore: "კლიენტების, საუბრებისა და ჯავშნების საძიებლად აკრიფეთ მინიმუმ ორი ასო.",
  searchFailed: "ძიებამ არ უპასუხა; გვერდები მაინც აქ არის.",
  keys: "↑ ↓ — არჩევა · Enter — გახსნა · Esc — დახურვა",
  unnamed: "კლიენტი სახელის გარეშე",
  conversationDetail: "{channel} · {date}",
  bookingDetail: "{date} · {guests}",
  partySize: { one: "{count} სტუმარი", other: "{count} სტუმარი" },
};
