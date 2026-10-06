/** `channelPages.*` texts of the Channels pages on a phone, in Russian. */

import type { Translation } from "../../../translate";
import type { channelPagesEn } from "./channelPages.en";

export const channelPagesRu: Translation<typeof channelPagesEn> = {
  heading: "Настройка",
  back: "Все каналы",
  website: {
    title: "Чат на сайте",
    hint: "Цвет, кнопка, код для сайта и где его можно показывать",
  },
  calls: {
    title: "Переадресация звонков",
    hint: "Коды, которые переводят пропущенные звонки на помощника",
  },
  share: {
    title: "Поделиться",
    hint: "Ссылки, QR-код и карточка на стол",
  },
  off: {
    website: "Чат на сайте выключен. Включите его среди каналов, чтобы выбрать вид и поставить на сайт.",
    calls: "Телефон не подключён. Подключите его среди каналов, чтобы получить коды переадресации.",
  },
};
