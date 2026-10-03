/** `quickReplies.*` texts of Settings → Quick replies, in Georgian. */

import type { Translation } from "../../../translate";
import type { quickRepliesEn } from "./quickReplies.en";

export const quickRepliesKa: Translation<typeof quickRepliesEn> = {
  description:
    "პასუხები, რომლებსაც გუნდი ხშირად აგზავნის, მზად თქვენი ბიზნესის ყველა ენაზე. საუბარში აკრიფეთ /, რომ ჩასვათ: კლიენტის სახელი და ჯავშნის დრო თავისით ჩაიწერება.",
  add: "ახალი სწრაფი პასუხი",
  loading: "სწრაფი პასუხები იტვირთება…",
  emptyTitle: "სწრაფი პასუხები ჯერ არ არის",
  emptyDescription: "სამუშაო საათები, როგორ მოგვაგნოთ, „გადმოგირეკავთ“: დაწერეთ ერთხელ და გაგზავნეთ ორი შეხებით.",
  listLabel: "სწრაფი პასუხები",
  languages: "ენები",
  variablesUsed: "ავსებს",
  edit: "რედაქტირება",
  editLabel: "სწრაფი პასუხის „{title}“ რედაქტირება",
  delete: "წაშლა",
  deleteLabel: "სწრაფი პასუხის „{title}“ წაშლა",
  confirmDelete: {
    title: "წავშალოთ სწრაფი პასუხი?",
    description: "„{title}“ მთელ გუნდს გაუქრება სიიდან.",
    confirm: "წაშლა",
  },
  deleted: "სწრაფი პასუხი წაიშალა",
  saved: "სწრაფი პასუხი შენახულია",
  editor: {
    newTitle: "ახალი სწრაფი პასუხი",
    editTitle: "სწრაფი პასუხის რედაქტირება",
    description: "დაწერეთ ყველა ენაზე, რომელზეც თქვენი კლიენტები წერენ. თანამშრომლები ტექსტს საუბრის ენაზე დაინახავენ.",
    title: "სახელი",
    titleHint: "ასე ჩანს პასუხი გუნდის სიაში.",
    shortcut: "შემოკლება",
    shortcutHint: "იკრიფება / ნიშნის შემდეგ პასუხის ველში: ასოები, ციფრები, - და _.",
    shortcutInvalid: "მხოლოდ ასოები, ციფრები, - და _, ჰარის გარეშე.",
    texts: "ტექსტი",
    textIn: "ტექსტი ({language})",
    textHint: "თუ ენა არ გჭირდებათ, ცარიელი დატოვეთ. საჭიროა ერთი ტექსტი მაინც.",
    needOneText: "დაწერეთ ტექსტი ერთ ენაზე მაინც.",
    insert: "ჩასმა",
    insertLabel: "„{variable}“ ჩასმა ტექსტში ({language})",
    preview: "როგორ დაინახავს კლიენტი",
    previewHint: "კლიენტისა და ჯავშნის მაგალითით.",
    sample: {
      name: "ნინო",
      bookingTime: "შაბ, 19:30",
    },
    save: "შენახვა",
    saving: "ინახება…",
    cancel: "გაუქმება",
    length: "{count} / {max}",
  },
  variables: {
    name: "კლიენტის სახელი",
    booking_time: "ჯავშნის დრო",
    business_name: "ბიზნესის სახელი",
  },
  errors: {
    shortcut_taken: "ეს შემოკლება სხვა სწრაფ პასუხს უკვე აქვს.",
    too_many_quick_replies: "ბიზნესს შეიძლება ჰქონდეს არაუმეტეს 100 სწრაფი პასუხისა. წაშალეთ ის, რომელიც აღარ გჭირდებათ.",
    unknown_variable: "ჩასმა შეიძლება მხოლოდ {name}, {booking_time} და {business_name}. შეამოწმეთ ფიგურული ფრჩხილები ტექსტში.",
    duplicate_language: "თითოეულ ენაზე მხოლოდ ერთი ტექსტი შეიძლება იყოს.",
  },
};
