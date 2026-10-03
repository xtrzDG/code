/** `tunnelOffer.*`: what the business offers, its hours and bookings, in Georgian. */

import type { Translation } from "../../../translate";
import type { tunnelOfferEn } from "./tunnelOffer.en";

export const tunnelOfferKa: Translation<typeof tunnelOfferEn> = {
  offer: {
    title: "რას სთავაზობთ?",
    text: "დაამატეთ, რასაც ყიდით, ფასებით. ასისტენტი მხოლოდ აქ მოცემულ ფასებს ასახელებს.",
    sourcesLabel: "როგორ დავამატოთ",
    sources: {
      type: "თავად ჩაწერა",
      website: "თქვენი ვებსაიტიდან",
      menu: "მენიუს ფოტოდან ან ფაილიდან",
    },
    tableLabel: "თქვენი შეთავაზება",
    name: "დასახელება",
    namePlaceholder: "რისი შეკვეთა ან დაჯავშნა შეუძლიათ კლიენტებს",
    price: "ფასი, {currency}",
    pricePlaceholder: "0",
    suggestion: "მაგალითი",
    suggestionsHint: "მაგალითები მხოლოდ მაშინ შეინახება, როცა ფასს მიუთითებთ. წაშალეთ ის, რაც არ გაქვთ.",
    addRow: "სტრიქონის დამატება",
    removeRow: "„{name}“-ის წაშლა",
    removeEmpty: "ამ სტრიქონის წაშლა",
    rowSaving: "ინახება…",
    rowSaved: "შენახულია",
    rowFailed: "არ შეინახა",
    priced: {
      one: "{count} პოზიცია ფასით",
      other: "{count} პოზიცია ფასით",
    },
    importedTitle: {
      one: "იმპორტიდან დაემატა {count} პოზიცია",
      other: "იმპორტიდან დაემატა {count} პოზიცია",
    },
    importHint: "წავიკითხავთ და გაჩვენებთ, რა ვიპოვეთ. სანამ არ შეამოწმებთ, არაფერი შეინახება.",
  },
  hours: {
    title: "როდის მუშაობთ?",
    text: "შემოგთავაზეთ ჩვეულებრივი საათები თქვენი სახის ბიზნესისთვის. შეცვალეთ, რაც თქვენთან სხვაგვარადაა.",
    hoursLabel: "სამუშაო საათები",
    bookingsTitle: "როგორ მუშაობს ჯავშნები?",
    slot: "ვიზიტი გრძელდება",
    partySize: "მაქსიმუმ რამდენი ადამიანი ერთ ჯავშანში",
    notice: "დაჯავშნა არაუგვიანეს",
    noticeNone: "ნებისმიერ დროს",
    cancellation: "გაუქმების წესი",
    cancellationHint: "კლიენტები მას დაჯავშნისას ან გაუქმებისას გაიგებენ.",
    resourceTitle: "რას ჯავშნიან კლიენტები",
    resourceHint: "მეტის დამატება მოგვიანებით შეგიძლიათ: ასისტენტი → ცოდნა.",
    resourceName: "დასახელება",
    resourceCount: "რამდენია",
    resourceCapacity: "ადამიანი თითოეულში",
    minutes: {
      one: "{count} წუთი",
      other: "{count} წუთი",
    },
    hoursCount: {
      one: "{count} საათი",
      other: "{count} საათი",
    },
    noticeHours: {
      one: "{count} საათით ადრე",
      other: "{count} საათით ადრე",
    },
    noticeDays: {
      one: "{count} დღით ადრე",
      other: "{count} დღით ადრე",
    },
    noticeMinutes: {
      one: "{count} წუთით ადრე",
      other: "{count} წუთით ადრე",
    },
    errors: {
      noHours: "მონიშნეთ ერთი სამუშაო დღე მაინც.",
      partySize: "დაწერეთ მთელი რიცხვი 1-დან.",
      resourceName: "დაასახელეთ, რას ჯავშნიან კლიენტები.",
      capacity: "დაწერეთ მთელი რიცხვი 1-დან.",
      unitCount: "დაწერეთ მთელი რიცხვი 1-დან.",
    },
  },
};
