import type { Translation } from "../../../translate";
import type { supportAccessEn } from "./supportAccess.en";

/** `supportAccess.*` по-русски: плашка доступа поддержки в кабинете. */
export const supportAccessRu: Translation<typeof supportAccessEn> = {
  label: "Доступ поддержки платформы",
  owner: {
    title: "Поддержка платформы смотрит ваш кабинет",
    who: "{name}: «{reason}»",
    reason: "Причина: «{reason}»",
    until: "до {time}",
    readOnly: "Поддержка может только смотреть: без вас ничего не изменится.",
    end: "Закрыть доступ",
    endTitle: "Закрыть доступ поддержке?",
    endDescription:
      "Поддержка сразу выйдет из кабинета, а разрешение на изменения тоже закончится.",
    ended: "У поддержки больше нет доступа",
    allow: "Разрешить поддержке изменения",
    allowHint:
      "Например, если вы попросили настроить помощника за вас. Закончится само.",
    allowedUntil: "Поддержка может вносить изменения до {time}",
    hours: "На сколько",
    hourOptions: {
      one: "{count} час",
      few: "{count} часа",
      many: "{count} часов",
      other: "{count} часа",
    },
    dayOption: "Сутки",
    weekOption: "Неделя",
    allowed: "Поддержка может вносить изменения",
    stopped: "Поддержка снова может только смотреть",
    staff: "Закрыть доступ или разрешить изменения может только владелец.",
  },
  support: {
    title: "Вы смотрите кабинет «{name}» как поддержка платформы",
    readOnly: "Только просмотр: изменения отклоняются.",
    canWrite: "Владелец разрешил изменения до {time}",
    until: "Доступ закончится в {time}",
    leave: "Выйти из кабинета",
    left: "Вы вышли из кабинета",
  },
};
