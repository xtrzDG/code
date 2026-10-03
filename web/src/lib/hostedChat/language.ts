/**
 * The language of the hosted chat page (/c/{address}): the visitor's
 * browser languages (Accept-Language, best first) matched against the
 * business's customer languages, else the business's default language.
 * The widget on the page makes the same choice from navigator.languages,
 * so the page around it and the chat start in one language; a language the
 * visitor picks in the chat is the widget's own business.
 */

/** Right-to-left scripts among the languages the page has texts in. */
const RIGHT_TO_LEFT = new Set(["ar", "fa", "he", "ur"]);

/** The tags of an Accept-Language header, best first: "de-DE,ru;q=0.8" -> ["de-DE", "ru"]. */
export function rankAcceptLanguage(header: string | null | undefined): string[] {
  if (!header) {
    return [];
  }
  return header
    .split(",")
    .map((part, index) => {
      const [rawTag = "", ...parameters] = part.trim().split(";");
      const quality = parameters
        .map((parameter) => parameter.trim())
        .find((parameter) => parameter.startsWith("q="));
      const value = quality ? Number(quality.slice(2)) : 1;
      return { tag: rawTag.trim(), quality: Number.isFinite(value) ? value : 0, index };
    })
    .filter((entry) => entry.tag !== "" && entry.tag !== "*" && entry.quality > 0)
    .sort((left, right) => right.quality - left.quality || left.index - right.index)
    .map((entry) => entry.tag);
}

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

/** The page's language: the visitor's best match among `available`, else `fallback`. */
export function chooseLanguage(
  acceptLanguage: string | null | undefined,
  available: readonly string[],
  fallback: string,
): string {
  for (const candidate of rankAcceptLanguage(acceptLanguage)) {
    const match = matchLanguage(candidate, available);
    if (match) {
      return match;
    }
  }
  return fallback;
}

export function directionOf(tag: string): "rtl" | "ltr" {
  return RIGHT_TO_LEFT.has(primaryLanguage(tag)) ? "rtl" : "ltr";
}
