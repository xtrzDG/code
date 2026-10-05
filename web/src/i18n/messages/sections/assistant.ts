/**
 * Texts of the Assistant's daily work outside its pages: the changes not
 * with customers yet and "Apply changes" (the banner over every page and
 * its sheet), and teaching it from conversations ("Fix this answer", "My
 * checks", "Answers worth improving").
 *
 * Top-level keys are namespaces. They are spread into en.ts, ru.ts and
 * ka.ts, so they must not clash with the namespaces of the other
 * dictionaries. `ru` and `ka` are type-checked against `en`.
 */

import type { Translation } from "../../translate";
import { applyChangesEn } from "./assistant/applyChanges.en";
import { applyChangesKa } from "./assistant/applyChanges.ka";
import { applyChangesRu } from "./assistant/applyChanges.ru";
import { teachingEn } from "./assistant/teaching.en";
import { teachingKa } from "./assistant/teaching.ka";
import { teachingRu } from "./assistant/teaching.ru";
import { updatesEn } from "./assistant/updates.en";
import { updatesKa } from "./assistant/updates.ka";
import { updatesRu } from "./assistant/updates.ru";

export const assistantFlowEn = {
  applyChanges: applyChangesEn,
  teaching: teachingEn,
  updates: updatesEn,
} as const;

export const assistantFlowRu: Translation<typeof assistantFlowEn> = {
  applyChanges: applyChangesRu,
  teaching: teachingRu,
  updates: updatesRu,
};

export const assistantFlowKa: Translation<typeof assistantFlowEn> = {
  applyChanges: applyChangesKa,
  teaching: teachingKa,
  updates: updatesKa,
};
