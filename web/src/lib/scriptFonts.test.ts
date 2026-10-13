import { readFileSync } from "node:fs";
import path from "node:path";

import { describe, expect, it } from "vitest";

import { LOCALES } from "@/i18n/config";

import { SCRIPT_FONT_OF_LOCALE, scriptFontHref } from "./scriptFonts";

/** A listing of the build's static media as `next build` (Turbopack) leaves it. */
const MEDIA = [
  "favicon.0osvh44es2qhp.ico",
  "noto_sans_cyrillic_wght.3zok7wrwvaysp.woff2",
  "noto_sans_georgian_wght.3v3gllle3jls7.woff2",
  "noto_sans_hebrew_wght.1c3_izrpi4_9e.woff2",
  "noto_sans_latin_ext_wght.16m2fuqai051q.woff2",
  "noto_sans_latin_wght-s.p.05o5-i1cea2yx.woff2",
];

describe("the script font a page preloads", () => {
  it("is the file of the language's own script", () => {
    expect(scriptFontHref("ka", MEDIA)).toBe("/_next/static/media/noto_sans_georgian_wght.3v3gllle3jls7.woff2");
    expect(scriptFontHref("ru", MEDIA)).toBe("/_next/static/media/noto_sans_cyrillic_wght.3zok7wrwvaysp.woff2");
    expect(scriptFontHref("he", MEDIA)).toBe("/_next/static/media/noto_sans_hebrew_wght.1c3_izrpi4_9e.woff2");
  });

  it("is none for English and German: Latin is preloaded on every page", () => {
    expect(scriptFontHref("en", MEDIA)).toBeNull();
    expect(scriptFontHref("de", MEDIA)).toBeNull();
  });

  it("is none rather than a guess when the build holds no such file or two of them", () => {
    expect(scriptFontHref("ka", [])).toBeNull();
    expect(scriptFontHref("ka", [...MEDIA, "noto_sans_georgian_wght.0ld0ne0ld0ne.woff2"])).toBeNull();
    // Another file whose name begins alike is not the Georgian one.
    expect(scriptFontHref("ka", ["noto_sans_georgian_wght_old.3v3gllle3jls7.woff2", "noto_sans_georgian_wght.css"])).toBeNull();
  });

  it("names a file fonts.ts loads, not preloaded for every page, in every language that needs one", () => {
    const fonts = readFileSync(path.resolve(__dirname, "..", "app", "fonts.ts"), "utf8");
    for (const locale of LOCALES) {
      const file = SCRIPT_FONT_OF_LOCALE[locale];
      if (file === null) {
        continue;
      }
      const source = `public/fonts/${file.replaceAll("_", "-")}.woff2`;
      const face = /localFont\(\{([\s\S]*?)\n\}\);/g;
      const body = [...fonts.matchAll(face)].map((match) => match[1] ?? "").find((call) => call.includes(source));
      expect(body, `${source} in fonts.ts`).toBeDefined();
      expect(body).toContain("preload: false");
    }
  });
});
