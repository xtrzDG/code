/** `overviewPhone.*` texts of the Overview on a phone, in Georgian. */

import type { Translation } from "../../../translate";
import type { overviewPhoneEn } from "./overviewPhone.en";

export const overviewPhoneKa: Translation<typeof overviewPhoneEn> = {
  today: {
    title: "დღეს",
    staffHint: "თქვენი საუბრები, მომლოდინე კლიენტები და დღევანდელი ჯავშნები",
  },
  folds: {
    statistics: "სტატისტიკა",
    summary: "{label}: {value}",
  },
};
