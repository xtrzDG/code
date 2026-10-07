/** `bookingCalendar.*`: the bookings calendar, in Russian. */

import type { Translation } from "../../../translate";
import type { bookingCalendarEn } from "./bookingCalendar.en";

export const bookingCalendarRu: Translation<typeof bookingCalendarEn> = {
  views: {
    label: "Показать брони",
    list: "Список",
    day: "День",
    week: "Неделя",
    nights: "Ночи",
  },
  toolbar: {
    label: "Даты календаря",
    previous: { day: "Предыдущий день", week: "Предыдущая неделя", nights: "Ночи раньше" },
    next: { day: "Следующий день", week: "Следующая неделя", nights: "Ночи позже" },
    today: "Сегодня",
    date: "Дата",
    includeTest: "Показывать тестовые брони",
  },
  loading: "Календарь загружается…",
  truncated: "В этом периоде больше броней, чем календарь может показать сразу. Откройте период короче или список.",
  legend: "Статус брони",
  moveHint: "Перетащите бронь на другое время или место. Или выберите её и двигайте стрелками: Enter — перенести, Escape — отменить.",
  day: {
    label: "Брони на {date} по местам",
    closed: "Закрыто",
    closedDay: "Закрыто весь день",
    newAt: "Новая бронь: {place}",
    booked: "занято {percent}",
    now: "Сейчас {time}",
    noPlacesTitle: "Нет мест с бронированием по времени",
    noPlacesDescription: "Добавьте столы, мастеров или залы, которые бронируют по времени, — день покажет каждое место отдельной колонкой.",
    toPlaces: "Добавить места",
  },
  block: {
    label: "{name}, {time}, {place}, {status}",
    test: "Тест",
  },
  move: {
    pending: "Перенести: {place}, {time}? Enter — перенести, Escape — отменить.",
    pendingStay: "Перенести: {place} с {date}? Enter — перенести, Escape — отменить.",
    moved: "Перенесено: {place}, {time}",
    movedStay: "Перенесено: {place} с {date}",
    undone: "Бронь вернулась на прежнее место",
    changed: "Эту бронь только что изменил кто-то другой: календарь показывает её такой, какая она сейчас.",
    cancelled: "Перенос отменён",
  },
  week: {
    label: "Загрузка мест, {range}",
    place: "Место",
    allPlaces: "Все места",
    closed: "Закрыто",
    free: "Свободно",
    share: "занято {percent}",
    rooms: {
      one: "занято {booked} из {open} номера",
      few: "занято {booked} из {open} номеров",
      many: "занято {booked} из {open} номеров",
      other: "занято {booked} из {open} номера",
    },
    cell: "{place}, {date}: {load}, {count}",
    legendTitle: "Загрузка",
    quiet: "Свободно",
    full: "Полно",
  },
  nights: {
    label: "Номера по ночам, {range}",
    room: "Номер",
    taken: "занято {booked} из {open}",
    newStay: "Новое проживание: {place}, ночь на {date}",
    noRoomsTitle: "Нет номеров с бронированием по ночам",
    noRoomsDescription: "Добавьте номера или категории номеров, которые бронируют по ночам, — здесь каждый будет отдельной строкой.",
  },
};
