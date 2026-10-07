/** `helpCenter.*` texts of the help center, the article drawer and "Help and support", in Georgian. */

import type { Translation } from "../../../translate";
import type { helpCenterEn } from "./helpCenter.en";

export const helpCenterKa: Translation<typeof helpCenterEn> = {
  title: "დახმარება",
  description: "მოკლე ინსტრუქციები კაბინეტის ყველა ნაწილისთვის.",
  searchLabel: "დახმარებაში ძიება",
  searchPlaceholder: "Telegram, ჯავშანი, ინვოისი…",
  search: "ძიება",
  clearSearch: "ძიების გასუფთავება",
  results: {
    one: "ნაპოვნია {count} სტატია",
    other: "ნაპოვნია {count} სტატია",
  },
  noResults: "„{query}“ — ვერაფერი მოიძებნა. სცადეთ სხვა სიტყვა.",
  topics: {
    getting_started: "დაწყება",
    channels: "არხები",
    daily_work: "ყოველდღიური სამუშაო",
    account: "ანგარიში და გადახდა",
  },
  allArticles: "ყველა სტატია",
  related: "წაიკითხეთ შემდეგ",
  otherLanguage: "ეს სტატია ჯერ არ არის თარგმნილი, ამიტომ ნაჩვენებია ენაზე: {language}.",
  pageHelp: "ამ გვერდის დახმარება",
  drawerTitle: "დახმარება",
  openInCenter: "დახმარების ცენტრში გახსნა",
  back: "უკან",
  stillStuck: "კიდევ გაქვთ კითხვა?",
  stillStuckLead: "მოგვწერეთ: გიპასუხებთ გუნდის წევრი.",
  noSupportLead: "შეამოწმეთ პლატფორმის მდგომარეობის გვერდი: თუ რამე ყველასთვის არ მუშაობს, გუნდი ამაზე უკვე მუშაობს.",
  tipsAgain: "მინიშნებების ხელახლა ჩვენება",
  tipsShown: "მინიშნებები ისევ გამოჩნდება გვერდებზე „შემოსული“, „ასისტენტი“ და „არხები“.",
  opensInNewTab: "გაიხსნება ახალ ჩანართში",
  support: {
    title: "დახმარება და მხარდაჭერა",
    center: "დახმარების ცენტრი",
    whatsNew: "რა არის ახალი",
    unread: {
      one: "{count} ახალი",
      other: "{count} ახალი",
    },
    status: "პლატფორმის სტატუსი",
    contact: "მხარდაჭერას მივწეროთ",
    whatsapp: "WhatsApp",
    telegram: "Telegram",
    email: "ელფოსტა",
  },
};
