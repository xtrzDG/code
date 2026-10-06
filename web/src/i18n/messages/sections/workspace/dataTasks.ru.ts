/** `dataTasks.*` texts in Russian (typed against dataTasks.en.ts). */

import type { Translation } from "../../../translate";
import type { dataTasksEn } from "./dataTasks.en";

export const dataTasksRu: Translation<typeof dataTasksEn> = {
  title: "Задачи с данными после выпуска",
  description:
    "Перевод документов в новый формат и заполнение столбцов поиска, которые пакетный воркер выполняет сам пачками по {size} строк. Следующий выпуск продвигается, только когда все задачи готовы.",
  open: {
    one: "{count} задача не завершена",
    few: "{count} задачи не завершены",
    many: "{count} задач не завершено",
    other: "{count} задачи не завершены",
  },
  allDone: "Все задачи готовы",
  failed: "С ошибкой: {count}",
  stalled: "Висят дольше суток: {count}",
  settled: "Воркеров другого выпуска нет: задачи выполняются.",
  waiting: "Ждём, пока остановятся воркеры выпуска {releases} (примерно {time}).",
  waitingUnnamed: "Ждём, пока остановятся воркеры выпуска без имени (примерно {time}).",
  none: "В этом выпуске нет задач с данными.",
  openCaption: "Незавершённые задачи с данными",
  doneCaption: "Готовые задачи с данными",
  showDone: {
    one: "Показать {count} готовую задачу",
    few: "Показать {count} готовые задачи",
    many: "Показать {count} готовых задач",
    other: "Показать {count} готовой задачи",
  },
  hideDone: "Скрыть готовые задачи",
  columns: {
    task: "Задача",
    status: "Состояние",
    progress: "Ход",
    when: "Когда",
    actions: "Действия",
  },
  kinds: {
    migrate_documents: "Переписать документы в формат №{version}",
    backfill_lookup: "Заполнить столбец поиска",
  },
  statuses: {
    pending: "Ждёт",
    running: "Идёт",
    done: "Готово",
    failed: "Ошибка",
  },
  lists: {
    customers: "Список клиентов",
    knowledge: "Список знаний",
  },
  holdsBack: "Задерживает: {lists}",
  rows: "{scanned} из примерно {estimate} строк",
  rowsUnknown: "Просмотрено строк: {scanned}",
  changed: "Изменено: {count}, пачек: {batches}",
  failedRows: "Не удалось обновить строк: {count} ({keys})",
  dueSince: "Ждёт с {time}",
  doneAt: "Готово {time}",
  lastBatch: "Последняя пачка {time}",
  isStalled: "Зависла",
  retry: "Пройти заново",
  retried: "Задача проходит таблицу заново.",
  indexing: {
    title: "Ещё индексируется",
    body: "После последнего выпуска ещё идёт обновление данных, поэтому несколько минут в списке могут отсутствовать некоторые старые записи.",
  },
};
