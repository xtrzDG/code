/** `overviewPhone.*` in Italian (a draft awaiting a native speaker's review). */

import type { Translation } from "../../../translate";
import type { overviewPhoneEn } from "./overviewPhone.en";

export const overviewPhoneIt: Translation<typeof overviewPhoneEn> = {
  today: {
    title: "Oggi",
    staffHint: "Le tue conversazioni, i clienti in attesa e le prenotazioni di oggi",
  },
  folds: {
    statistics: "Statistiche",
    summary: "{label}: {value}",
  },
};
