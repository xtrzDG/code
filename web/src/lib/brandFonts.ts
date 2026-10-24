/**
 * The cabinet's typeface (src/styles/typeface.css): the class that turns it
 * on and the files a cabinet page preloads.
 *
 * The public site (the landing, niche and legal pages) keeps the system's
 * fonts and loads none: its first paint waits for nothing but its HTML and
 * stylesheet. The cabinet uses the brand typeface, and with
 * `font-display: optional` a file that is not there within about 100 ms of
 * being needed is dropped for the rest of the document, while the cabinet
 * changes pages without a new document. So the root layout preloads, on
 * cabinet pages only, Latin (digits, punctuation, every English and German
 * word) and the one script file the page's language needs, as the build
 * emitted them (`<file name>.<content hash>.woff2` in its static media).
 */

import type { Locale } from "@/i18n/config";

/** On <html>, the class under which --font-sans names the brand faces (cabinet pages). */
export const BRAND_TYPEFACE_CLASS = "brand-typeface";

/** The script files of typeface.css preloaded per language, by their name in public/fonts/. */
export type ScriptFontFile = "noto-sans-cyrillic-wght" | "noto-sans-georgian-wght" | "noto-sans-hebrew-wght";

/** The Latin file, preloaded on every cabinet page. */
export const LATIN_FONT_FILE = "noto-sans-latin-wght";

type BrandFontFile = ScriptFontFile | typeof LATIN_FONT_FILE;

/** The file a language's own script needs beyond Latin (German and English: none). */
export const SCRIPT_FONT_OF_LOCALE: Record<Locale, ScriptFontFile | null> = {
  ka: "noto-sans-georgian-wght",
  ru: "noto-sans-cyrillic-wght",
  he: "noto-sans-hebrew-wght",
  en: null,
  de: null,
};

/** Where the build serves the files a stylesheet's url() names (its `static/media`). */
const MEDIA_PATH = "/_next/static/media/";

/** The emitted name of a font file: its name, then a content hash. */
function isEmittedFile(name: string, file: BrandFontFile): boolean {
  return name.startsWith(`${file}.`) && /^[a-z-]+\.[A-Za-z0-9_-]+\.woff2$/.test(name);
}

/** The address of `file` in a listing of the build's static media; null unless it holds exactly one. */
function emittedHref(file: BrandFontFile, mediaFiles: readonly string[]): string | null {
  const emitted = mediaFiles.filter((name) => isEmittedFile(name, file));
  return emitted.length === 1 ? `${MEDIA_PATH}${emitted[0]}` : null;
}

/**
 * The addresses a cabinet page in `locale` preloads: Latin, then its own
 * script's file when it needs one. A file the listing does not hold exactly
 * once is left out rather than guessed.
 */
export function brandFontHrefs(locale: Locale, mediaFiles: readonly string[]): string[] {
  const script = SCRIPT_FONT_OF_LOCALE[locale];
  const files: BrandFontFile[] = script === null ? [LATIN_FONT_FILE] : [LATIN_FONT_FILE, script];
  return files.map((file) => emittedHref(file, mediaFiles)).filter((href) => href !== null);
}
