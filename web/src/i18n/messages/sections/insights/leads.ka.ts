/** `leads.*` texts of leads (customer requests), in Georgian. */

import type { Translation } from "../../../translate";
import type { leadsEn } from "./leads.en";

export const leadsKa: Translation<typeof leadsEn> = {
  loading: "მოთხოვნები იტვირთება…",
  status: {
    new: "ახალი",
    in_progress: "მუშავდება",
    won: "წარმატებული",
    lost: "უარი",
  },
  type: {
    banquet: "ბანკეტი",
    group: "ჯგუფი",
    corporate: "კორპორატიული ღონისძიება",
    order: "შეკვეთა",
    viewing: "დათვალიერება",
    otherRequest: "სხვა მოთხოვნა",
  },
  updated: "მოთხოვნის სტატუსი: „{status}“",
};
