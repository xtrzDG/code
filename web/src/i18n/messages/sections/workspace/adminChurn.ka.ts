/** `adminChurn.*` texts of the platform admin's Metrics page, in Georgian. */

import type { Translation } from "../../../translate";
import type { adminChurnEn } from "./adminChurn.en";

export const adminChurnKa: Translation<typeof adminChurnEn> = {
  title: "რატომ მიდიან მფლობელები",
  description:
    "პერიოდის გაუქმებები მფლობელის მიერ არჩეული მიზეზით, გაუქმების ნაცვლად მიღებული შეთავაზებები, სეზონური პაუზები და შეტყობინებები გაუქმებიდან 14 და 30 დღეში.",
  empty: "ამ პერიოდში გაუქმებები, შეთავაზებები და პაუზები არ ყოფილა.",
  stats: {
    cancellations: "გააუქმეს",
    saved: "დარჩნენ შეთავაზებით",
    pausesScheduled: "დაგეგმილი პაუზები",
    pausesEnded: "დასრულებული პაუზები",
    winBackSent: "დაბრუნების შეტყობინებები",
    returned: "დაბრუნდნენ მის შემდეგ",
  },
  reason: "მიზეზი",
  cancelled: "გააუქმეს",
  tookOffer: "მიიღეს შეთავაზება",
  noReason: "არ უკითხავთ (კითხვამდე)",
  offersTitle: "მიღებული შეთავაზებები",
  commentsTitle: "მფლობელების სიტყვებით",
  openClient: "კლიენტის გახსნა",
};
