/** `changelog.*` texts of "What's new", in Italian (draft awaiting a native speaker's review). */

import type { Translation } from "../../../translate";
import type { changelogEn } from "./changelog.en";

export const changelogIt: Translation<typeof changelogEn> = {
  title: "Novità",
  description: "Le ultime modifiche al pannello, dalla più recente.",
  newBadge: "Nuovo",
};
