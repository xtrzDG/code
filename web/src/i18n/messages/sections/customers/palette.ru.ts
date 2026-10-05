/** `palette.*` texts: the command palette (Cmd/Ctrl+K), in Russian. */

import type { Translation } from "../../../translate";
import type { paletteEn } from "./palette.en";

export const paletteRu: Translation<typeof paletteEn> = {
  title: "Поиск и переход",
  open: "Поиск",
  openTitle: "Поиск (Ctrl+K или ⌘K)",
  placeholder: "Клиент, разговор, бронь или страница",
  groups: {
    navigation: "Перейти",
    customers: "Клиенты",
    conversations: "Разговоры",
    bookings: "Брони",
  },
  searching: "Ищем…",
  noResults: "По запросу «{text}» ничего не нашлось.",
  resultCount: {
    one: "{count} результат",
    few: "{count} результата",
    many: "{count} результатов",
    other: "{count} результата",
  },
  typeMore: "Введите хотя бы две буквы, чтобы искать клиентов, разговоры и брони.",
  searchFailed: "Поиск не ответил; страницы по-прежнему здесь.",
  keys: "↑ ↓ — выбрать · Enter — открыть · Esc — закрыть",
  unnamed: "Клиент без имени",
  conversationDetail: "{channel} · {date}",
  bookingDetail: "{date} · {guests}",
  partySize: { one: "{count} гость", few: "{count} гостя", many: "{count} гостей", other: "{count} гостя" },
};
