/**
 * `workspace.*` texts of shared by channels, billing, settings and the admin,
 * in Russian.
 */

import type { Translation } from "../../../translate";
import type { workspaceCommonEn } from "./common.en";

export const workspaceCommonRu: Translation<typeof workspaceCommonEn> = {
  copy: "Копировать",
  copied: "Скопировано",
  copyFailed: "Не удалось скопировать. Выделите текст и скопируйте вручную.",
  ownerOnlyChange: "Изменять это может только владелец. Смотреть можно.",
  ownerOnlyTitle: "Только для владельца",
  ownerOnlyDescription: "Этот раздел видит только владелец бизнеса.",
  loadMore: "Показать ещё",
  usage: {
    notIncluded: "Не входит",
  },
  plans: {
    chat: "Чат",
    voice_and_chat: "Голос + чат",
    plus: "Плюс",
  },
};
