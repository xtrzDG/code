/** `leads.*` in Hebrew (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { leadsEn } from "./leads.en";

export const leadsHe: Translation<typeof leadsEn> = {
  loading: "טוענים פניות…",
  status: {
    new: "חדשה",
    in_progress: "בטיפול",
    won: "נסגרה בהצלחה",
    lost: "אבדה",
  },
  type: {
    banquet: "אירוע",
    group: "קבוצה",
    corporate: "אירוע חברה",
    order: "הזמנה",
    viewing: "צפייה בנכס",
    otherRequest: "פנייה אחרת",
  },
  updated: "הפנייה הועברה ל„{status}”",
};
