/**
 * `insights.*` texts of shared by the dashboard, conversations, bookings,
 * leads and handoffs, in Georgian.
 */

import type { Translation } from "../../../translate";
import type { insightsCommonEn } from "./common.en";

export const insightsCommonKa: Translation<typeof insightsCommonEn> = {
  loadingMore: "იტვირთება…",
  showMore: "მეტის ჩვენება",
  shownOf: "ნაჩვენებია {shown} / {total}",
  includeTest: "სატესტოების ჩვენება",
  includeTestHint: "სატესტო ჩატიდან და შემოწმებებიდან",
  testBadge: "ტესტი",
  afterHours: "სამუშაო საათების გარეთ",
  unknownCustomer: "კლიენტი სახელის გარეშე",
  callPhone: "დარეკვა: {phone}",
  openConversation: "საუბრის გახსნა",
  all: "ყველა",
  clearFilters: "ფილტრების გასუფთავება",
  noMatchesTitle: "ფილტრებს არაფერი ემთხვევა",
  noMatchesDescription: "შეცვალეთ ან გაასუფთავეთ ფილტრები.",
  copy: "კოპირება",
  copied: "დაკოპირდა",
  copyFailed: "კოპირება ვერ მოხერხდა. მონიშნეთ ტექსტი და დააკოპირეთ ხელით.",
  customerMessage: {
    title: "შეტყობინება კლიენტისთვის",
    description: "აქედან ასისტენტი ამ ტექსტს თავად არ აგზავნის. გაუგზავნეთ კლიენტს იმ არხში, სადაც ურთიერთობთ.",
  },
  channels: {
    phone: "ტელეფონი",
    whatsapp: "WhatsApp",
    instagram: "Instagram",
    messenger: "Messenger",
    telegram: "Telegram",
    web_chat: "ჩატი საიტზე",
    viber: "Viber",
    owner_test: "სატესტო ჩატი",
  },
};
