/** `leads.*` texts of leads (customer requests), in Russian. */

import type { Translation } from "../../../translate";
import type { leadsEn } from "./leads.en";

export const leadsRu: Translation<typeof leadsEn> = {
  loading: "Загружаем заявки…",
  tabsLabel: "Статус заявки",
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
  statusOf: "Статус заявки от {name}",
  statusLabel: "Статус",
  requestedDate: "Дата",
  partySize: "Людей",
  budget: "Бюджет",
  source: "Источник",
  received: "Получена",
  details: "Подробности",
  showDetails: "Подробнее",
  contact: "Клиент",
  updated: "Заявка переведена в статус «{status}»",
  emptyTitle: "Заявок пока нет",
  emptyDescription: "Когда клиент просит то, что помощник сам не бронирует (банкет, группу, заказ), заявка приходит сюда для менеджера.",
};
