/**
 * `insights.*` texts of shared by the dashboard, conversations, bookings,
 * leads and handoffs, in Russian.
 */

import type { Translation } from "../../../translate";
import type { insightsCommonEn } from "./common.en";

export const insightsCommonRu: Translation<typeof insightsCommonEn> = {
  loadingMore: "Загрузка…",
  showMore: "Показать ещё",
  includeTest: "Показывать тестовые",
  includeTestHint: "Из тестового чата и проверок",
  testBadge: "Тест",
  afterHours: "Вне рабочего времени",
  unknownCustomer: "Клиент без имени",
  callPhone: "Позвонить {phone}",
  openConversation: "Открыть разговор",
  noMatchesTitle: "Под фильтры ничего не подходит",
  noMatchesDescription: "Измените или сбросьте фильтры, чтобы увидеть больше.",
  copy: "Скопировать",
  copied: "Скопировано",
  copyFailed: "Не удалось скопировать. Выделите текст и скопируйте вручную.",
  customerMessage: {
    title: "Сообщение для клиента",
    description: "Отсюда помощник сам этот текст не отправляет. Перешлите его клиенту в том канале, где вы общаетесь.",
  },
  channels: {
    phone: "Телефон",
    whatsapp: "WhatsApp",
    instagram: "Instagram",
    messenger: "Messenger",
    telegram: "Telegram",
    web_chat: "Чат на сайте",
    viber: "Viber",
    owner_test: "Тестовый чат",
  },
};
