/** `quickReplies.*` texts of Settings → Quick replies, in Russian. */

import type { Translation } from "../../../translate";
import type { quickRepliesEn } from "./quickReplies.en";

export const quickRepliesRu: Translation<typeof quickRepliesEn> = {
  description:
    "Ответы, которые команда отправляет часто, готовые на каждом языке вашего бизнеса. В разговоре наберите /, чтобы вставить ответ: имя клиента и время записи подставятся сами.",
  add: "Новый быстрый ответ",
  loading: "Загружаем быстрые ответы…",
  emptyTitle: "Быстрых ответов пока нет",
  emptyDescription: "Часы работы, как добраться, «мы вам перезвоним»: напишите один раз и отправляйте в два касания.",
  listLabel: "Быстрые ответы",
  languages: "Языки",
  variablesUsed: "Подставляет",
  edit: "Изменить",
  editLabel: "Изменить быстрый ответ «{title}»",
  delete: "Удалить",
  deleteLabel: "Удалить быстрый ответ «{title}»",
  confirmDelete: {
    title: "Удалить быстрый ответ?",
    description: "«{title}» пропадёт из списка у всей команды.",
    confirm: "Удалить",
  },
  deleted: "Быстрый ответ удалён",
  saved: "Быстрый ответ сохранён",
  editor: {
    newTitle: "Новый быстрый ответ",
    editTitle: "Изменить быстрый ответ",
    description: "Напишите его на каждом языке, на котором пишут ваши клиенты. Сотрудники увидят текст на языке разговора.",
    title: "Название",
    titleHint: "Так ответ называется в списке у команды.",
    shortcut: "Сокращение",
    shortcutHint: "Набирается после / в поле ответа: буквы, цифры, - и _.",
    shortcutInvalid: "Только буквы, цифры, - и _, без пробелов.",
    texts: "Текст",
    textIn: "Текст на языке: {language}",
    textHint: "Оставьте язык пустым, если он не нужен. Нужен хотя бы один текст.",
    needOneText: "Напишите текст хотя бы на одном языке.",
    insert: "Вставить",
    insertLabel: "Вставить «{variable}» в текст на языке: {language}",
    preview: "Как увидит клиент",
    sample: {
      name: "Нино",
      bookingTime: "сб, 19:30",
    },
    save: "Сохранить",
    saving: "Сохраняем…",
    cancel: "Отмена",
    length: "{count} / {max}",
  },
  variables: {
    name: "Имя клиента",
    booking_time: "Время записи",
    business_name: "Название бизнеса",
  },
  errors: {
    shortcut_taken: "Это сокращение уже занято другим быстрым ответом.",
    too_many_quick_replies: "У бизнеса может быть не больше 100 быстрых ответов. Удалите тот, который больше не нужен.",
    unknown_variable: "Подставить можно только {name}, {booking_time} и {business_name}. Проверьте фигурные скобки в тексте.",
    duplicate_language: "На каждом языке может быть только один текст.",
  },
};
