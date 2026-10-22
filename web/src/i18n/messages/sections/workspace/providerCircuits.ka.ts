/** `providerCircuits.*` texts in Georgian (typed against providerCircuits.en.ts). */

import type { Translation } from "../../../translate";
import type { providerCircuitsEn } from "./providerCircuits.en";

export const providerCircuitsKa: Translation<typeof providerCircuitsEn> = {
  title: "პროვაიდერების ამომრთველები",
  description:
    "ყოველ პროვაიდერს, რომლის გავლითაც დამმუშავებლები აგზავნიან, ამომრთველი აქვს. წუთში ხუთი შეცდომა მას რთავს: შეტყობინებები პროვაიდერთან მიმართვის გარეშე ელოდება, 30 წამის შემდეგ კი ერთი საცდელი გაგზავნა გადის. ერთი პროვაიდერი დამმუშავებლის მიწოდების ნაკადების არაუმეტეს ნახევარს იკავებს.",
  none: "არცერთ დამმუშავებელს ამომრთველები არ უცნობებია",
  noneDescription: "დამმუშავებლები ამომრთველებს ყოველ სიგნალთან ერთად აცნობებენ; წინა გამოშვების დამმუშავებელი მათ არ აცნობებს.",
  circuit: "ამომრთველი",
  state: "მდგომარეობა",
  workers: "დამმუშავებლები, სადაც ჩართული არ არის",
  workersOf: "{notClosed} / {total}",
  failures: "შეცდომები ბოლო წუთში",
  opened: "ამოირთო",
  states: {
    closed: "ჩართულია",
    half_open: "საცდელი გაგზავნა",
    open: "ამორთულია",
  },
  providers: {
    meta: "Meta (WhatsApp, Messenger, Instagram)",
    telegram: "Telegram-ის ბოტები",
    platform_bot: "პლატფორმის ბოტი",
    twilio_sms: "SMS (Twilio)",
    smtp: "ელფოსტა (SMTP)",
    flitt: "გადახდები (Flitt)",
    web_push: "ვებ-შეტყობინებები",
  },
};
