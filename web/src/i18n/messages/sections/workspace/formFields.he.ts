/** `formFields.*` in Hebrew (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { formFieldsEn } from "./formFields.en";

export const formFieldsHe: Translation<typeof formFieldsEn> = {
  time: {
    hours: "שעות",
    minutes: "דקות",
    dayPeriod: "לפני או אחרי הצהריים",
    empty: "לא נקבע",
  },
  date: {
    placeholder: "בחרו תאריך",
    open: "פתיחת לוח השנה",
    calendar: "לוח שנה",
    previousMonth: "החודש הקודם",
    nextMonth: "החודש הבא",
    today: "היום",
    clear: "ניקוי",
    date: "תאריך",
    time: "שעה",
  },
  autosave: {
    hint: "השינויים נשמרים מעצמם.",
    saving: "שומרים…",
    saved: "נשמר",
    failed: "לא נשמר",
    retry: "לנסות שוב",
  },
};
