/** `tunnelBusiness.*`: the business and where it is, in Georgian. */

import type { Translation } from "../../../translate";
import type { tunnelBusinessEn } from "./tunnelBusiness.en";

export const tunnelBusinessKa: Translation<typeof tunnelBusinessEn> = {
  business: {
    title: "რა ჰქვია თქვენს ბიზნესს?",
    text: "შევქმნით ასისტენტს, რომელიც თქვენს კლიენტებს დღე და ღამე უპასუხებს.",
    name: "ბიზნესის სახელი",
    namePlaceholder: "მაგალითად, „კაფე რუსთაველზე“",
    kindTitle: "რას საქმიანობთ?",
    kindHint: "აირჩიეთ ყველაზე ახლო. ამაზეა დამოკიდებული, რას იკითხავს, რას დაჯავშნის და რა ეცოდინება ასისტენტს.",
    kindFixed: "ეს ასისტენტის შექმნისას აირჩიეთ და მისი შეცვლა აღარ შეიძლება.",
    legalReview: "ამ სახის ბიზნესისთვის ასისტენტის გაშვებამდე ტარდება მოკლე იურიდიული შემოწმება.",
    detailsTitle: "რას კითხულობენ კლიენტები ყოველთვის",
    errors: {
      name: "დაწერეთ ბიზნესის სახელი.",
      kind: "აირჩიეთ, რას საქმიანობს თქვენი ბიზნესი.",
    },
  },
  place: {
    title: "სად იმყოფებით?",
    text: "ქვეყანაზეა დამოკიდებული ვალუტა, დროის სარტყელი და თქვენი კლიენტების ენები. შევავსეთ ყველაფერი, რაც შევძელით.",
    country: "ქვეყანა",
    countryHint: "ფასები ვალუტაში: {currency}",
    countryFixed: "ასისტენტის შექმნის შემდეგ ქვეყნის შეცვლა აღარ შეიძლება.",
    city: "ქალაქი",
    cityPlaceholder: "მაგალითად, თბილისი",
    address: "მისამართი",
    addressPlaceholder: "ქუჩა და ნომერი",
    addressHint: "ასისტენტი კლიენტებს ეტყვის, როგორ მოგაგნონ.",
    addressOptional: "არასავალდებულო",
    languages: "რა ენებზე წერენ თქვენი კლიენტები",
    languagesHint: "ასისტენტი თითოეულ კლიენტს მის ენაზე პასუხობს, თუ ის ამ სიაშია.",
    defaultLanguage: "პირველი მისალმების ენა",
    timezone: "დროის სარტყელი",
    creating: "ვქმნით თქვენს ასისტენტს…",
    errors: {
      country: "აირჩიეთ ქვეყანა.",
      languages: "აირჩიეთ ერთი ენა მაინც.",
      address: "დაწერეთ მისამართი: მასზე მოგაგნებენ კლიენტები.",
      restricted: "ამ ქვეყნის ბიზნესის შექმნა ჯერ შეუძლებელია.",
    },
  },
};
