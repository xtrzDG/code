/** `live.*` по-русски (см. live.en.ts). */

import type { Translation } from "../../../translate";
import type { liveEn } from "./live.en";

export const liveRu: Translation<typeof liveEn> = {
  status: {
    live: "Онлайн",
    connecting: "Подключение…",
    reconnecting: "Переподключение…",
    paused: "Обновления приостановлены",
  },
  updatedJustNow: "Обновлено только что",
  updatedMinutesAgo: {
    one: "Обновлено {count} минуту назад",
    few: "Обновлено {count} минуты назад",
    many: "Обновлено {count} минут назад",
    other: "Обновлено {count} минуты назад",
  },
  updatedAt: "Обновлено в {time}",
  updating: "Обновляется…",
  liveHint: "Страница обновляется сама, когда клиенты пишут, бронируют или ждут человека.",
  reconnectingHint: "Связь прервалась, мы переподключаемся. Можно попробовать сейчас.",
  reconnect: "Попробовать сейчас",
  needsPersonTitle: "Клиенту нужен человек",
  needsPersonOpen: "Открыть",
  needsPersonAnnouncement: "Клиенту нужен человек. Ждут: {count}.",
  sound: "Сигнал, когда нужен человек",
  soundHint: "Короткий звук на этом устройстве, когда разговор передан вашей команде.",
};
