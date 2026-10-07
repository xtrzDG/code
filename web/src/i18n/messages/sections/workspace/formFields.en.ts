/**
 * `formFields.*` texts of the UI kit's date and time fields and of the
 * settings forms that save themselves, in English: the reference that ru
 * and ka are typed against.
 */

export const formFieldsEn = {
  time: {
    hours: "Hours",
    minutes: "Minutes",
    dayPeriod: "AM or PM",
    empty: "Not set",
  },
  date: {
    placeholder: "Choose a date",
    open: "Open the calendar",
    calendar: "Calendar",
    previousMonth: "Previous month",
    nextMonth: "Next month",
    today: "Today",
    clear: "Clear",
    date: "Date",
    time: "Time",
  },
  autosave: {
    hint: "Changes save themselves.",
    saving: "Saving…",
    saved: "Saved",
    failed: "Not saved",
    retry: "Try again",
  },
} as const;
