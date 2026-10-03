/**
 * Texts of the Assistant's daily work outside its pages: the changes not
 * with customers yet and "Apply changes" (the banner over every page and
 * its sheet).
 *
 * Top-level keys are namespaces. They are spread into en.ts, ru.ts and
 * ka.ts, so they must not clash with the namespaces of the other
 * dictionaries. `ru` and `ka` are type-checked against `en`.
 */

import type { Translation } from "../../translate";
import { applyChangesEn } from "./assistant/applyChanges.en";
import { applyChangesKa } from "./assistant/applyChanges.ka";
import { applyChangesRu } from "./assistant/applyChanges.ru";

export const assistantFlowEn = {
  applyChanges: applyChangesEn,
} as const;

export const assistantFlowRu: Translation<typeof assistantFlowEn> = {
  applyChanges: applyChangesRu,
};

export const assistantFlowKa: Translation<typeof assistantFlowEn> = {
  applyChanges: applyChangesKa,
};
