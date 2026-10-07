/** `workspaceCommon.*` in Hebrew (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { workspaceCommonEn } from "./common.en";

export const workspaceCommonHe: Translation<typeof workspaceCommonEn> = {
  copy: "העתקה",
  copied: "הועתק",
  copyFailed: "לא הצלחנו להעתיק. סמנו את הטקסט והעתיקו ידנית.",
  ownerOnlyChange: "רק הבעלים יכולים לשנות את זה. אפשר להסתכל.",
  ownerOnlyTitle: "לבעלים בלבד",
  ownerOnlyDescription: "רק הבעלים של העסק יכולים לראות את החלק הזה.",
  loadMore: "להציג עוד",
  usage: {
    notIncluded: "לא כלול",
  },
  plans: {
    chat: "צ׳אט",
    voice_and_chat: "קול + צ׳אט",
    plus: "Plus",
  },
};
