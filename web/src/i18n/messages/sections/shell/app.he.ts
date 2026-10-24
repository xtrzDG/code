/** `app.*` in Hebrew: the installed app and the offline page (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { appEn } from "./app.en";

export const appHe: Translation<typeof appEn> = {
  shortName: "העוזרים",
  offlineTitle: "אין חיבור לאינטרנט",
  offlineDescription: "לוח הבקרה צריך אינטרנט. הוא ייפתח שוב ברגע שתחזרו לרשת.",
  offlineRetry: "לנסות שוב",
};
