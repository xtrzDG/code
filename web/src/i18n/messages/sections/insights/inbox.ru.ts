/** `inbox.*` texts of the team inbox list, in Russian. */

import type { Translation } from "../../../translate";
import type { inboxEn } from "./inbox.en";

export const inboxRu: Translation<typeof inboxEn> = {
  title: "Входящие",
  viewsLabel: "Какие разговоры показать",
  views: {
    needs_person: "Нужен человек",
    requests: "Заявки",
    mine: "Мои",
    unassigned: "Без ответственного",
    all: "Все",
  },
  moreViews: "Ещё",
  moreViewsChosen: "Ещё: {view}",
  viewCount: {
    one: "{count} разговор",
    few: "{count} разговора",
    many: "{count} разговоров",
    other: "{count} разговора",
  },
  empty: {
    needs_person: {
      title: "Никто не ждёт человека",
      description: "Когда помощник передаёт разговор вашей команде, он сразу появляется здесь.",
    },
    requests: {
      title: "Открытых заявок нет",
      description: "Банкеты, группы и другие заявки, которые принял помощник, ждут здесь, пока ими кто-нибудь не займётся.",
    },
    mine: {
      title: "На вас ничего не назначено",
      description: "Разговоры, которые вы взяли себе или которые поручили вам, ждут здесь, пока нужна команда.",
    },
    unassigned: {
      title: "У каждого разговора есть ответственный",
      description: "Здесь появляются разговоры, которым нужна команда, но за которые пока никто не отвечает.",
    },
    all: {
      title: "Разговоров пока нет",
      description: "Разговоры появятся здесь, как только клиенты напишут или позвонят помощнику.",
    },
  },
  showAll: "Показать все разговоры",
  loading: "Загружаем входящие…",
  listLabel: "Разговоры",
  searchLabel: "Поиск по всем разговорам",
  searchPlaceholder: "Поиск: имя, телефон или текст",
  filters: {
    open: "Фильтры",
    openWithCount: "Фильтры ({count})",
    title: "Фильтры",
    description: "Период, статус и тестовые разговоры действуют на все разговоры и на поиск.",
    show: "Показать разговоры",
    clear: "Сбросить фильтры",
    includeTest: "Показывать тестовые разговоры",
  },
  results: "Найдено по запросу «{search}»",
  clearSearch: "Очистить поиск",
  row: {
    unassigned: "Никто не назначен",
    assignedTo: "Отвечает: {name}",
    you: "Вы",
    notes: {
      one: "{count} заметка",
      few: "{count} заметки",
      many: "{count} заметок",
      other: "{count} заметки",
    },
    request: "Заявка: {type}",
    waiting: "Ждёт с {time}",
  },
  assign: {
    open: "Назначить",
    menuLabel: "Кто отвечает за разговор",
    handledBy: "Отвечает: {name}",
    handledByYou: "Отвечаете вы",
    automatically: "Назначено автоматически",
    nobody: "Пока никто не отвечает",
    takeIt: "Взять себе",
    unassign: "Снять назначение",
    you: "Вы",
    teammate: "Участник команды",
    waiting: {
      one: "{count} ждёт",
      few: "{count} ждут",
      many: "{count} ждут",
      other: "{count} ждут",
    },
    loading: "Загружаем команду…",
    assigned: "Теперь за разговор отвечает {name}",
    taken: "Теперь за разговор отвечаете вы",
    cleared: "Теперь никто не назначен",
    conflict: "Кто-то только что изменил, кто отвечает за этот разговор. Показываем, как сейчас.",
    colleague: "За разговор отвечает коллега. Попросите владельца передать его вам.",
    notMember: "Этого человека уже нет в команде.",
  },
};
