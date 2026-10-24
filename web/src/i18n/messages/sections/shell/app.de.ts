/** `app.*` in German: the installed app and the offline page (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { appEn } from "./app.en";

export const appDe: Translation<typeof appEn> = {
  shortName: "Assistenten",
  offlineTitle: "Sie sind offline",
  offlineDescription: "Das Dashboard braucht Internet. Es öffnet sich wieder, sobald Sie online sind.",
  offlineRetry: "Erneut versuchen",
};
