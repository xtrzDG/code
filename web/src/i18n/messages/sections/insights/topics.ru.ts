/** `topics.*` texts: карточка «О чём спрашивают клиенты» на обзоре, на русском. */

import type { Translation } from "../../../translate";
import type { topicsEn } from "./topics.en";

export const topicsRu: Translation<typeof topicsEn> = {
  title: "О чём спрашивают клиенты",
  description: "Первые сообщения за последние 30 дней, разобранные по темам каждую ночь.",
  updated: "Обновлено {date}",
  waiting: "Темы появятся после первой ночи с разговорами.",
  empty: "За последние 30 дней клиенты ещё не писали.",
  conversations: {
    one: "{count} разговор",
    few: "{count} разговора",
    many: "{count} разговоров",
    other: "{count} разговора",
  },
  unanswered: {
    one: "{count} без ответа",
    few: "{count} без ответа",
    many: "{count} без ответа",
    other: "{count} без ответа",
  },
  unansweredHint: "Вопросы, на которые помощник не смог ответить: добавьте ответ — и он будет отвечать.",
  addAnswer: "Добавить ответ",
  otherLanguages: "Другие языки",
  languageLabel: "Язык",
  loading: "Загружаем темы…",
};
