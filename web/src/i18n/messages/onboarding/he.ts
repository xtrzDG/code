import type { Translation } from "../../translate";
import type { onboardingEn } from "./en";
import { profileEditHe } from "./profileEdit.he";

/** Texts of the business profile in Hebrew (a draft awaiting native review). Keys as in en.ts. */
export const onboardingHe: Translation<typeof onboardingEn> = {
  onboarding: {
    choose: "בחרו…",
    gaps: {
      times: { one: "פעם אחת", two: "פעמיים", other: "{count} פעמים" },
      notReady: { one: "חסר פריט חובה אחד", two: "חסרים שני פריטי חובה", other: "חסרים {count} פריטי חובה" },
    },
    week: {
      closed: "סגור",
      opens: "נפתח",
      closes: "נסגר",
      addInterval: "הוספת הפסקה או משמרת שנייה",
      removeInterval: "הסרת מרווח הזמן",
      overnight: "עד {time} למחרת",
      roundTheClock: "פתוח 24 שעות",
      copyToAll: "העתקת יום שני לכל הימים",
    },
    offer: {
      kinds: {
        faq: "שאלה ותשובה",
        policy: "כלל",
        menu_item: "פריט בתפריט",
        service: "שירות",
        room_type: "סוג חדר",
        package: "חבילה",
        vehicle: "רכב",
        product: "מוצר",
      },
    },
    booking: {
      noBookings: "התחום שלכם לא מקבל הזמנות: העוזר אוסף פניות ומעביר אותן למנהל.",
      resourceKinds: {
        table: "שולחן",
        room: "חדר",
        staff: "מומחה",
        arena: "מגרש או אולם",
        bay: "עמדת שירות",
        vehicle: "רכב",
        slot: "משבצת זמן",
      },
    },
    resources: {
      namePlaceholder: "לדוגמה: מגרש 1",
    },
  },
  profileEdit: profileEditHe,
};
