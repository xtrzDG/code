/** `dataExports.*` texts: exports of the business's data, in Russian. */

import type { Translation } from "../../../translate";
import type { dataExportsEn } from "./dataExports.en";

export const dataExportsRu: Translation<typeof dataExportsEn> = {
  csv: {
    button: "Выгрузить CSV",
    bookingsHint: "Брони, которые показывают фильтры, таблицей (CSV)",
    inboxLabel: "Выгрузить эти разговоры в CSV",
    inboxHint: "Выбранный раздел и канал, со всеми сообщениями",
    tableLabel: "Скачать «{table}» в CSV",
    saved: "Файл скачан",
    tables: {
      bookings: "Брони",
      leads: "Заявки",
      contacts: "Клиенты",
      conversations: "Разговоры",
      audit_log: "Журнал действий",
    },
  },
  full: {
    title: "Выгрузка ваших данных",
    description:
      "Всё, что хранится о вашем бизнесе, одним ZIP-файлом: клиенты, разговоры со всеми сообщениями, звонки, брони, заявки, услуги, пропущенные звонки, отзывы и журнал действий — в JSON и таблицами (CSV).",
    start: "Подготовить полную выгрузку",
    started: "Готовим выгрузку",
    working: "Собираем архив. Это займёт несколько минут; можно уйти со страницы и вернуться.",
    history: "Последние выгрузки",
    empty: "Выгрузок пока не было. Подготовьте её, когда понадобится копия данных.",
    requested: "Запрошена {date}",
    readyUntil: "Хранится до {date}",
    download: "Скачать ZIP",
    downloadLabel: "Скачать выгрузку, запрошенную {date}",
    downloadStarted: "Скачивание началось",
    downloadsLeft: {
      one: "Осталось {count} скачивание из {total}",
      few: "Осталось {count} скачивания из {total}",
      many: "Осталось {count} скачиваний из {total}",
      other: "Осталось {count} скачивания из {total}",
    },
    usedUp: "Эту выгрузку уже скачали три раза. Чтобы получить ещё одну копию, подготовьте новую.",
    gone: "Эта выгрузка больше не хранится. Подготовьте новую.",
    sizeKb: "{size} КБ",
    sizeMb: "{size} МБ",
    records: {
      one: "{count} запись",
      few: "{count} записи",
      many: "{count} записей",
      other: "{count} записи",
    },
    failed: "Не удалось собрать архив. Подготовьте выгрузку ещё раз; если снова не выйдет, напишите в поддержку.",
    status: {
      queued: "В очереди",
      running: "Готовится",
      ready: "Готова",
      expired: "Удалена",
      failed: "Ошибка",
    },
    linkNote:
      "Для каждого скачивания создаётся одноразовая ссылка: она работает 10 минут и только у вас. Выгрузку можно скачать три раза в течение суток, и каждый владелец получает уведомление — кто скачал, с какого устройства и адреса.",
    erasedNote: "Клиентов, чьи данные удалены, нет ни в одной выгрузке.",
  },
  tables: {
    title: "Таблицы для Excel",
    description:
      "Одна таблица в CSV — для Excel, Numbers или Google Таблиц. Брони и «Входящие» выгружаются ещё и с выбранными там фильтрами.",
  },
};
