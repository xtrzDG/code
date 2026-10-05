/** `dpaNotice.*` по-русски (см. dpaNotice.en.ts). */

import type { Translation } from "../../../translate";
import type { dpaNoticeEn } from "./dpaNotice.en";

export const dpaNoticeRu: Translation<typeof dpaNoticeEn> = {
  label: "Новое соглашение об обработке данных",
  title: "Вышла новая версия соглашения об обработке данных ({version})",
  due: "Она заменяет версию, которую вы приняли. Прочитайте и примите её до {date}: без текущей версии изменения помощника не применить.",
  overdue:
    "Она заменяет версию, которую вы приняли; срок принятия ({date}) прошёл. Без текущей версии изменения помощника не применить — прочитайте и примите её сейчас.",
  action: "Прочитать и принять",
};
