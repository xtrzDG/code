/** `formFields.*` texts in Russian. */

import type { Translation } from "../../../translate";
import type { formFieldsEn } from "./formFields.en";

export const formFieldsRu: Translation<typeof formFieldsEn> = {
  time: {
    hours: "Часы",
    minutes: "Минуты",
    dayPeriod: "До или после полудня",
    empty: "Не задано",
  },
  date: {
    placeholder: "Выберите дату",
    open: "Открыть календарь",
    calendar: "Календарь",
    previousMonth: "Предыдущий месяц",
    nextMonth: "Следующий месяц",
    today: "Сегодня",
    clear: "Очистить",
    date: "Дата",
    time: "Время",
  },
  autosave: {
    hint: "Изменения сохраняются сами.",
    saving: "Сохраняем…",
    saved: "Сохранено",
    failed: "Не сохранено",
    retry: "Повторить",
  },
};
