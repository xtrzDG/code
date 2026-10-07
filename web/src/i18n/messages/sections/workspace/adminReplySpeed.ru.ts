/** `adminReplySpeed.*` texts of the reply-speed card on the admin's client page, in Russian. */

import type { Translation } from "../../../translate";
import type { adminReplySpeedEn } from "./adminReplySpeed.en";

export const adminReplySpeedRu: Translation<typeof adminReplySpeedEn> = {
  title: "Скорость ответа, 7 дней",
  description: "Сколько ждали клиенты — от первого сообщения без ответа до ответа помощника.",
  median: "Обычно (медиана)",
  p95: "19 из 20 ответов быстрее",
  replies: "Измерено ответов",
  slowNote: "Больше одного ответа из двадцати шли дольше 15 секунд. Проверьте провайдера модели и инструменты бизнеса.",
  empty: "За последние 7 дней измеренных ответов нет. Чаты измеряются начиная с этого обновления; звонки и тестовый чат не измеряются.",
  tableCaption: "Скорость ответа по каналам",
  channel: "Канал",
  channelReplies: "Ответов",
  channelMedian: "Медиана",
  channelP95: "95%",
  seconds: "{value} с",
  minutes: "{value} мин",
  issueLabel: "Медленные ответы",
};
