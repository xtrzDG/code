/**
 * The aliases of a knowledge item in the editor: the item's name in the
 * business's other languages, reviewed as chips. An approved alias is the
 * owner's; a suggested one came from the model and is not offered to
 * customers until the owner accepts it.
 */

import type { Schema } from "@/api/types";
import type { MessageKey } from "@/i18n/translate";

type AliasStatus = Schema<"KnowledgeAliasStatus">;

export interface AliasRow {
  language: string;
  text: string;
  status: AliasStatus;
}

/** The API's limits: three names per language, 200 characters each. */
const MAX_ALIASES_PER_LANGUAGE = 3;
export const MAX_ALIAS_LENGTH = 200;

export type AliasChange = { ok: true; rows: AliasRow[] } | { ok: false; error: MessageKey };

export function aliasRowsFrom(aliases: readonly AliasRow[] | undefined): AliasRow[] {
  return (aliases ?? []).map(({ language, text, status }) => ({
    language,
    text,
    status,
  }));
}

/**
 * The languages the editor offers names in, in the business's order: the
 * ones the item is not written in (all of them when the item names none),
 * and any language that already has a name (a synonym in the item's own
 * language stays visible and removable).
 */
export function aliasLanguages(
  businessLanguages: readonly string[],
  itemLanguages: readonly string[],
  rows: readonly AliasRow[] = [],
): string[] {
  return businessLanguages.filter(
    (language) => !itemLanguages.includes(language) || rows.some((row) => row.language === language),
  );
}

/**
 * The names in languages the business still uses: the API refuses a name
 * in any other language, so a language dropped from the business takes
 * its names with it when the owner next edits them.
 */
export function aliasesInLanguages(rows: readonly AliasRow[], businessLanguages: readonly string[]): AliasRow[] {
  return rows.filter((row) => businessLanguages.includes(row.language));
}

function folded(text: string): string {
  return text.normalize("NFKC").toLocaleLowerCase().replace(/\s+/g, " ").trim();
}

/** Add the owner's name in a language (approved at once). */
export function addAlias(rows: readonly AliasRow[], language: string, text: string): AliasChange {
  const cleaned = text.replace(/\s+/g, " ").trim();
  if (cleaned === "") {
    return { ok: false, error: "validation.required" };
  }
  if (cleaned.length > MAX_ALIAS_LENGTH) {
    return { ok: false, error: "knowledge.aliases.tooLong" };
  }
  const sameLanguage = rows.filter((row) => row.language === language);
  if (sameLanguage.some((row) => folded(row.text) === folded(cleaned))) {
    return { ok: false, error: "knowledge.aliases.duplicate" };
  }
  if (sameLanguage.length >= MAX_ALIASES_PER_LANGUAGE) {
    return { ok: false, error: "knowledge.aliases.tooMany" };
  }
  return {
    ok: true,
    rows: [...rows, { language, text: cleaned, status: "approved" }],
  };
}

/** The owner accepts a suggestion: it becomes theirs. */
export function acceptAlias(rows: readonly AliasRow[], index: number): AliasRow[] {
  return rows.map((row, position) => (position === index ? { ...row, status: "approved" } : row));
}

export function removeAlias(rows: readonly AliasRow[], index: number): AliasRow[] {
  return rows.filter((_, position) => position !== index);
}

/**
 * The form's names with the model's new suggestions joined: only for
 * languages the form has no name in, so the owner's unsaved work stays.
 */
export function mergeSuggestions(rows: readonly AliasRow[], stored: readonly AliasRow[]): AliasRow[] {
  const covered = new Set(rows.map((row) => row.language));
  return [...rows, ...stored.filter((row) => row.status === "suggested" && !covered.has(row.language))];
}

export function countSuggested(rows: readonly AliasRow[]): number {
  return rows.filter((row) => row.status === "suggested").length;
}

export function sameAliases(left: readonly AliasRow[], right: readonly AliasRow[]): boolean {
  return (
    left.length === right.length &&
    left.every(
      (row, index) =>
        row.language === right[index]?.language &&
        row.text === right[index]?.text &&
        row.status === right[index]?.status,
    )
  );
}
