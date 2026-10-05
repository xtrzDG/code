/** `segments.*` texts: saved groups of customers and their CSV, in Georgian. */

import type { Translation } from "../../../translate";
import type { segmentsEn } from "./segments.en";

export const segmentsKa: Translation<typeof segmentsEn> = {
  loading: "სეგმენტები იტვირთება…",
  new: "ახალი სეგმენტი",
  empty: "სეგმენტები ჯერ არ არის",
  emptyDescription: "შეინახეთ კლიენტების ჯგუფი, მაგალითად მუდმივი სტუმრები, რომლებიც 60 დღეა არ მოსულან, და ჩამოტვირთეთ ის დაგზავნისთვის.",
  limit: "ბიზნესს შეიძლება ჰქონდეს არაუმეტეს 50 სეგმენტისა. ახლის შესანახად წაშალეთ ერთ-ერთი.",
  members: "კლიენტები",
  noMembers: "ამ სეგმენტს ახლა არავინ შეესაბამება.",
  showMore: "მეტი კლიენტის ჩვენება",
  export: "CSV-ის ჩამოტვირთვა",
  exportHint: "სეგმენტის კლიენტები ტელეფონებით, არხებით, ტეგებითა და ჯავშნებით — სხვა სერვისში დაგზავნისთვის.",
  edit: "შეცვლა",
  delete: "წაშლა",
  deleteTitle: "წავშალოთ სეგმენტი „{name}“?",
  deleteBody: "იშლება მხოლოდ შენახული წესები; კლიენტები არ იცვლება.",
  deleted: "სეგმენტი წაიშალა",
  saved: "სეგმენტი შენახულია",
  editor: {
    newTitle: "ახალი სეგმენტი",
    editTitle: "სეგმენტის შეცვლა",
    name: "სახელი",
    namePlaceholder: "მაგ., 60 დღეა არ მოსულან",
    rules: "ვინ შედის",
    rulesHint: "ყველა შევსებული წესი უნდა სრულდებოდეს. დაბლოკილი და წაშლილი კლიენტები არასოდეს შედიან.",
    tag: "ტეგი",
    anyTag: "ნებისმიერი ტეგი",
    lastVisit: "ბოლო ვიზიტი … დღეზე მეტი ხნის წინ",
    minBookings: "მინიმუმ … ჯავშანი",
    maxBookings: "მაქსიმუმ … ჯავშანი",
    vipOnly: "მხოლოდ VIP კლიენტები",
    save: "სეგმენტის შენახვა",
  },
  errors: {
    name: "დაარქვით სეგმენტს სახელი (60 სიმბოლომდე).",
    days: "დღეები — მთელი რიცხვი 1-დან 3650-მდე.",
    bookings: "ჯავშნები — მთელი რიცხვი 0-დან 10000-მდე.",
    minMax: "„მინიმუმი“ არ შეიძლება იყოს „მაქსიმუმზე“ მეტი.",
  },
  preview: {
    counting: "ვითვლით…",
    count: { one: "შეესაბამება {count} კლიენტი", other: "შეესაბამება {count} კლიენტი" },
    atLeast: { one: "შეესაბამება მინიმუმ {count} კლიენტი", other: "შეესაბამება მინიმუმ {count} კლიენტი" },
    none: "ჯერ არავინ შეესაბამება.",
  },
  summary: {
    everyone: "ყველა კლიენტი",
    tag: "ტეგი „{tag}“",
    lastVisit: {
      one: "ბოლო ვიზიტი {count} დღეზე მეტი ხნის წინ",
      other: "ბოლო ვიზიტი {count} დღეზე მეტი ხნის წინ",
    },
    minBookings: { one: "მინიმუმ {count} ჯავშანი", other: "მინიმუმ {count} ჯავშანი" },
    maxBookings: { one: "მაქსიმუმ {count} ჯავშანი", other: "მაქსიმუმ {count} ჯავშანი" },
    vipOnly: "მხოლოდ VIP",
  },
};
