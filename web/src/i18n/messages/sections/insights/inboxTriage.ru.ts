/** `inboxTriage.*` texts of working through the inbox list, in Russian. */

import type { Translation } from "../../../translate";
import type { inboxTriageEn } from "./inboxTriage.en";

export const inboxTriageRu: Translation<typeof inboxTriageEn> = {
  density: {
    label: "Строки",
    comfortable: "Удобно",
    compact: "Компактно",
  },
  resize: {
    label: "Ширина списка разговоров",
    hint: "Перетащите или используйте стрелки. Двойной щелчок вернёт обычную ширину.",
  },
  keys: {
    open: "Быстрые клавиши",
    title: "Быстрые клавиши",
    description: "Разбирайте список без мыши. Клавиши работают, пока вы не печатаете.",
    listHint: "J и K — по списку, E — решено, A — взять себе, X — выбрать, вопросительный знак — все клавиши.",
    resolveNote: "Решено: передача человеку закрывается и разговор возвращается помощнику, а открытая заявка становится успешной. Отменить можно в появившемся сообщении.",
    actions: {
      next: "Следующий разговор",
      previous: "Предыдущий разговор",
      open: "Открыть разговор",
      resolve: "Отметить решённым",
      assign: "Взять себе",
      select: "Выбрать для общего действия",
      search: "Поиск",
      help: "Показать эти клавиши",
      clear: "Снять выбор",
    },
  },
  select: {
    row: "Выбрать разговор с клиентом {name}",
    all: "Выбрать все разговоры, где есть что решить",
    count: {
      one: "Выбран {count}",
      few: "Выбрано {count}",
      many: "Выбрано {count}",
      other: "Выбрано {count}",
    },
    resolve: "Отметить решёнными",
    clear: "Снять выбор",
  },
  resolved: {
    one: "{count} разговор решён",
    few: "{count} разговора решены",
    many: "{count} разговоров решены",
    other: "{count} разговора решены",
  },
  resolvedPartly: "Решено {done} из {total}. Остальные кто-то изменил чуть раньше, список показывает, как они сейчас.",
  undone: "Вернули как было",
  undonePartly: "Часть не удалось вернуть: их уже кто-то изменил. Список показывает, как они сейчас.",
  nothingToResolve: "В этом разговоре нечего решать: нет открытой передачи человеку или заявки.",
  alreadyYours: "Этот разговор уже у вас.",
  age: {
    now: "сейчас",
    minutes: "{count} мин",
    hours: "{count} ч",
    days: "{count} дн",
  },
  details: {
    source: "Откуда",
    assignee: "Ответственный",
    lastMessage: "Последнее сообщение",
  },
};
