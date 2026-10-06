/** `channelPages.*` texts of the Channels pages on a phone, in Georgian. */

import type { Translation } from "../../../translate";
import type { channelPagesEn } from "./channelPages.en";

export const channelPagesKa: Translation<typeof channelPagesEn> = {
  heading: "მორგება",
  back: "ყველა არხი",
  website: {
    title: "ჩატი საიტზე",
    hint: "ფერი, ღილაკი, კოდი საიტისთვის და სად შეიძლება მისი ჩვენება",
  },
  calls: {
    title: "ზარების გადამისამართება",
    hint: "კოდები, რომლებიც გამოტოვებულ ზარებს ასისტენტზე გადაამისამართებს",
  },
  share: {
    title: "გაზიარება",
    hint: "ბმულები, QR-კოდი და მაგიდის ბარათი",
  },
  off: {
    website: "საიტის ჩატი გამორთულია. ჩართეთ ის არხებში, რომ აირჩიოთ მისი იერსახე და დადოთ საიტზე.",
    calls: "ტელეფონი არ არის დაკავშირებული. დააკავშირეთ ის არხებში, რომ მიიღოთ გადამისამართების კოდები.",
  },
};
