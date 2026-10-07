/** `chrome.*` texts of the phone's compact page chrome, in Georgian. */

import type { Translation } from "../../../translate";
import type { chromeEn } from "./chrome.en";

export const chromeKa: Translation<typeof chromeEn> = {
  pageInfo: "ამ გვერდის შესახებ",
  liveDot: "{status}. {updated}",
  filters: {
    open: "ფილტრები",
    openWithCount: "ფილტრები: არჩეულია {count}",
    title: "ფილტრები",
    clear: "ფილტრების გასუფთავება",
    show: "ჩვენება",
  },
};
