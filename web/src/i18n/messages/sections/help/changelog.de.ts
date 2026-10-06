/** `changelog.*` in German (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { changelogEn } from "./changelog.en";

export const changelogDe: Translation<typeof changelogEn> = {
  title: "Neuigkeiten",
  description: "Was sich zuletzt im Dashboard geändert hat, das Neueste zuerst.",
  newBadge: "Neu",
};
