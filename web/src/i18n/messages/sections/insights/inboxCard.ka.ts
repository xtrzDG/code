/** `inboxCard.*` texts of a conversation in the team inbox, in Georgian. */

import type { Translation } from "../../../translate";
import type { inboxCardEn } from "./inboxCard.en";

export const inboxCardKa: Translation<typeof inboxCardEn> = {
  back: "შემოსულში დაბრუნება",
  openDetails: "დეტალები",
  openDetailsOf: "საუბრის დეტალები: {name}",
  openNotes: "შენიშვნები",
  openNotesCount: {
    one: "შენიშვნები ({count})",
    other: "შენიშვნები ({count})",
  },
  panelLabel: "საუბრის შესახებ",
  panelTabs: "პანელი",
  messageContext: {
    story_reply: "პასუხი თქვენს ისტორიაზე",
    story_mention: "მოხსენიება კლიენტის ისტორიაში",
  },
  offeredChoices: "შეთავაზებული ვარიანტები",
  actions: {
    label: "სწრაფი მოქმედებები",
    resolve: "მოგვარდა",
    resolveHint: "ასისტენტი ამ კლიენტს ისევ უპასუხებს",
    call: "დარეკვა",
    callLabel: "დარეკვა ნომერზე {phone}",
    book: "დაჯავშნა",
  },
  work: {
    needsPerson: "ადამიანის დახმარება",
    request: "მოთხოვნა",
    requestStatus: "მოთხოვნის სტატუსი",
    since: "{time}-დან",
  },
  details: {
    customer: "კლიენტი",
    channel: "არხი",
    language: "ენა",
    started: "დაიწყო",
    lastMessage: "ბოლო შეტყობინება",
  },
  technical: {
    title: "ტექნიკური დეტალები",
    hint: "რა დგას პასუხების უკან: ასისტენტის განახლება, რომელმაც ისინი გასცა, და მისი ზუსტი მოთხოვნები თქვენს მონაცემებზე.",
    tokens: "ტოკენები",
    cost: "ხელოვნური ინტელექტის ღირებულება",
    version: "ასისტენტის განახლება",
    message: "შეტყობინების ტექნიკური დეტალები",
  },
  notes: {
    title: "შენიშვნები",
    hint: "ამას მხოლოდ თქვენი გუნდი ხედავს",
    description: "შენიშვნები გუნდში რჩება: მათ ვერც კლიენტი ხედავს და ვერც ასისტენტი.",
    placeholder: "რა დავპირდით, ვინ გადარეკავს, რა უნდა გვახსოვდეს…",
    add: "შენიშვნის დამატება",
    adding: "ინახება…",
    added: "შენიშვნა შენახულია. მას მხოლოდ თქვენი გუნდი ხედავს.",
    unknownAuthor: "გუნდის ყოფილი წევრი",
    delete: "შენიშვნის წაშლა",
    confirmDelete: {
      title: "წავშალოთ შენიშვნა?",
      description: "ის მთელ გუნდს გაუქრება.",
      confirm: "წაშლა",
    },
    deleted: "შენიშვნა წაიშალა",
    empty: "შენიშვნები ჯერ არ არის. შენიშვნა შემდეგ ადამიანს დაეხმარება: რა დავპირდით, ვინ გადარეკავს.",
    loading: "შენიშვნები იტვირთება…",
    length: "{count} / {max}",
  },
  quickReplies: {
    open: "სწრაფი პასუხები",
    hint: "აკრიფეთ / სწრაფი პასუხებისთვის",
    listLabel: "სწრაფი პასუხები",
    loading: "სწრაფი პასუხები იტვირთება…",
    empty: "სწრაფი პასუხები ჯერ არ არის.",
    emptyOwner: "ხშირად გაგზავნილი პასუხები შექმენით აქ: პარამეტრები → სწრაფი პასუხები.",
    manage: "სწრაფი პასუხების მართვა",
    noMatch: "სწრაფი პასუხი „/{query}“ არ მოიძებნა.",
    missing: "გაგზავნამდე შეავსეთ:",
    fillLabel: "მნიშვნელობა: {variable}",
    fill: "ჩასმა",
    placeholdersLeft: "გაგზავნამდე შეავსეთ ფიგურულ ფრჩხილებში მოცემული ნაწილები: {variables}.",
    variables: {
      name: "კლიენტის სახელი",
      booking_time: "ჯავშნის დრო",
      business_name: "ბიზნესის სახელი",
    },
  },
  composer: {
    placeholder: "მისწერეთ კლიენტს…",
    sendLabel: "გაგზავნა",
  },
  request: {
    updated: "მოთხოვნა: {status}",
  },
  resolveConfirm: {
    title: "მოინიშნოს მოგვარებულად?",
    description: "{name}: ასისტენტი ამ კლიენტს ისევ დაიწყებს პასუხს.",
    confirm: "მოგვარდა",
  },
  resolved: "მოინიშნა მოგვარებულად. ასისტენტი ამ კლიენტს ისევ პასუხობს.",
  reopened: "გადაცემა ისევ ღიაა. ასისტენტი არ უპასუხებს, სანამ არ მოგვარდება.",
};
