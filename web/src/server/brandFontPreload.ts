import "server-only";

import { readdirSync } from "node:fs";
import path from "node:path";

import { preload } from "react-dom";

import type { Locale } from "@/i18n/config";
import { brandFontHrefs } from "@/lib/brandFonts";

/**
 * Preloads a cabinet page's brand font files, Latin and its own script's
 * (lib/brandFonts.ts): the root layout calls it for cabinet pages only, and
 * React puts the <link rel="preload"> tags in the head, so the files load
 * with the stylesheet and are there for the first paint. The production server reads its build's file names once; the
 * development server, whose files change as it compiles, on every page.
 */

const IS_PRODUCTION = process.env.NODE_ENV === "production";

/** `next build` writes to .next/static, `next dev` to .next/dev/static (the working directory is web/). */
const MEDIA_DIRECTORY = path.join(process.cwd(), ".next", ...(IS_PRODUCTION ? [] : ["dev"]), "static", "media");

let builtMediaFiles: readonly string[] | null = null;

function mediaFiles(): readonly string[] {
  if (builtMediaFiles !== null) {
    return builtMediaFiles;
  }
  let files: readonly string[];
  try {
    files = readdirSync(MEDIA_DIRECTORY);
  } catch {
    // No build output here (a test, a server started elsewhere): nothing to preload.
    files = [];
  }
  if (IS_PRODUCTION) {
    builtMediaFiles = files;
  }
  return files;
}

export function preloadBrandFonts(locale: Locale): void {
  for (const href of brandFontHrefs(locale, mediaFiles())) {
    preload(href, { as: "font", type: "font/woff2", crossOrigin: "anonymous" });
  }
}
