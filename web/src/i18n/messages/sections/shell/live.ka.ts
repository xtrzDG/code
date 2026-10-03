/** `live.*` ქართულად (იხ. live.en.ts). */

import type { Translation } from "../../../translate";
import type { liveEn } from "./live.en";

export const liveKa: Translation<typeof liveEn> = {
  status: {
    live: "ონლაინ",
    connecting: "მიერთება…",
    reconnecting: "ხელახლა მიერთება…",
    paused: "განახლებები შეჩერებულია",
  },
  updatedJustNow: "განახლდა ახლახან",
  updatedMinutesAgo: {
    one: "განახლდა {count} წუთის წინ",
    other: "განახლდა {count} წუთის წინ",
  },
  updatedAt: "განახლდა {time}-ზე",
  updating: "ახლდება…",
  liveHint: "გვერდი თავად ახლდება, როცა კლიენტები წერენ, ჯავშნიან ან ადამიანს ელოდებიან.",
  reconnectingHint: "კავშირი გაწყდა, ხელახლა ვუერთდებით. შეგიძლიათ ახლავე სცადოთ.",
  reconnect: "ახლავე ცდა",
  needsPersonTitle: "კლიენტს ადამიანი სჭირდება",
  needsPersonOpen: "გახსნა",
  needsPersonAnnouncement: "კლიენტს ადამიანი სჭირდება. ელოდება: {count}.",
  sound: "ხმოვანი სიგნალი, როცა ადამიანია საჭირო",
  soundHint: "მოკლე ხმა ამ მოწყობილობაზე, როცა საუბარი თქვენს გუნდს გადაეცემა.",
};
