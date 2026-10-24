/**
 * The brand typeface on a first visit (src/styles/typeface.css): with
 * `display: "optional"` a file that is late for the first paint stays out of
 * the whole document, and the cabinet changes pages without a new one. So a
 * Georgian, Russian or Hebrew page preloads its own script's file with the
 * stylesheet, at the very address its @font-face loads (one download), and
 * the face has loaded once the page has; an English page preloads Latin
 * alone. The public site keeps the system's fonts: it preloads and fetches
 * no font file (its LCP waits for none).
 */

import type { Page } from "@playwright/test";

import { WEB_URL } from "./support/env";
import { expect, test } from "./support/fixtures";

/** The font files the page's head preloads. */
function preloadedFonts(page: Page): Promise<string[]> {
  return page.evaluate(() =>
    [...document.querySelectorAll<HTMLLinkElement>('link[rel="preload"][as="font"]')].map((link) => link.href),
  );
}

/** The address each @font-face of the page's stylesheets loads, with its unicode-range. */
function fontFaces(page: Page): Promise<{ src: string; range: string }[]> {
  return page.evaluate(() =>
    [...document.styleSheets].flatMap((sheet) =>
      [...sheet.cssRules]
        .filter((rule): rule is CSSFontFaceRule => rule instanceof CSSFontFaceRule)
        .map((rule) => ({
          src: new URL(/url\(["']?([^"')]+)/.exec(rule.style.getPropertyValue("src"))?.[1] ?? "", sheet.href ?? location.href).href,
          range: rule.style.getPropertyValue("unicode-range"),
        })),
    ),
  );
}

const SCRIPTS = [
  { locale: "ka", file: "noto-sans-georgian-wght", range: "U+10A0-10FF" },
  { locale: "ru", file: "noto-sans-cyrillic-wght", range: "U+400-45F" },
  { locale: "he", file: "noto-sans-hebrew-wght", range: "U+590-5FF" },
] as const;

test.describe("the brand typeface", () => {
  for (const script of SCRIPTS) {
    test(`a page in ${script.locale} preloads its script's file, the one its @font-face loads`, async ({ page }) => {
      await page.context().addCookies([{ name: "aw_locale", value: script.locale, url: WEB_URL }]);
      await page.goto("/login");
      await expect(page.locator("html")).toHaveAttribute("lang", script.locale);

      const preloaded = await preloadedFonts(page);
      const own = preloaded.filter((href) => href.includes(`/${script.file}.`));
      expect(own, "the script's file is preloaded once").toHaveLength(1);
      expect(preloaded.filter((href) => href.includes("/noto-sans-latin-wght.")), "Latin is preloaded too").toHaveLength(1);

      // The preload is the very file the @font-face of that script loads: one download, used at once.
      const face = (await fontFaces(page)).find((rule) => rule.range.toUpperCase().includes(script.range));
      expect(face?.src).toBe(own[0]);
      await page.evaluate(() => document.fonts.ready);
      const downloads = await page.evaluate(
        (file) => performance.getEntriesByType("resource").filter((entry) => entry.name.includes(`/${file}.`)).length,
        script.file,
      );
      expect(downloads, "fetched once").toBe(1);
      // And it has loaded: the face of the page's own letters is ready.
      const status = await page.evaluate(
        (range) => [...document.fonts].find((font) => font.unicodeRange.toUpperCase().includes(range))?.status,
        script.range,
      );
      expect(status).toBe("loaded");
    });
  }

  test("an English page preloads Latin alone", async ({ page }) => {
    await page.context().addCookies([{ name: "aw_locale", value: "en", url: WEB_URL }]);
    await page.goto("/login");
    await expect(page.locator("html")).toHaveAttribute("lang", "en");
    const preloaded = await preloadedFonts(page);
    expect(preloaded.map((href) => href.split("/").at(-1)?.split(".")[0])).toEqual(["noto-sans-latin-wght"]);
  });

  for (const address of ["/en", "/ka/for/hotel"]) {
    test(`the public page ${address} keeps the system's fonts and fetches no font file`, async ({ page }) => {
      const fonts: string[] = [];
      page.on("request", (request) => {
        if (request.resourceType() === "font") {
          fonts.push(request.url());
        }
      });
      await page.goto(address);
      await page.evaluate(() => document.fonts.ready);
      expect(await preloadedFonts(page)).toEqual([]);
      expect(fonts).toEqual([]);
      const family = await page.evaluate(() => getComputedStyle(document.body).fontFamily);
      expect(family.startsWith("ui-sans-serif"), family).toBe(true);
    });
  }
});
