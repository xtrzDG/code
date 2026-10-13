/**
 * Which brand font file a page preloads for its language (src/app/fonts.ts).
 *
 * The Latin file is preloaded on every page by next/font. Georgian,
 * Cyrillic and Hebrew are not: every page would pay for scripts it does not
 * show. Yet with `display: "optional"` a file that is not there within about
 * 100 ms of being needed is dropped for the rest of the document, and the
 * cabinet changes pages without a new document: a Georgian, Russian or
 * Hebrew session would stay in the system's font. So the root layout
 * preloads the one script file its language needs, as next/font emitted it
 * (`<file name, - as _>.<content hash>.woff2` in the build's static media).
 */

import type { Locale } from "@/i18n/config";

/** The script files of fonts.ts preloaded per language, by the name next/font gives them. */
export type ScriptFontFile = "noto_sans_cyrillic_wght" | "noto_sans_georgian_wght" | "noto_sans_hebrew_wght";

/** The file a language's own script needs beyond Latin (German and English: none). */
export const SCRIPT_FONT_OF_LOCALE: Record<Locale, ScriptFontFile | null> = {
  ka: "noto_sans_georgian_wght",
  ru: "noto_sans_cyrillic_wght",
  he: "noto_sans_hebrew_wght",
  en: null,
  de: null,
};

/** Where next/font's files are served from (the build's `static/media`). */
const MEDIA_PATH = "/_next/static/media/";

/** The emitted name of a font file next/font does not preload: its name, then a content hash. */
function isEmittedFile(name: string, file: ScriptFontFile): boolean {
  return name.startsWith(`${file}.`) && /^[a-z_]+\.[A-Za-z0-9_-]+\.woff2$/.test(name);
}

/**
 * The address to preload for `locale`, found in a listing of the build's
 * static media; null when the language needs no script file, or when the
 * listing does not hold exactly one such file (then nothing is preloaded
 * rather than a file the page does not use).
 */
export function scriptFontHref(locale: Locale, mediaFiles: readonly string[]): string | null {
  const file = SCRIPT_FONT_OF_LOCALE[locale];
  if (file === null) {
    return null;
  }
  const emitted = mediaFiles.filter((name) => isEmittedFile(name, file));
  return emitted.length === 1 ? `${MEDIA_PATH}${emitted[0]}` : null;
}
