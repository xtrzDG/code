/** `navigation.*` texts: sections of a business, the sidebar and the phone tab bar, in Russian. */

import type { Translation } from "../../../translate";
import type { navigationEn } from "./navigation.en";

export const navigationRu: Translation<typeof navigationEn> = {
  sections: {
    overview: "Обзор",
    messages: "Сообщения",
    bookings: "Брони",
    assistant: "Помощник",
    settings: "Настройки",
  },
  descriptions: {
    overview: "Как работает помощник и что сегодня ждёт вашего внимания.",
    messages: "Все разговоры, те, где нужен человек, и заявки клиентов — в одном месте.",
    bookings: "Брони со статусами; можно добавить вручную.",
    assistant: "Попробуйте помощника, научите его, выберите, где он отвечает, и примените изменения.",
    settings: "Ваш бизнес, команда, уведомления, звонки, тариф, приватность и журнал действий.",
    assistantTest: "Пишите так, как написал бы клиент. Настоящим клиентам ничего не уйдёт.",
    assistantProfile: "Контакты, часы работы, что вы предлагаете, правила брони и когда звать человека — анкета, по которой работает помощник.",
    assistantVersions: "Каждое обновление помощника с проверками, публикацией и возвратом.",
  },
  pages: {
    messagesAll: "Все разговоры",
    messagesHandoffs: "Нужен человек",
    messagesLeads: "Заявки",
    assistantTest: "Попробовать",
    assistantKnowledge: "Знания",
    assistantProfile: "Часы и правила",
    assistantChannels: "Каналы",
    assistantVersions: "Обновления и проверки",
    settingsGeneral: "Бизнес",
    settingsTeam: "Команда",
    settingsNotifications: "Уведомления",
    settingsCalls: "Звонки",
    settingsReviews: "Отзывы",
    settingsBilling: "Тариф и оплата",
    settingsPrivacy: "Приватность",
    settingsAudit: "Журнал действий",
  },
  sectionPages: "Страницы раздела «{section}»",
  applyChanges: "Применить изменения",
  applyChangesHint: "Подготовить обновление из анкеты и знаний, проверить и опубликовать, если проверки пройдены.",
  advanced: "Дополнительно",
  collapse: "Свернуть меню",
  expand: "Развернуть меню",
  tabBar: "Разделы",
  more: "Ещё",
  waiting: {
    one: "{count} ждёт",
    few: "{count} ждут",
    many: "{count} ждут",
    other: "{count} ждут",
  },
  ownerOnlyTitle: "Эта страница для владельцев",
  ownerOnlyDescription: "Ваша роль в «{business}» её не открывает. Если здесь нужно что-то изменить, попросите владельца.",
  toOverview: "К обзору",
};
