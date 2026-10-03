/** `tunnel.*`: the frame of "Create an AI assistant", in Georgian. */

import type { Translation } from "../../../translate";
import type { tunnelEn } from "./tunnel.en";

export const tunnelKa: Translation<typeof tunnelEn> = {
  pageTitle: "AI ასისტენტის შექმნა",
  newAssistant: "ახალი ასისტენტი",
  railLabel: "მორგების ნაბიჯები",
  steps: {
    business: "თქვენი ბიზნესი",
    place: "სად ხართ",
    offer: "რას სთავაზობთ",
    hours: "საათები და ჯავშნები",
    people: "ვინ დაეხმარება",
    channels: "სად წერენ კლიენტები",
    try: "გამოცდა",
    launch: "გაშვება",
  },
  stepOf: "ნაბიჯი {number} {total}-დან",
  stepState: {
    done: "მზადაა",
    skipped: "გამოტოვებულია",
    current: "აქ ხართ",
    todo: "ჯერ წინაა",
  },
  announce: "ნაბიჯი {number} {total}-დან: {title}",
  announceFinale: "თქვენი ასისტენტი მუშაობს",
  back: "უკან",
  continue: "შემდეგი",
  skip: "ჯერჯერობით გამოტოვება",
  enterHint: "ან დააჭირეთ Enter-ს",
  exit: "შენახვა და გასვლა",
  saving: "ინახება…",
  saved: "შენახულია",
  saveFailed: "ჯერ არ შენახულა",
  ownerOnlyTitle: "ასისტენტს მფლობელი ქმნის",
  ownerOnlyText: "მისი მორგება მხოლოდ „{business}“-ის მფლობელს შეუძლია. საუბრები, ჯავშნები და მოთხოვნები კაბინეტში გამოჩნდება, როგორც კი ასისტენტი ამუშავდება.",
  openCabinet: "კაბინეტის გახსნა",
};
