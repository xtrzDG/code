/** `knowledge.offer.*` texts of bookable offers, in Georgian. */

import type { Translation } from "../../../translate";
import type { knowledgeOfferEn } from "./knowledgeOffer.en";

export const knowledgeOfferKa: Translation<typeof knowledgeOfferEn> = {
  offer: {
    nightlyPrice: "ღამის ფასი, {currency}",
    nightlyPriceHint: "ამდენი ღირს ღამე ყველა სეზონის გარეთ. დატოვეთ ცარიელი, თუ ფასი რამეზეა დამოკიდებული.",
    durationHint: "5-დან 720 წუთამდე: ჯავშანი ამდენ ხანს გრძელდება.",
    buffer: "შესვენება შემდეგ, წთ",
    bufferHint: "შემსრულებელი ამდენ ხანს დაკავებულია მომსახურების შემდეგ (დალაგება, მომზადება).",
    performers: "ვინ ასრულებს",
    performersHint: "ჩაწერა მხოლოდ მათთან მოხდება. თუ არავინაა მონიშნული — ნებისმიერთან, ვინც კონკრეტულ სერვისებზე არ არის მიბმული.",
    rooms: "ამ ტიპის ნომრები",
    roomsHint: "ამ ტიპის დარჩენა ერთ-ერთ ამ ნომერში იჯავშნება. თუ არცერთია მონიშნული — ნებისმიერ ნომერში, რომელიც ღამეებით იჯავშნება.",
    noResources: "ასარჩევი ჯერ არავინაა: ჯერ დაამატეთ თანამშრომლები ან ადგილები, რომლებიც დროით იჯავშნება.",
    noRooms: "ღამეებით დასაჯავშნი ნომრები ჯერ არ არის: ჯერ დაამატეთ ისინი.",
    toResources: "გადასვლა: „რესურსები და საათები“",
    resourceOff: "გამორთულია",
    filter: "ძებნა სახელით",
    noMatches: "„{query}“-ით ვერავინ მოიძებნა",
    selectedCount: { one: "არჩეულია {count}", other: "არჩეულია {count}" },
    seasons: "სეზონური ფასები",
    seasonsHint: "სეზონის შიგნით ღამე ამ სეზონის ფასი ღირს, ყოველ წელს. სეზონი შეიძლება ახალ წელზე გადადიოდეს; სეზონები ერთმანეთს არ უნდა ფარავდეს.",
    addSeason: "სეზონის დამატება",
    seasonTitle: "სეზონი {number}",
    seasonName: "სახელი",
    seasonNamePlaceholder: "მაგალითად: ზაფხული",
    from: "დან",
    to: "მდე",
    day: "დღე",
    month: "თვე",
    seasonRate: "ღამეში, {currency}",
    removeSeason: "სეზონი {number}-ის წაშლა",
    noSeasons: "სეზონები არ არის: ყოველი ღამე ჩვეულებრივი ღამის ფასი ღირს.",
    performedBy: "ასრულებს: {names}",
    roomsList: "ნომრები: {names}",
    breakValue: "+{count} წთ შესვენება",
    perNight: "{price} ღამეში",
    seasonsValue: { one: "{count} სეზონი", other: "{count} სეზონი" },
    errors: {
      bufferRange: "0-დან 240 წუთამდე",
      seasonDate: "ამ თვეში ასეთი დღე არ არის",
      seasonOverlap: "სეზონებს {first} და {second} საერთო დღეები აქვთ: ღამეს ერთი ფასი უნდა ჰქონდეს.",
      tooManySeasons: { one: "მაქსიმუმ {count} სეზონი", other: "მაქსიმუმ {count} სეზონი" },
    },
  },
};
