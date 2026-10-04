/** `changelog.*` texts of "What's new", in Russian. */

import type { Translation } from "../../../translate";
import type { changelogEn } from "./changelog.en";

export const changelogRu: Translation<typeof changelogEn> = {
  title: "Что нового",
  description: "Что недавно изменилось в кабинете, сначала новое.",
  newBadge: "Новое",
};
