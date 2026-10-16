/**
 * Language names as labels. The interface languages read the backend's CLDR
 * table (displayNames.generated.ts, some 25 KB), so this sits apart from
 * format.ts: only the pages that name languages load it.
 */

import { capitalizeFirst } from "./capitalize";
import { LANGUAGE_NAMES } from "./displayNames.generated";

/**
 * A language tag as a label in the locale: languageName("ka", "ru") ->
 * "Грузинский". The interface languages read the backend's CLDR table (the
 * same on the server and in every browser; Chrome has no Georgian language
 * names); other tags and languages ask Intl.
 */
export function languageName(tag: string, locale: string): string {
  const known = LANGUAGE_NAMES[locale.split(/[-_]/)[0]?.toLowerCase() ?? locale]?.[tag];
  if (known) {
    return capitalizeFirst(known, locale);
  }
  try {
    return capitalizeFirst(new Intl.DisplayNames([locale], { type: "language" }).of(tag) ?? tag, locale);
  } catch {
    return tag;
  }
}
