/** `overviewPhone.*` texts of the Overview on a phone, in Russian. */

import type { Translation } from "../../../translate";
import type { overviewPhoneEn } from "./overviewPhone.en";

export const overviewPhoneRu: Translation<typeof overviewPhoneEn> = {
  today: {
    title: "Сегодня",
    staffHint: "Ваши разговоры, клиенты, которые ждут, и брони на сегодня",
  },
  folds: {
    statistics: "Статистика",
    summary: "{label}: {value}",
  },
};
