/** `app.*` texts of the installed app and the offline page, in Italian (draft awaiting a native speaker's review). */

import type { Translation } from "../../../translate";
import type { appEn } from "./app.en";

export const appIt: Translation<typeof appEn> = {
  shortName: "Assistenti",
  offlineTitle: "Sei offline",
  offlineDescription: "Il pannello ha bisogno di internet. Si riaprirà appena tornerai online.",
  offlineRetry: "Riprova",
};
