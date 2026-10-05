/** `platformStatus.*` texts of the public status page and the cabinet's announcement banner, in Georgian. */

import type { Translation } from "../../../translate";
import type { platformStatusEn } from "./platformStatus.en";

export const platformStatusKa: Translation<typeof platformStatusEn> = {
  title: "პლატფორმის სტატუსი",
  description: "მუშაობს თუ არა ახლა კლიენტებთან ჩატები, არხები, ზარები და კაბინეტი, და როგორ ჩაიარა ბოლო 90 დღემ.",
  overall: {
    operational: "ყველაფერი მუშაობს",
    maintenance: "მიმდინარეობს გეგმიური სამუშაოები",
    degraded: "ზოგი ნაწილი ჩვეულებრივზე ნელა მუშაობს",
    outage: "ზოგი ნაწილი ახლა არ მუშაობს",
    no_data: "ჯერ არაფერი გაზომილა",
  },
  levels: {
    operational: "მუშაობს",
    maintenance: "გეგმიური სამუშაოები",
    degraded: "ნელა",
    outage: "არ მუშაობს",
    no_data: "მონაცემები არ არის",
  },
  components: {
    chat: "საიტის ჩატი და ჩატის გვერდი",
    meta: "WhatsApp, Instagram და Messenger",
    telegram: "Telegram",
    voice: "სატელეფონო ზარები",
    cabinet: "კაბინეტი და შესვლა",
  },
  checkedAt: "შემოწმდა {time}",
  componentsTitle: "პლატფორმის ნაწილები",
  historyLabel: "{component}: ბოლო 90 დღე",
  historyStart: "90 დღის წინ",
  historyEnd: "დღეს",
  uptime: {
    one: "{count} დღის განმავლობაში {share} პრობლემების გარეშე",
    other: "{count} დღის განმავლობაში {share} პრობლემების გარეშე",
  },
  observingSince: "დაკვირვების დაწყება: {date}",
  noHistory: "გაზომილი დღეები ჯერ არ არის",
  day: "{day}: {level}",
  announcementLevels: {
    info: "შეტყობინება",
    maintenance: "გეგმიური სამუშაოები",
    degraded: "შენელება",
    outage: "გათიშვა",
  },
  activeTitle: "ახლა",
  scheduled: "დაგეგმილი",
  starts: "დაიწყება {time}",
  since: "{time}-დან",
  expectedEnd: "სავარაუდო დასრულება {time}",
  resolved: "მოგვარდა {time}",
  updated: "განახლდა {time}",
  affects: "ეხება: {components}",
  pastTitle: "წარსული ინციდენტები",
  pastEmpty: "ბოლო 90 დღეში ინციდენტი არ ყოფილა.",
  unreachable: {
    title: "სტატუსი ვერ ჩაიტვირთა",
    body: "ეს გვერდი ახლა ვერ უკავშირდება პლატფორმას. თუ ჩატებიც არ მუშაობს, მისწერეთ მხარდაჭერას: გუნდმა უკვე იცის.",
  },
  selfMeasured: "პლატფორმა ყოველ ხუთ წუთში ამოწმებს თავს, გუნდი კი ამატებს იმას, რაც იცის.",
  openCabinet: "კაბინეტის გახსნა",
  banner: {
    region: "პლატფორმის შეტყობინება",
    details: "დეტალები",
    dismiss: "დამალვა",
  },
};
