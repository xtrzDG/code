/**
 * The language of the hosted chat page (/c/{address}): the visitor's
 * browser languages (Accept-Language, best first) matched against the
 * business's customer languages, else the business's default language.
 * The widget on the page makes the same choice from navigator.languages,
 * so the page around it and the chat start in one language; a language the
 * visitor picks in the chat is the widget's own business.
 */

import { acceptLanguageTags } from "../landing";
import { matchLanguage } from "./language";

/** The page's language: the visitor's best match among `available`, else `fallback`. */
export function chooseLanguage(
  acceptLanguage: string | null | undefined,
  available: readonly string[],
  fallback: string,
): string {
  for (const candidate of acceptLanguageTags(acceptLanguage)) {
    const match = matchLanguage(candidate, available);
    if (match) {
      return match;
    }
  }
  return fallback;
}
