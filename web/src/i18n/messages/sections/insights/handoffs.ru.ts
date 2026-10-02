/** `handoffs.*` texts of handoffs to a person, in Russian. */

import type { Translation } from "../../../translate";
import type { handoffsEn } from "./handoffs.en";

export const handoffsRu: Translation<typeof handoffsEn> = {
  loading: "Загружаем передачи…",
  tabsLabel: "Статус передачи",
  tabs: {
    open: "Открытые",
    resolved: "Закрытые",
    all: "Все",
  },
  urgency: {
    critical: "Критично",
    high: "Срочно",
    normal: "Обычная",
    low: "Не срочно",
  },
  reason: {
    customer_request: "Попросили человека",
    complaint: "Жалоба",
    vip_guest: "VIP-гость",
    non_standard_request: "Нестандартный запрос",
    unknown_answer: "Помощник не знал ответа",
    emergency: "Экстренный случай",
    sensitive_topic: "Деликатная тема",
    profile_rule: "Ваше правило передачи",
    unverified_numbers: "Непроверенные цены или цифры",
  },
  status: {
    pending: "Уведомляем сотрудников",
    notified: "Сотрудники уведомлены",
    notification_failed: "Уведомление не дошло",
    resolved: "Закрыта",
  },
  notificationFailedHint: "Сотрудники не получили уведомление. Перезвоните клиенту и проверьте контакты в настройках.",
  resolvedAt: "Закрыта {date}",
  resolve: "Закрыть",
  confirmResolve: {
    title: "Закрыть передачу?",
    description: "{name}: помощник снова начнёт отвечать этому клиенту.",
    confirm: "Закрыть",
  },
  resolved: "Передача закрыта",
  emptyOpenTitle: "Открытых передач нет",
  emptyOpenDescription: "Когда помощник передаёт разговор человеку, разговор ждёт здесь с кратким пересказом.",
  emptyTitle: "Передач пока нет",
};
