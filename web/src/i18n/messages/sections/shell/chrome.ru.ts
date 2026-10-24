/** `chrome.*` texts of the phone's compact page chrome, in Russian. */

import type { Translation } from "../../../translate";
import type { chromeEn } from "./chrome.en";

export const chromeRu: Translation<typeof chromeEn> = {
  pageInfo: "Об этой странице",
  liveDot: "{status}. {updated}",
  filters: {
    open: "Фильтры",
    openWithCount: "Фильтры: выбрано {count}",
    title: "Фильтры",
    clear: "Сбросить фильтры",
    show: "Показать",
  },
};
