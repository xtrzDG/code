/** `messageDelivery.*` in Georgian (typed against the English reference). */

import type { Translation } from "../../../translate";
import type { messageDeliveryEn } from "./messageDelivery.en";

export const messageDeliveryKa: Translation<typeof messageDeliveryEn> = {
  label: "მიწოდება",
  states: {
    sending: "იგზავნება…",
    retrying: "ჯერ არ მიწოდებულა, ვცდით ხელახლა",
    delivered: "მიწოდებულია",
    failed: "ვერ მიეწოდა",
  },
  nextAttempt: "შემდეგი ცდა {time}-ზე",
  reasons: {
    rate_limited: "მესენჯერმა ლოდინი გვთხოვა",
    provider_unavailable: "მესენჯერმა არ უპასუხა",
    recipient_refused: "მესენჯერმა არ მიიღო (კლიენტმა შეიძლება ბიზნესი დაბლოკა, ან 24-საათიანი ფანჯარა დაიხურა)",
    template_rejected: "WhatsApp-მა შეტყობინების შაბლონი არ მიიღო",
    channel_disconnected: "არხი აღარ არის დაკავშირებული",
    credential_rejected: "არხის წვდომამ შეწყვიტა მუშაობა: ხელახლა დააკავშირეთ „არხებში“",
    not_configured: "ამ შეტყობინების გაგზავნა ვერაფრით ხერხდება",
    expired: "მისი დრო გავიდა, სანამ გაიგზავნებოდა",
  },
};
