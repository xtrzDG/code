/** `app.*` texts: the installed app and the page shown without a connection, in Russian. */

import type { Translation } from "../../../translate";
import type { appEn } from "./app.en";

export const appRu: Translation<typeof appEn> = {
  shortName: "Ассистенты",
  offlineTitle: "Нет подключения к интернету",
  offlineDescription: "Кабинету нужен интернет. Он откроется снова, как только связь вернётся.",
  offlineRetry: "Повторить",
};
