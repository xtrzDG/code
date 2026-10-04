/** `digestChannels.*` texts: სად მოდის მფლობელის შეჯამებები (ელფოსტა, მოწყობილობები, Telegram, WhatsApp), ქართულად. */

import type { Translation } from "../../../translate";
import type { digestChannelsEn } from "./digestChannels.en";

export const digestChannelsKa: Translation<typeof digestChannelsEn> = {
  title: "სად მოდის",
  email: "ელფოსტა",
  emailTo: "მისამართზე {email}",
  emailMissing: "ტელეფონით შედიხართ, ამიტომ შეჯამებებისთვის ელფოსტა არ არის.",
  emailNotReady: "ელფოსტა ამ პლატფორმაზე ჯერ არ არის მორგებული.",
  push: "მოწყობილობები",
  devices: {
    one: "შეტყობინებები ჩართულია {count} მოწყობილობაზე",
    other: "შეტყობინებები ჩართულია {count} მოწყობილობაზე",
  },
  noDevices: "შეტყობინებები ჯერ არცერთ მოწყობილობაზე არ არის ჩართული.",
  manageDevices: "შეტყობინებების პარამეტრები",
  telegram: "Telegram",
  telegramHint: "სრული ანგარიში პლატფორმის ბოტისგან.",
  telegramChat: "Telegram-ის ჩატი",
  telegramNoChats: "ჯერ დააკავშირეთ Telegram-ის ჩატი: „არხები“ → „შეტყობინებები თანამშრომლებს Telegram-ში“.",
  openChannels: "„არხების“ გახსნა",
  telegramNotReady: "Telegram ამ პლატფორმაზე ჯერ არ არის მორგებული.",
  whatsapp: "WhatsApp",
  whatsappHint: "მოკლე შეჯამება ბმულით, პლატფორმის ნომრიდან.",
  whatsappNumber: "თქვენი WhatsApp ნომერი",
  whatsappNumberHint: "ქვეყნის კოდით. WhatsApp-ის არჩევით თანხმდებით ამ შეტყობინებების მიღებაზე.",
  whatsappNotReady: "WhatsApp-ში შეჯამებები ამ პლატფორმაზე ჯერ არ არის მორგებული.",
  save: "შენახვა",
  saved: "შენახულია",
  invalidNumber: "შეიყვანეთ ნომერი ქვეყნის კოდით, მაგალითად +995 555 12 34 56.",
  refusals: {
    telegramNotAvailable: "Telegram-ში შეჯამებები ამ პლატფორმაზე ჯერ არ არის მორგებული.",
    telegramChatNotLinked: "ეს ჩატი ბიზნესს აღარ არის დაკავშირებული. აირჩიეთ სხვა ან ხელახლა დააკავშირეთ.",
    whatsappNotAvailable: "WhatsApp-ში შეჯამებები ამ პლატფორმაზე ჯერ არ არის მორგებული.",
    whatsappNumberMissing: "შეიყვანეთ WhatsApp ნომერი შეჯამებებისთვის.",
  },
};
