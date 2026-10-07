/** `leads.*` texts of leads (customer requests), in Russian. */

import type { Translation } from "../../../translate";
import type { leadsEn } from "./leads.en";

export const leadsRu: Translation<typeof leadsEn> = {
  loading: "Загружаем заявки…",
  status: {
    new: "Новая",
    in_progress: "В работе",
    won: "Успешная",
    lost: "Отказ",
  },
  type: {
    banquet: "Банкет",
    group: "Группа",
    corporate: "Корпоратив",
    order: "Заказ",
    viewing: "Просмотр",
    otherRequest: "Другая заявка",
  },
  updated: "Заявка переведена в статус «{status}»",
};
