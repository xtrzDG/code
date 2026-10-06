/** `chrome.*` in Hebrew: the page's compact chrome on a phone (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { chromeEn } from "./chrome.en";

export const chromeHe: Translation<typeof chromeEn> = {
  pageInfo: "על העמוד הזה",
  liveDot: "{status}. {updated}",
  filters: {
    open: "מסננים",
    openWithCount: "מסננים: {count} פעילים",
    title: "מסננים",
    clear: "ניקוי המסננים",
    show: "הצגה",
  },
};
