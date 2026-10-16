/** `overviewPhone.*` in German (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { overviewPhoneEn } from "./overviewPhone.en";

export const overviewPhoneDe: Translation<typeof overviewPhoneEn> = {
  today: {
    title: "Heute",
    staffHint: "Ihre Gespräche, wartende Kunden und die heutigen Buchungen",
  },
  folds: {
    statistics: "Statistik",
    summary: "{label}: {value}",
  },
};
