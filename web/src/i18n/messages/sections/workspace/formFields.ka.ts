/** `formFields.*` texts in Georgian. */

import type { Translation } from "../../../translate";
import type { formFieldsEn } from "./formFields.en";

export const formFieldsKa: Translation<typeof formFieldsEn> = {
  time: {
    hours: "საათი",
    minutes: "წუთი",
    dayPeriod: "შუადღემდე ან შუადღის შემდეგ",
    empty: "არ არის მითითებული",
  },
  date: {
    placeholder: "აირჩიეთ თარიღი",
    open: "კალენდრის გახსნა",
    calendar: "კალენდარი",
    previousMonth: "წინა თვე",
    nextMonth: "შემდეგი თვე",
    today: "დღეს",
    clear: "გასუფთავება",
    date: "თარიღი",
    time: "დრო",
  },
  autosave: {
    hint: "ცვლილებები თავად ინახება.",
    saving: "ვინახავთ…",
    saved: "შენახულია",
    failed: "არ შეინახა",
    retry: "ხელახლა ცდა",
    retryLater: "არ შეინახა: კავშირი არ არის. ცოტა ხანში ისევ ვცდით.",
    stale: "სანამ არედაქტირებდით, ეს ველი სხვამ შეცვალა. ახლა მასში შენახული მნიშვნელობაა.",
    leaveWarning: "ცვლილება ჯერ კიდევ ინახება.",
  },
};
