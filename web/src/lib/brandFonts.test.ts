import { readFileSync } from "node:fs";
import path from "node:path";

import { describe, expect, it } from "vitest";

import { LOCALES } from "@/i18n/config";

import { BRAND_TYPEFACE_CLASS, LATIN_FONT_FILE, SCRIPT_FONT_OF_LOCALE, brandFontHrefs, type ScriptFontFile } from "./brandFonts";

/** A listing of the build's static media as `next build` (Turbopack) leaves it. */
const MEDIA = [
  "favicon.0osvh44es2qhp.ico",
  "noto-sans-cyrillic-wght.3zok7wrwvaysp.woff2",
  "noto-sans-georgian-wght.3v3gllle3jls7.woff2",
  "noto-sans-hebrew-wght.1c3_izrpi4_9e.woff2",
  "noto-sans-latin-ext-wght.16m2fuqai051q.woff2",
  "noto-sans-latin-wght.05o5-i1cea2yx.woff2",
];

const LATIN = "/_next/static/media/noto-sans-latin-wght.05o5-i1cea2yx.woff2";
const GEORGIAN = "/_next/static/media/noto-sans-georgian-wght.3v3gllle3jls7.woff2";

/** The script files typeface.css keeps for a language that joins (no cabinet language needs one today). */
const SCRIPT_FILES: readonly ScriptFontFile[] = ["noto-sans-cyrillic-wght", "noto-sans-georgian-wght", "noto-sans-hebrew-wght"];

/** What a language with its own script would declare: here Italian standing in for one written in Georgian. */
const WITH_GEORGIAN = { en: null, it: "noto-sans-georgian-wght" } as const;

describe("the brand font files a cabinet page preloads", () => {
  it("are Latin alone for English and Italian, never the extended Latin file", () => {
    expect(brandFontHrefs("en", MEDIA)).toEqual([LATIN]);
    expect(brandFontHrefs("it", MEDIA)).toEqual([LATIN]);
    expect(LOCALES.every((locale) => SCRIPT_FONT_OF_LOCALE[locale] === null)).toBe(true);
  });

  it("are Latin and the file of the language's own script, for a language that declares one", () => {
    expect(brandFontHrefs("it", MEDIA, WITH_GEORGIAN)).toEqual([LATIN, GEORGIAN]);
    expect(brandFontHrefs("it", MEDIA, { en: null, it: "noto-sans-cyrillic-wght" })).toEqual([
      LATIN,
      "/_next/static/media/noto-sans-cyrillic-wght.3zok7wrwvaysp.woff2",
    ]);
    expect(brandFontHrefs("it", MEDIA, { en: null, it: "noto-sans-hebrew-wght" })).toEqual([
      LATIN,
      "/_next/static/media/noto-sans-hebrew-wght.1c3_izrpi4_9e.woff2",
    ]);
    expect(brandFontHrefs("en", MEDIA, WITH_GEORGIAN)).toEqual([LATIN]);
  });

  it("leave out rather than guess a file the build holds not once", () => {
    expect(brandFontHrefs("it", [], WITH_GEORGIAN)).toEqual([]);
    expect(brandFontHrefs("it", [...MEDIA, "noto-sans-georgian-wght.0ld0ne0ld0ne.woff2"], WITH_GEORGIAN)).toEqual([LATIN]);
    // Another file whose name begins alike is not the Georgian one.
    expect(brandFontHrefs("it", ["noto-sans-georgian-wght-old.3v3gllle3jls7.woff2", "noto-sans-georgian-wght.css"], WITH_GEORGIAN)).toEqual([]);
  });

  it("name files typeface.css loads", () => {
    const typeface = readFileSync(path.resolve(__dirname, "..", "styles", "typeface.css"), "utf8");
    const declared = LOCALES.map((locale) => SCRIPT_FONT_OF_LOCALE[locale]).filter((file) => file !== null);
    for (const file of [LATIN_FONT_FILE, ...SCRIPT_FILES, ...declared]) {
      expect(typeface, file).toContain(`url("../../public/fonts/${file}.woff2")`);
    }
  });
});

describe("the public site's fonts", () => {
  it("are the system's: the root layout gives the brand class and preloads to cabinet pages only", () => {
    const layout = readFileSync(path.resolve(__dirname, "..", "app", "layout.tsx"), "utf8");
    expect(layout).toMatch(/const isCabinetPage = clientTexts\.scope === "full";/);
    expect(layout).toMatch(/if \(isCabinetPage\) \{\s*preloadBrandFonts\(locale\);\s*\}/);
    expect(layout).toContain('className={cn("h-full", isCabinetPage && BRAND_TYPEFACE_CLASS)}');
    const typeface = readFileSync(path.resolve(__dirname, "..", "styles", "typeface.css"), "utf8");
    expect(typeface).toContain(`.${BRAND_TYPEFACE_CLASS} {`);
  });
});
