/** `helpCenter.*` texts of the help center, the article drawer and "Help and support", in Russian. */

import type { Translation } from "../../../translate";
import type { helpCenterEn } from "./helpCenter.en";

export const helpCenterRu: Translation<typeof helpCenterEn> = {
  title: "Помощь",
  description: "Короткие инструкции ко всем разделам кабинета.",
  searchLabel: "Поиск по справке",
  searchPlaceholder: "Telegram, запись, счёт…",
  search: "Найти",
  clearSearch: "Очистить поиск",
  results: {
    one: "Найдена {count} статья",
    few: "Найдено {count} статьи",
    many: "Найдено {count} статей",
    other: "Найдено {count} статьи",
  },
  noResults: "По запросу «{query}» ничего не нашлось. Попробуйте другое слово.",
  topics: {
    getting_started: "С чего начать",
    channels: "Каналы",
    daily_work: "Каждый день",
    account: "Аккаунт и оплата",
  },
  loadFailed: "Не удалось загрузить справку. Проверьте связь и попробуйте ещё раз.",
  allArticles: "Все статьи",
  related: "Читать дальше",
  otherLanguage: "Эта статья ещё не переведена, поэтому показана на языке: {language}.",
  pageHelp: "Помощь по этой странице",
  drawerTitle: "Помощь",
  openInCenter: "Открыть в справке",
  back: "Назад",
  stillStuck: "Остались вопросы?",
  stillStuckLead: "Напишите нам: ответит человек из команды.",
  noSupportLead: "Загляните на страницу состояния платформы: если что-то не работает у всех, команда уже этим занимается.",
  tipsAgain: "Показать подсказки снова",
  tipsShown: "Подсказки снова появятся на страницах «Входящие», «Помощник» и «Каналы».",
  opensInNewTab: "откроется в новой вкладке",
  support: {
    title: "Помощь и поддержка",
    center: "Справка",
    whatsNew: "Что нового",
    unread: {
      one: "{count} новое",
      few: "{count} новых",
      many: "{count} новых",
      other: "{count} новых",
    },
    status: "Статус платформы",
    contact: "Написать в поддержку",
    whatsapp: "WhatsApp",
    telegram: "Telegram",
    email: "Эл. почта",
  },
};
