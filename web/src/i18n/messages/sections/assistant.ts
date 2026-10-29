/**
 * Texts of the Assistant's daily work outside its pages: the changes not
 * with customers yet and "Apply changes" (the banner over every page and
 * its sheet), and teaching it from conversations ("Fix this answer", "My
 * checks", "Answers worth improving").
 *
 * Top-level keys are namespaces. They are spread into the dictionaries of
 * every locale, so they must not clash with the namespaces of the other
 * dictionaries. The other languages are type-checked against `en`.
 */

import type { Translation } from "../../translate";
import { applyChangesEn } from "./assistant/applyChanges.en";
import { teachingEn } from "./assistant/teaching.en";
import { updatesEn } from "./assistant/updates.en";
import { applyChangesIt } from "./assistant/applyChanges.it";
import { teachingIt } from "./assistant/teaching.it";
import { updatesIt } from "./assistant/updates.it";

export const assistantFlowEn = {
  applyChanges: applyChangesEn,
  teaching: teachingEn,
  updates: updatesEn,
} as const;

export const assistantFlowIt: Translation<typeof assistantFlowEn> = {
  applyChanges: applyChangesIt,
  teaching: teachingIt,
  updates: updatesIt,
};
