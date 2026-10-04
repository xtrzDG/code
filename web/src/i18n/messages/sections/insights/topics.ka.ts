/** `topics.*` texts: მიმოხილვის ბარათი „რას კითხულობენ კლიენტები“, ქართულად. */

import type { Translation } from "../../../translate";
import type { topicsEn } from "./topics.en";

export const topicsKa: Translation<typeof topicsEn> = {
  title: "რას კითხულობენ კლიენტები",
  description: "ბოლო 30 დღის პირველი შეტყობინებები, ყოველ ღამე თემებად დაჯგუფებული.",
  updated: "განახლდა {date}",
  waiting: "თემები გამოჩნდება საუბრების პირველი ღამის შემდეგ.",
  empty: "ბოლო 30 დღეში კლიენტებს ჯერ არ მოუწერიათ.",
  conversations: { one: "{count} საუბარი", other: "{count} საუბარი" },
  unanswered: { one: "{count} პასუხის გარეშე", other: "{count} პასუხის გარეშე" },
  unansweredHint: "კითხვები, რომლებსაც ასისტენტმა ვერ უპასუხა: დაამატეთ პასუხი და ის უპასუხებს.",
  addAnswer: "პასუხის დამატება",
  otherLanguages: "სხვა ენები",
  languageLabel: "ენა",
  loading: "თემები იტვირთება…",
};
