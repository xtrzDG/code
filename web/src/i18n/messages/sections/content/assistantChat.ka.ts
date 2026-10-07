/** `assistant.*` texts of the test chat, in Georgian. */

import type { Translation } from "../../../translate";
import type { assistantChatEn } from "./assistantChat.en";

export const assistantChatKa: Translation<typeof assistantChatEn> = {
  chat: {
    newConversation: "ახალი საუბარი",
    logLabel: "სატესტო საუბარი",
    emptyTitle: "დაიწყეთ სატესტო საუბარი",
    emptyDescription: "იკითხეთ ის, რასაც თქვენი კლიენტები კითხულობენ, ნებისმიერ ენაზე. ან სცადეთ:",
    suggestions: {
      hours: "რომელ საათებში მუშაობთ?",
      price: "რა ღირს?",
      booking: "მინდა დავჯავშნო ხვალ 19:00-ზე 4 კაცზე",
      human: "შეიძლება ადამიანს დაველაპარაკო?",
    },
    typing: "ასისტენტი წერს…",
    choicesLabel: "ასარჩევი პასუხები",
    inputLabel: "შეტყობინება",
    placeholder: "დაწერეთ შეტყობინება…",
    inputHint: {
      one: "Enter — გაგზავნა, Shift+Enter — ახალი სტრიქონი. {count} სიმბოლომდე.",
      other: "Enter — გაგზავნა, Shift+Enter — ახალი სტრიქონი. {count} სიმბოლომდე.",
    },
    send: "გაგზავნა",
    failed: "არ გაიგზავნა.",
    silent: "ასისტენტი დუმს: საუბარი ადამიანს გადაეცა.",
    handedOffTitle: "გადაეცა ადამიანს",
    handedOffDescription: "ნამდვილ ჩატში ახლა თქვენი თანამშრომელი უპასუხებდა, ამიტომ ასისტენტი დუმს. შემოწმების გასაგრძელებლად დაიწყეთ ახალი საუბარი.",
    guardRewritten: "ციფრები შემოწმდა და გასწორდა",
    guardHandedOff: "გადაეცა: ციფრში დარწმუნებული არ იყო",
    handedOff: "გადაეცა ადამიანს",
    bookingsCreated: { one: "შეიქმნა სატესტო ჯავშანი", other: "შეიქმნა {count} სატესტო ჯავშანი" },
    leadsCreated: { one: "შეიქმნა სატესტო განაცხადი", other: "შეიქმნა {count} სატესტო განაცხადი" },
    toolCalls: { one: "ინსტრუმენტის {count} გამოძახება", other: "ინსტრუმენტის {count} გამოძახება" },
    toolError: "შეცდომა",
    toolInput: "შემავალი მონაცემები",
    toolResult: "შედეგი",
    noVersionsTitle: "შესამოწმებელი ჯერ არაფერია",
    noVersionsDescription: "გამოიყენეთ ცვლილებები ასისტენტის პირველი განახლების მოსამზადებლად და აქ ესაუბრეთ.",
    errors: {
      service: "ენობრივი მოდელი ახლა მიუწვდომელია. სცადეთ ერთ წუთში.",
    },
  },
};
