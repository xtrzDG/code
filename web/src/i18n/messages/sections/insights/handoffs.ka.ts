/** `handoffs.*` texts of handoffs to a person, in Georgian. */

import type { Translation } from "../../../translate";
import type { handoffsEn } from "./handoffs.en";

export const handoffsKa: Translation<typeof handoffsEn> = {
  loading: "გადაცემები იტვირთება…",
  tabsLabel: "გადაცემის სტატუსი",
  tabs: {
    open: "ღია",
    resolved: "დახურული",
    all: "ყველა",
  },
  urgency: {
    critical: "კრიტიკული",
    high: "სასწრაფო",
    normal: "ჩვეულებრივი",
    low: "არასასწრაფო",
  },
  reason: {
    customer_request: "ითხოვა ადამიანი",
    complaint: "საჩივარი",
    vip_guest: "VIP სტუმარი",
    non_standard_request: "არასტანდარტული მოთხოვნა",
    unknown_answer: "ასისტენტმა პასუხი არ იცოდა",
    emergency: "საგანგებო შემთხვევა",
    sensitive_topic: "დელიკატური თემა",
    profile_rule: "თქვენი გადაცემის წესი",
    unverified_numbers: "გადაუმოწმებელი ფასები ან ციფრები",
  },
  status: {
    pending: "თანამშრომლებს ვატყობინებთ",
    notified: "თანამშრომლებს ეცნობათ",
    notification_failed: "შეტყობინება ვერ მივიდა",
    resolved: "დახურულია",
  },
  notificationFailedHint: "თანამშრომლებმა შეტყობინება ვერ მიიღეს. გადაურეკეთ კლიენტს და შეამოწმეთ კონტაქტები პარამეტრებში.",
  resolvedAt: "დაიხურა {date}",
  resolve: "დახურვა",
  confirmResolve: {
    title: "დავხუროთ გადაცემა?",
    description: "{name}: ასისტენტი ამ კლიენტს ისევ უპასუხებს.",
    confirm: "დახურვა",
  },
  resolved: "გადაცემა დაიხურა",
  emptyOpenTitle: "ღია გადაცემები არ არის",
  emptyOpenDescription: "როცა ასისტენტი საუბარს ადამიანს გადასცემს, საუბარი აქ მოკლე შეჯამებით ელოდება.",
  emptyTitle: "გადაცემები ჯერ არ არის",
};
