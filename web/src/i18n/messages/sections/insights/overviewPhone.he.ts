/** `overviewPhone.*` in Hebrew (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { overviewPhoneEn } from "./overviewPhone.en";

export const overviewPhoneHe: Translation<typeof overviewPhoneEn> = {
  today: {
    title: "היום",
    staffHint: "השיחות שלכם, לקוחות שממתינים וההזמנות של היום",
  },
  folds: {
    statistics: "סטטיסטיקה",
    summary: "{label}: {value}",
  },
};
