/** `chrome.*` texts of the page's compact chrome on a phone, in Italian (draft awaiting a native speaker's review). */

import type { Translation } from "../../../translate";
import type { chromeEn } from "./chrome.en";

export const chromeIt: Translation<typeof chromeEn> = {
  pageInfo: "Informazioni su questa pagina",
  liveDot: "{status}. {updated}",
  filters: {
    open: "Filtri",
    openWithCount: "Filtri ({count})",
    title: "Filtri",
    clear: "Cancella i filtri",
    show: "Mostra",
  },
};
