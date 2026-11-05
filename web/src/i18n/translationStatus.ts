/**
 * How far a dictionary is translated, against English: which texts are
 * missing, which are left over, and the share that is there. A plural
 * text (an object with `other`) counts as one text whatever categories
 * its language uses.
 *
 * Used by `scripts/translation-status.mjs` (a translator's report and the
 * texts still to translate) and by the dictionary tests. No path aliases:
 * Node imports this file with its type syntax stripped.
 */

export type TextTree = { readonly [key: string]: string | TextTree | undefined };

export interface TranslationStatus {
  /** Texts of the English reference. */
  total: number;
  /** Paths English has and the dictionary lacks. */
  missing: string[];
  /** Paths the dictionary has and English does not (stale keys). */
  extra: string[];
  /** Whole percent of the English texts that are translated. */
  percent: number;
}

const isPlural = (value: TextTree): boolean => typeof value.other === "string";

/** Every text of a tree by its dotted path: "common.save", "billing.notices.trialTitle". */
export function textPaths(tree: TextTree, prefix = ""): Map<string, string | TextTree> {
  const paths = new Map<string, string | TextTree>();
  for (const [key, value] of Object.entries(tree)) {
    if (value === undefined) {
      continue;
    }
    const path = `${prefix}${key}`;
    if (typeof value === "string" || isPlural(value)) {
      paths.set(path, value);
    } else {
      for (const [inner, text] of textPaths(value, `${path}.`)) {
        paths.set(inner, text);
      }
    }
  }
  return paths;
}

export function translationStatus(reference: TextTree, dictionary: TextTree): TranslationStatus {
  const english = textPaths(reference);
  const translated = textPaths(dictionary);
  const missing = [...english.keys()].filter((path) => !translated.has(path));
  const extra = [...translated.keys()].filter((path) => !english.has(path));
  const total = english.size;
  const percent = total === 0 ? 100 : Math.floor(((total - missing.length) / total) * 100);
  return { total, missing, extra, percent };
}

/** The English texts still to translate, by path: the brief for a translator. */
export function missingTexts(reference: TextTree, dictionary: TextTree): Record<string, string | TextTree> {
  const english = textPaths(reference);
  return Object.fromEntries(translationStatus(reference, dictionary).missing.map((path) => [path, english.get(path) ?? ""]));
}
