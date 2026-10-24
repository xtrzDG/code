/** `tunnel.*`: the frame of "Create an AI assistant", in Russian. */

import type { Translation } from "../../../translate";
import type { tunnelEn } from "./tunnel.en";

export const tunnelRu: Translation<typeof tunnelEn> = {
  pageTitle: "Создать AI-помощника",
  newAssistant: "Новый помощник",
  railLabel: "Шаги настройки",
  steps: {
    business: "Ваш бизнес",
    place: "Где вы",
    offer: "Что вы предлагаете",
    hours: "Часы и брони",
    people: "Кто поможет",
    channels: "Где пишут клиенты",
    try: "Попробовать",
    launch: "Запуск",
  },
  stepOf: "Шаг {number} из {total}",
  stepState: {
    done: "готово",
    skipped: "пропущено",
    current: "вы здесь",
    todo: "ещё впереди",
  },
  announce: "Шаг {number} из {total}: {title}",
  announceFinale: "Ваш помощник работает",
  back: "Назад",
  continue: "Дальше",
  skip: "Пропустить пока",
  enterHint: "или нажмите Enter",
  exit: "Сохранить и выйти",
  saving: "Сохраняем…",
  saved: "Сохранено",
  saveFailed: "Пока не сохранено",
  ownerOnlyTitle: "Помощника создаёт владелец",
  ownerOnlyText: "Настроить его может только владелец «{business}». Разговоры, брони и заявки появятся в кабинете, как только помощник заработает.",
  openCabinet: "Открыть кабинет",
};
