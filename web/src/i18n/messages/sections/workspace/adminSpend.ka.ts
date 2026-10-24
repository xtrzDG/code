/** `adminSpend.*` texts in Georgian (typed against adminSpend.en.ts). */

import type { Translation } from "../../../translate";
import type { adminSpendEn } from "./adminSpend.en";

export const adminSpendKa: Translation<typeof adminSpendEn> = {
  title: "დღევანდელი ხარჯები",
  description: "რამდენი ემართება პლატფორმას პროვაიდერებისთვის {day}-ისთვის (UTC). ხარჯები, რომლებიც პროვაიდერს ჯერ არ უცნობებია, დაგეგმილი ფასებით ითვლება.",
  total: "სულ დღეს",
  weekMean: "დღიური საშუალო წინა 7 დღეში: {amount}",
  spike: "ჩვეულებრივზე ბევრად მეტი",
  budget: "დღიური ბიუჯეტის ({amount}) {percent}%",
  budgetLabel: "დღიური ბიუჯეტიდან გამოყენებული",
  noBudget: "დღიური ბიუჯეტი არ არის დაყენებული (PLATFORM_DAILY_SPEND_BUDGET_USD).",
  providersLabel: "ხარჯები პროვაიდერების მიხედვით",
  providers: {
    language_model: "AI მოდელი",
    voice: "ხმოვანი აგენტი",
    telephony: "სატელეფონო ზარები",
    whatsapp: "WhatsApp-ის შაბლონები",
    transcription: "ხმოვანი შეტყობინებების გაშიფვრა",
  },
  brakedTitle: "კლიენტები, რომლებმაც ხარჯების ლიმიტს გადააჭარბეს",
  brakedNone: "დღეს არცერთ კლიენტს არ გადაუჭარბებია ხარჯების ლიმიტი.",
  levels: {
    soft_limit: "უფრო იაფი მოდელი",
    hard_limit: "მხოლოდ მოთხოვნები",
  },
  brakedLine: "{spend} / {limit}, {time}-დან",
};
