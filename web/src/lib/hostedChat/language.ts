/**
 * Language tags of the pages customers see (the hosted chat page, the
 * table card): matching a browser tag to the available ones, and the
 * direction of a language. negotiate.ts picks the page's language.
 */

/** Right-to-left scripts among the languages the page has texts in. */
const RIGHT_TO_LEFT = new Set(["ar", "fa", "he", "ur"]);

/** The first two letters of a tag, lower case: "pt-BR" -> "pt". */
export function primaryLanguage(tag: string): string {
  return tag.trim().toLowerCase().replace("_", "-").split("-")[0] ?? "";
}

/**
 * The available tag a browser tag stands for: the same tag, else the same
 * primary language ("en-GB" -> "en", "pt" -> "pt-BR"), else null.
 */
export function matchLanguage(candidate: string, available: readonly string[]): string | null {
  const wanted = candidate.trim().toLowerCase().replace("_", "-");
  if (!wanted) {
    return null;
  }
  const exact = available.find((tag) => tag.toLowerCase() === wanted);
  if (exact) {
    return exact;
  }
  const base = primaryLanguage(wanted);
  return available.find((tag) => primaryLanguage(tag) === base) ?? null;
}

export function directionOf(tag: string): "rtl" | "ltr" {
  return RIGHT_TO_LEFT.has(primaryLanguage(tag)) ? "rtl" : "ltr";
}
