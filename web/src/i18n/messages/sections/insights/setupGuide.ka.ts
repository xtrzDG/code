/** `setupGuide.*`: the Overview's setup guide, the progress ring and the milestone toasts, in Georgian. */

import type { Translation } from "../../../translate";
import type { setupGuideEn } from "./setupGuide.en";

export const setupGuideKa: Translation<typeof setupGuideEn> = {
  titleSetup: "მოარგეთ ასისტენტი",
  titleLive: "მოიზიდეთ პირველი კლიენტები",
  descriptionSetup: "ყოველი ნაბიჯი იქიდან იხსნება, სადაც გაჩერდით. ასისტენტი კლიენტებს გამოქვეყნების შემდეგ უპასუხებს.",
  liveSince: "კლიენტებს პასუხობს. გაშვების თარიღი: {date}",
  minutesLeft: { one: "დარჩა დაახლოებით {count} წუთი", other: "დარჩა დაახლოებით {count} წუთი" },
  continueSetup: "მორგების გაგრძელება",
  afterLaunchHint: "გაშვების შემდეგ: შემოწმება ტელეფონიდან, მეორე არხი და ბმული კლიენტებისთვის.",
  minutes: "{count} წთ",
  optional: "სურვილისამებრ",
  skip: "გამოტოვება",
  unskip: "დაბრუნება",
  skipLabel: "„{step}“ — გამოტოვება",
  unskipLabel: "„{step}“ — დაბრუნება",
  status: {
    next: "შემდეგი",
    skipped: "გამოტოვებული",
  },
  phone: {
    description: "ტელეფონის კამერა კოდზე მიმართეთ და ასისტენტს ისე მისწერეთ, როგორც კლიენტი მისწერდა.",
    qrAlt: "{link} ბმულის QR კოდი",
    copyLink: "ბმულის კოპირება",
    unavailable: "ჩატის გვერდი გამორთულია. ჩართეთ ვებსაიტის ჩატი „არხებში“ ან ტელეფონიდან მისწერეთ დაკავშირებულ მესენჯერში.",
    orTelegram: "ან Telegram-ში:",
    listening: "ველოდებით თქვენს შეტყობინებას…",
    hint: "ნაბიჯი შესრულდება, როცა თქვენი შეტყობინება მოვა.",
    success: "მუშაობს: თქვენი შეტყობინება ასისტენტამდე მივიდა.",
    hide: "დამალვა",
  },
  finished: {
    title: "ყველაფერი მზადაა",
    description: "ასისტენტი კლიენტებს პასუხობს და მათ იციან, სად იპოვონ.",
    dismiss: "ბარათის დამალვა",
  },
  wins: {
    title: "მიღწევები",
    first_conversation: "პირველი საუბარი კლიენტთან",
    first_booking: "პირველი ჯავშანი",
    first_after_hours_booking: "პირველი ჯავშანი არასამუშაო საათებში",
  },
  ring: {
    title: "მორგება",
    label: "მორგება შესრულებულია {percent}%-ით",
    short: "{percent}%",
  },
  celebrations: {
    first_conversation: {
      title: "პირველმა კლიენტმა მოგწერათ",
      description: "ასისტენტმა უპასუხა. საუბარი შემოსულებშია.",
    },
    first_booking: {
      title: "პირველი ჯავშანი",
      description: "ასისტენტმა კლიენტი თავად ჩაწერა.",
    },
    first_after_hours_booking: {
      title: "ჯავშანი, როცა დაკეტილი იყავით",
      description: "კლიენტი არასამუშაო საათებში ჩაეწერა და პასუხი არავის დასჭირდა.",
    },
    openInbox: "შემოსულის გახსნა",
    openBookings: "ჯავშნების გახსნა",
    close: "დახურვა",
  },
};
