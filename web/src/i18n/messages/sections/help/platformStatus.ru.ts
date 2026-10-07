/** `platformStatus.*` texts of the public status page and the cabinet's announcement banner, in Russian. */

import type { Translation } from "../../../translate";
import type { platformStatusEn } from "./platformStatus.en";

export const platformStatusRu: Translation<typeof platformStatusEn> = {
  title: "Статус платформы",
  description: "Работают ли сейчас чаты с клиентами, каналы, звонки и кабинет и как прошли последние 90 дней.",
  overall: {
    operational: "Всё работает",
    maintenance: "Идут плановые работы",
    degraded: "Некоторые части работают медленнее обычного",
    outage: "Некоторые части сейчас не работают",
    no_data: "Пока нет замеров",
  },
  levels: {
    operational: "Работает",
    maintenance: "Плановые работы",
    degraded: "Медленно",
    outage: "Не работает",
    no_data: "Нет данных",
  },
  components: {
    chat: "Чат на сайте и страница чата",
    meta: "WhatsApp, Instagram и Messenger",
    telegram: "Telegram",
    voice: "Телефонные звонки",
    cabinet: "Кабинет и вход",
  },
  checkedAt: "Проверено {time}",
  monitoringDelayed: {
    title: "Собственные проверки платформы запаздывают",
    minutesAgo: {
      one: "Последняя проверка {count} мин назад.",
      few: "Последняя проверка {count} мин назад.",
      many: "Последняя проверка {count} мин назад.",
      other: "Последняя проверка {count} мин назад.",
    },
    at: "Последняя проверка: {time}",
    body: "Пока проверки не наверстают, никто не может поручиться за уровни ниже, поэтому чаты показаны как замедленные.",
  },
  componentsTitle: "Части платформы",
  historyLabel: "{component}: последние 90 дней",
  historyStart: "90 дней назад",
  historyEnd: "Сегодня",
  uptime: {
    one: "{share} без проблем за {count} день",
    few: "{share} без проблем за {count} дня",
    many: "{share} без проблем за {count} дней",
    other: "{share} без проблем за {count} дня",
  },
  observingSince: "Наблюдаем с {date}",
  noHistory: "Пока нет замеренных дней",
  day: "{day}: {level}",
  announcementLevels: {
    info: "Сообщение",
    maintenance: "Плановые работы",
    degraded: "Замедление",
    outage: "Сбой",
  },
  activeTitle: "Сейчас",
  scheduled: "Запланировано",
  starts: "Начало {time}",
  since: "С {time}",
  expectedEnd: "Ожидаемое окончание {time}",
  resolved: "Решено {time}",
  updated: "Обновлено {time}",
  affects: "Затрагивает: {components}",
  pastTitle: "Прошлые сбои",
  pastEmpty: "За последние 90 дней сбоев не было.",
  unreachable: {
    title: "Не удалось загрузить статус",
    body: "Эта страница сейчас не может связаться с платформой. Если чаты тоже не работают, напишите в поддержку: команда уже знает.",
  },
  selfMeasured: "Платформа проверяет себя каждые пять минут, а команда добавляет то, что знает.",
  openCabinet: "Открыть кабинет",
  banner: {
    region: "Объявление платформы",
    details: "Подробнее",
    dismiss: "Скрыть",
  },
};
