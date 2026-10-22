/** `billingCard.*` texts of Settings → Billing: the card on file, the retries of a declined payment and the trial's "Save card" prompt, in Georgian. */

import type { Translation } from "../../../translate";
import type { billingCardEn } from "./billingCard.en";

export const billingCardKa: Translation<typeof billingCardEn> = {
  title: "გადახდის ბარათი",
  description: "გამოწერის ავტომატური გადახდები ამ ბარათიდან ჩამოიჭრება.",
  endingIn: "ბარათი, რომელიც მთავრდება {digits}-ით",
  expires: "მოქმედებს {date}-მდე",
  noExpiry: "მოქმედების ვადა უცნობია",
  expiryStates: {
    expired: "ვადაგასულია",
    expiring: "ვადა მალე იწურება",
  },
  facts: {
    provider: "გადახდის სერვისი",
    savedAt: "შენახულია",
  },
  noCard: "ბარათი ჯერ არ არის შენახული",
  noCardTrial: "შეინახეთ ბარათი და საცდელი პერიოდის დასრულების შემდეგ გამოწერა თავისით გაგრძელდება.",
  noCardPaid: "შეინახეთ ბარათი, რომ შემდეგი გადახდები თავისით გავიდეს.",
  cardWithoutDetails: "ბარათი შენახულია {provider}-ში. მისი მონაცემები აქ შემდეგი გადახდის შემდეგ გამოჩნდება.",
  expiredHint: "ამ ბარათს ვადა გაუვიდა. შემდეგ გადახდამდე შეინახეთ ახალი.",
  expiringHint: "ამ ბარათს ვადა მალე გასდის. შეინახეთ ახალი, რომ შემდეგი გადახდა გავიდეს.",
  noCharge: "ბარათის შენახვისას არაფერი ჩამოიჭრება: გადახდის სერვისი მას მხოლოდ ამოწმებს.",
  payToSave: "ღია ანგარიშის გადახდა ინახავს ბარათს, რომლითაც იხდით.",
  save: "ბარათის შენახვა",
  update: "ბარათის განახლება",
  opening: "იხსნება…",
  retry: {
    title: "ავტომატური გადახდა ვერ შესრულდა",
    declined: "ბარათმა გადახდა უარყო. ჩვენ თავად ვცდით ხელახლა.",
    outcomes: {
      claimed: "მცდელობა {attempt} / {total} მიმდინარეობს.",
      approved: "მცდელობა {attempt} / {total} წარმატებით შესრულდა. გადახდა დასტურდება.",
      declined: "მცდელობა {attempt} / {total} უარყოფილია.",
      processing: "მცდელობა {attempt} / {total} მუშავდება.",
      failed: "მცდელობა {attempt} / {total} ვერ მივიდა გადახდის სერვისამდე.",
      not_possible: "მცდელობა {attempt} / {total} შეუძლებელია: შენახული ბარათი არ არის.",
      skipped: "მცდელობა {attempt} / {total} გამოტოვებულია.",
    },
    next: "შემდეგი მცდელობა: {date}",
    noMore: "მეტი მცდელობა აღარ იქნება. {date}-დან ასისტენტი მხოლოდ იღებს მოთხოვნებს.",
  },
  trialPrompt: {
    title: { one: "საცდელ პერიოდს დარჩა {count} დღე", other: "საცდელ პერიოდს დარჩა {count} დღე" },
    body: "{date}-მდე არაფერი ჩამოიჭრება: შეინახეთ ბარათი ახლა და ასისტენტი საცდელი პერიოდის შემდეგაც გააგრძელებს პასუხებს.",
  },
  returned: {
    title: "ბარათს ვინახავთ",
    pending: "ბარათი აქ გამოჩნდება, როგორც კი გადახდის სერვისი დაადასტურებს, ჩვეულებრივ ერთ წუთში.",
    savedTitle: "ბარათი შენახულია",
    saved: "ავტომატური გადახდები ახლა ამ ბარათიდან ჩამოიჭრება.",
  },
  errors: {
    cannotSave: "ახლა ბარათის შენახვა შეუძლებელია. გადაიხადეთ ღია ანგარიში: ეს შეინახავს ბარათს, რომლითაც იხდით.",
  },
};
