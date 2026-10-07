/** `segments.*` texts: saved groups of customers and their CSV, in Russian. */

import type { Translation } from "../../../translate";
import type { segmentsEn } from "./segments.en";

export const segmentsRu: Translation<typeof segmentsEn> = {
  loading: "Загружаем сегменты…",
  new: "Новый сегмент",
  empty: "Сегментов пока нет",
  emptyDescription: "Сохраните группу клиентов, например постоянных, которые не приходили 60 дней, и скачайте её для рассылки.",
  limit: "У бизнеса может быть не больше 50 сегментов. Удалите один, чтобы сохранить новый.",
  members: "Клиенты",
  noMembers: "Сейчас под этот сегмент никто не подходит.",
  export: "Скачать CSV",
  exportHint: "Клиенты сегмента с телефонами, каналами, метками и бронями — для рассылки в другом сервисе.",
  edit: "Изменить",
  delete: "Удалить",
  deleteTitle: "Удалить сегмент «{name}»?",
  deleteBody: "Удаляются только сохранённые правила; клиенты не меняются.",
  deleted: "Сегмент удалён",
  saved: "Сегмент сохранён",
  editor: {
    newTitle: "Новый сегмент",
    editTitle: "Изменить сегмент",
    name: "Название",
    namePlaceholder: "Например, не приходили 60 дней",
    rules: "Кто входит",
    rulesHint: "Должны выполняться все заполненные правила. Заблокированные и удалённые клиенты не входят никогда.",
    tag: "Метка",
    anyTag: "Любая метка",
    lastVisit: "Последний визит больше … дней назад",
    minBookings: "Броней не меньше …",
    maxBookings: "Броней не больше …",
    vipOnly: "Только VIP-клиенты",
    save: "Сохранить сегмент",
  },
  errors: {
    name: "Назовите сегмент (до 60 символов).",
    days: "Дни — целое число от 1 до 3650.",
    bookings: "Брони — целое число от 0 до 10000.",
    minMax: "«Не меньше» не может быть больше, чем «не больше».",
  },
  preview: {
    counting: "Считаем…",
    count: {
      one: "Подходит {count} клиент",
      few: "Подходят {count} клиента",
      many: "Подходят {count} клиентов",
      other: "Подходят {count} клиента",
    },
    atLeast: {
      one: "Подходит не меньше {count} клиента",
      few: "Подходят не меньше {count} клиентов",
      many: "Подходят не меньше {count} клиентов",
      other: "Подходят не меньше {count} клиента",
    },
    none: "Пока никто не подходит.",
  },
  summary: {
    everyone: "Все клиенты",
    tag: "метка «{tag}»",
    lastVisit: {
      one: "последний визит больше {count} дня назад",
      few: "последний визит больше {count} дней назад",
      many: "последний визит больше {count} дней назад",
      other: "последний визит больше {count} дня назад",
    },
    minBookings: {
      one: "не меньше {count} брони",
      few: "не меньше {count} броней",
      many: "не меньше {count} броней",
      other: "не меньше {count} брони",
    },
    maxBookings: {
      one: "не больше {count} брони",
      few: "не больше {count} броней",
      many: "не больше {count} броней",
      other: "не больше {count} брони",
    },
    vipOnly: "только VIP",
  },
};
