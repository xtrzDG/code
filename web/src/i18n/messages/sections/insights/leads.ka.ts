/** `leads.*` texts of leads (customer requests), in Georgian. */

import type { Translation } from "../../../translate";
import type { leadsEn } from "./leads.en";

export const leadsKa: Translation<typeof leadsEn> = {
  loading: "მოთხოვნები იტვირთება…",
  tabsLabel: "მოთხოვნის სტატუსი",
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
  statusOf: "მოთხოვნის სტატუსი, {name}",
  statusLabel: "სტატუსი",
  requestedDate: "თარიღი",
  partySize: "ადამიანი",
  budget: "ბიუჯეტი",
  source: "წყარო",
  received: "მიღებულია",
  details: "დეტალები",
  showDetails: "დეტალურად",
  contact: "კლიენტი",
  updated: "მოთხოვნის სტატუსი: „{status}“",
  emptyTitle: "მოთხოვნები ჯერ არ არის",
  emptyDescription: "როცა კლიენტი ითხოვს იმას, რასაც ასისტენტი თავად არ ჯავშნის (ბანკეტი, ჯგუფი, შეკვეთა), მოთხოვნა აქ მოდის მენეჯერისთვის.",
};
