/** `chrome.*` in German: the page's compact chrome on a phone (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { chromeEn } from "./chrome.en";

export const chromeDe: Translation<typeof chromeEn> = {
  pageInfo: "Über diese Seite",
  liveDot: "{status}. {updated}",
  filters: {
    open: "Filter",
    openWithCount: "Filter: {count} aktiv",
    title: "Filter",
    clear: "Filter zurücksetzen",
    show: "Anzeigen",
  },
};
