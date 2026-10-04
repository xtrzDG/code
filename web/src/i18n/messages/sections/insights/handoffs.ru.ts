/** `handoffs.*` texts of "Needs a person", in Russian (wording: docs/glossary.md). */

import type { Translation } from "../../../translate";
import type { handoffsEn } from "./handoffs.en";

export const handoffsRu: Translation<typeof handoffsEn> = {
  loading: "Загружаем…",
  tabsLabel: "Показать",
  tabs: {
    open: "Ждут",
    resolved: "Решённые",
    all: "Все",
  },
  urgency: {
    critical: "Критично",
    high: "Срочно",
    normal: "Обычно",
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
    profile_rule: "Одно из ваших правил",
    unverified_numbers: "Неподтверждённые цены или цифры",
  },
  status: {
    pending: "Уведомляем сотрудников",
    notified: "Сотрудники уведомлены",
    notification_failed: "Уведомление не дошло",
    resolved: "Решено",
  },
  notificationFailedHint: "Сотрудники не получили уведомление. Перезвоните клиенту и проверьте контакты в настройках.",
  resolvedAt: "Решено {date}",
  resolve: "Решено",
  confirmResolve: {
    title: "Отметить как решённое?",
    description: "{name}: помощник снова начнёт отвечать этому клиенту.",
    confirm: "Решено",
  },
  resolved: "Отмечено как решённое",
  emptyOpenTitle: "Сейчас никто не ждёт человека",
  emptyOpenDescription: "Когда помощник передаёт разговор человеку, разговор ждёт здесь с кратким пересказом.",
  emptyTitle: "Здесь пока пусто",
  summaryCodes: {
    model_declined: "Помощник не стал отвечать на это сообщение.",
    model_unavailable: "Помощник был временно недоступен и не смог ответить.",
    answer_unfinished: "Помощник не смог закончить ответ.",
    unverified_values: "Помощник не отправил ответ: в нём были цифры или утверждения, которых нет в данных бизнеса.",
    call_booking_unverified_values:
      "Во время звонка помощник назвал цифры, которых нет в данных бизнеса. Сверьте бронь из этого звонка с расшифровкой.",
    call_request_unverified_values:
      "Во время звонка помощник назвал цифры, которых нет в данных бизнеса. Сверьте заявку из этого звонка с расшифровкой.",
    reply_undelivered: "Ответ помощника не дошёл до клиента. Свяжитесь с ним другим способом.",
    data_erased: "Данные удалены по просьбе клиента.",
  },
  summaryCodesWithValues: {
    unverified_values: "Помощник не отправил ответ: в нём были цифры или утверждения, которых нет в данных бизнеса ({values}).",
    call_booking_unverified_values:
      "Во время звонка помощник назвал цифры, которых нет в данных бизнеса ({values}). Сверьте бронь из этого звонка с расшифровкой.",
    call_request_unverified_values:
      "Во время звонка помощник назвал цифры, которых нет в данных бизнеса ({values}). Сверьте заявку из этого звонка с расшифровкой.",
  },
  quote: {
    customer: "Сообщение клиента",
    reply: "Ответ, который не дошёл",
  },
};
