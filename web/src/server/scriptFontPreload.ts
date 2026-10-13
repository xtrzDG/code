import "server-only";

import { readdirSync } from "node:fs";
import path from "node:path";

import { preload } from "react-dom";

import type { Locale } from "@/i18n/config";
import { scriptFontHref } from "@/lib/scriptFonts";

/**
 * Preloads the brand font file of the page's own script (lib/scriptFonts.ts):
 * the root layout calls it, and React puts the <link rel="preload"> in the
 * head, so the file loads with the stylesheet and is there for the first
 * paint. The production server reads its build's file names once; the
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

export function preloadScriptFont(locale: Locale): void {
  const href = scriptFontHref(locale, mediaFiles());
  if (href !== null) {
    preload(href, { as: "font", type: "font/woff2", crossOrigin: "anonymous" });
  }
}
