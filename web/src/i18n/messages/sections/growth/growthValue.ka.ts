/** `growthValue.*` ქართულად: ჯავშნები მოლოდინის სიიდან და განმეორებით ვიზიტზე შეტყობინებების შემდეგ. */

import type { Translation } from "../../../translate";
import type { growthValueEn } from "./growthValue.en";

export const growthValueKa: Translation<typeof growthValueEn> = {
  label: "ჯავშნები, რომლებიც ასისტენტმა დააბრუნა",
  waitlist: { one: "{count} მოლოდინის სიიდან", other: "{count} მოლოდინის სიიდან" },
  campaign: {
    one: "{count} განმეორებით ვიზიტზე შეტყობინების შემდეგ",
    other: "{count} განმეორებით ვიზიტზე შეტყობინებების შემდეგ",
  },
  worth: "≈ {money}",
  waitlistHint: "გათავისუფლებული ადგილები, რომლებიც მომლოდინე კლიენტებმა დაიკავეს.",
  campaignHint: "კლიენტები, რომლებმაც შეტყობინების შემდეგ ხელახლა დაჯავშნეს.",
  rows: {
    waitlistBookings: "ჯავშნები მოლოდინის სიიდან",
    waitlistValue: "მოლოდინის სიიდან ჯავშნების ღირებულება",
    campaignBookings: "ჯავშნები განმეორებით ვიზიტზე შეტყობინებების შემდეგ",
    campaignValue: "განმეორებით ვიზიტზე შეტყობინებების შემდეგ ჯავშნების ღირებულება",
  },
};
