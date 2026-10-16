/** `conversationMedia.*` in Georgian (typed against the English reference). */

import type { Translation } from "../../../translate";
import type { conversationMediaEn } from "./conversationMedia.en";

export const conversationMediaKa: Translation<typeof conversationMediaEn> = {
  label: "დანართები",
  kinds: {
    audio: "ხმოვანი შეტყობინება",
    image: "ფოტო",
    location: "მდებარეობა",
    contact: "კონტაქტი",
    sticker: "სტიკერი",
    file: "ფაილი",
  },
  voice: {
    transcript: "ტრანსკრიფცია",
    play: "მოსმენა",
    playLabel: "ხმოვანი შეტყობინების მოსმენა",
    playerLabel: "კლიენტის ხმოვანი შეტყობინება",
    playerUnsupported: "თქვენი ბრაუზერი აქ აუდიოს ვერ უკრავს.",
    loading: "იტვირთება…",
    missing: "ეს ხმოვანი შეტყობინება აღარ არის ხელმისაწვდომი: ის წაიშალა შენახვის ვადის გასვლის შემდეგ ან კლიენტის მონაცემებთან ერთად.",
    error: "ხმოვანი შეტყობინების ჩატვირთვა ვერ მოხერხდა. სცადეთ ერთ წუთში.",
    retry: "ხელახლა ცდა",
  },
  photo: {
    alt: "კლიენტის გამოგზავნილი ფოტო",
    altWithCaption: "კლიენტის გამოგზავნილი ფოტო: {caption}",
    open: "ფოტოს გახსნა",
    viewerTitle: "ფოტო კლიენტისგან",
    unavailable: "ფოტოს ჩვენება ვერ მოხერხდა: ის წაიშალა ან თქვენი სესია დასრულდა.",
  },
  place: {
    openMap: "რუკაზე გახსნა",
    openMapLabel: "{place} რუკაზე გახსნა (ახალ ჩანართში)",
    unnamed: "გაზიარებული მდებარეობა",
  },
  deleted: "ფაილი წაიშალა შენახვის ვადის გასვლის შემდეგ.",
  problems: {
    unsupported_kind: "ასისტენტი ამას ვერ კითხულობს და კლიენტს სთხოვა, ტექსტით მოწეროს.",
    too_large: "ფაილი ძალიან დიდია: კლიენტს სთხოვეს, ტექსტით მოწეროს.",
    too_long: "ამოსაცნობად ძალიან გრძელია: კლიენტს სთხოვეს, ტექსტით მოწეროს.",
    unavailable: "მესენჯერი ამ ფაილს აღარ გასცემს: კლიენტს სთხოვეს, ტექსტით მოწეროს.",
    unrecognized_format: "ფორმატი, რომელსაც ასისტენტი ვერ კითხულობს: კლიენტს სთხოვეს, ტექსტით მოწეროს.",
    not_understood: "სიტყვების გარჩევა ვერ მოხერხდა: კლიენტს სთხოვეს, ტექსტით მოწეროს.",
  },
};
