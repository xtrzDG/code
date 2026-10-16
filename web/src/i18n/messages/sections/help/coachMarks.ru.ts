/** `coachMarks.*` texts of the one-time tips on the Inbox, the Assistant and Channels, in Russian. */

import type { Translation } from "../../../translate";
import type { coachMarksEn } from "./coachMarks.en";

export const coachMarksRu: Translation<typeof coachMarksEn> = {
  label: "Подсказка",
  gotIt: "Понятно",
  readGuide: "Читать инструкцию",
  inbox: {
    title: "Входящие вашей команды",
    body: "Сверху разговоры, где нужен человек. Откройте разговор, чтобы ответить, передать его коллеге или оставить заметку, которую видит только команда.",
  },
  assistant: {
    title: "Сначала попробуйте помощника здесь",
    body: "Напишите так, как написал бы клиент. Всё, чему вы учите помощника, сначала появляется здесь, а клиенты получают это позже.",
  },
  channels: {
    title: "Подключите каналы, где пишут клиенты",
    body: "Начните с канала, которым клиенты пользуются чаще всего. На каждой карточке видно, работает ли канал и когда пришло последнее сообщение.",
  },
};
