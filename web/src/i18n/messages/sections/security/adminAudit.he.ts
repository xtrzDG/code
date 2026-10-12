/** `adminAudit.*` בעברית: דף "ביקורת" של מנהל הפלטפורמה. */

import type { Translation } from "../../../translate";
import type { adminAuditEn } from "./adminAudit.en";

export const adminAuditHe: Translation<typeof adminAuditEn> = {
  nav: "ביקורת",
  title: "ביקורת",
  description: "הבדיקה היומית של כל יומני הפעולות לשינויים, ויומן הפלטפורמה עצמה: כניסות שנכשלו, נעילות, יציאות והחלפות מפתחות.",
  chains: {
    title: "בדיקת שינויים",
    platform: "יומן הפלטפורמה",
    intact: "יומנים שלמים",
    broken: "יומנים ששונו",
    allIntact: "הבדיקות האחרונות מצאו את היומן של כל עסק כפי שנרשם.",
    brokenList: "יומנים שנמצאו משונים",
    business: "עסק",
    entry: "רשומה",
    problem: "הבעיה",
    checked: "נבדק",
    platformName: "פלטפורמה",
  },
  log: {
    title: "יומן הפלטפורמה",
    description: "רשומות שאינן שייכות לעסק, החדשות קודם. הכתובת שאליה נשלח קוד הכניסה מוצגת רק כטביעת אצבע מבוססת מפתח, לעולם לא הכתובת עצמה.",
    filters: "סינון יומן הפלטפורמה",
    event: "אירוע",
    allEvents: "כל האירועים",
    when: "מתי",
    what: "מה",
    who: "מי",
    address: "כתובת רשת",
    entry: "רשומה",
    empty: "עדיין אין רשומות",
    emptyFiltered: "אין רשומות לאירוע הזה",
    unknownPerson: "אדם לא ידוע",
    system: "מערכת",
  },
  events: {
    login_failed: "קוד שגוי",
    otp_locked: "הקוד ננעל",
    mfa_locked: "השלב השני ננעל",
    logout: "יציאה",
    key_rotation: "החלפת מפתח",
  },
  entities: {
    login_destination: "כתובת כניסה",
    user: "אדם",
    user_session: "הפעלה",
    encryption_keys: "מפתחות הצפנה",
    audit_log_entry: "רשומות ביקורת",
  },
};
