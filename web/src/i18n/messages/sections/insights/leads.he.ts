/** `leads.*` in Hebrew (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { leadsEn } from "./leads.en";

export const leadsHe: Translation<typeof leadsEn> = {
  loading: "טוענים פניות…",
  tabsLabel: "סטטוס הפנייה",
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
  statusOf: "הסטטוס של הפנייה מ-{name}",
  statusLabel: "סטטוס",
  requestedDate: "תאריך",
  partySize: "אנשים",
  budget: "תקציב",
  source: "מקור",
  received: "התקבלה",
  details: "פרטים",
  showDetails: "פרטים",
  contact: "לקוח",
  updated: "הפנייה הועברה ל„{status}”",
  emptyTitle: "עדיין אין פניות",
  emptyDescription: "כשלקוח מבקש משהו שהעוזר לא מזמין בעצמו (אירוע, קבוצה, הזמנה), הבקשה מגיעה לכאן עבור המנהל.",
};
