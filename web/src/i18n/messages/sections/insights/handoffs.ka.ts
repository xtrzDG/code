/** `handoffs.*` texts of "Needs a person", in Georgian (wording: docs/glossary.md). */

import type { Translation } from "../../../translate";
import type { handoffsEn } from "./handoffs.en";

export const handoffsKa: Translation<typeof handoffsEn> = {
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
    profile_rule: "თქვენი ერთ-ერთი წესი",
    unverified_numbers: "დაუდასტურებელი ფასები ან ციფრები",
  },
  status: {
    pending: "თანამშრომლებს ვატყობინებთ",
    notified: "თანამშრომლებს ეცნობათ",
    notification_failed: "შეტყობინება ვერ მივიდა",
    resolved: "მოგვარდა",
  },
  notificationFailedHint: "თანამშრომლებმა შეტყობინება ვერ მიიღეს. გადაურეკეთ კლიენტს და შეამოწმეთ კონტაქტები პარამეტრებში.",
  summaryCodes: {
    model_declined: "ასისტენტმა ამ შეტყობინებას პასუხი არ გასცა.",
    model_unavailable: "ასისტენტი დროებით მიუწვდომელი იყო და პასუხი ვერ გასცა.",
    answer_unfinished: "ასისტენტმა პასუხის დასრულება ვერ მოახერხა.",
    unverified_values: "ასისტენტმა პასუხი არ გაგზავნა: მასში იყო ციფრები ან მტკიცებები, რომლებიც ბიზნესის მონაცემებში არ არის.",
    call_booking_unverified_values:
      "ზარისას ასისტენტმა დაასახელა ციფრები, რომლებიც ბიზნესის მონაცემებში არ არის. შეადარეთ ამ ზარის ჯავშანი ზარის ტრანსკრიპტს.",
    call_request_unverified_values:
      "ზარისას ასისტენტმა დაასახელა ციფრები, რომლებიც ბიზნესის მონაცემებში არ არის. შეადარეთ ამ ზარის მოთხოვნა ზარის ტრანსკრიპტს.",
    reply_undelivered: "ასისტენტის პასუხი კლიენტამდე ვერ მივიდა. დაუკავშირდით მას სხვა გზით.",
    data_erased: "მონაცემები წაიშალა კლიენტის თხოვნით.",
  },
  summaryCodesWithValues: {
    unverified_values: "ასისტენტმა პასუხი არ გაგზავნა: მასში იყო ციფრები ან მტკიცებები, რომლებიც ბიზნესის მონაცემებში არ არის ({values}).",
    call_booking_unverified_values:
      "ზარისას ასისტენტმა დაასახელა ციფრები, რომლებიც ბიზნესის მონაცემებში არ არის ({values}). შეადარეთ ამ ზარის ჯავშანი ზარის ტრანსკრიპტს.",
    call_request_unverified_values:
      "ზარისას ასისტენტმა დაასახელა ციფრები, რომლებიც ბიზნესის მონაცემებში არ არის ({values}). შეადარეთ ამ ზარის მოთხოვნა ზარის ტრანსკრიპტს.",
  },
  quote: {
    customer: "კლიენტის შეტყობინება",
    reply: "პასუხი, რომელიც ვერ მივიდა",
  },
};
