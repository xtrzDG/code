/**
 * The brand typeface on a first visit (src/styles/typeface.css): with
 * `display: "optional"` a file that is late for the first paint stays out of
 * the whole document, and the cabinet changes pages without a new one. So a
 * cabinet page, in English or Italian, preloads the Latin file with the
 * stylesheet, at the very address its @font-face loads (one download), and
 * that face has loaded once the page has; the other scripts' files (a
 * customer's name or message) come only when such a character is shown. The
 * public site keeps the system's fonts: it preloads and fetches no font file
 * (its LCP waits for none).
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

/** The address each @font-face of the page's stylesheets loads, by its family. */
function fontFaces(page: Page): Promise<{ family: string; src: string }[]> {
  return page.evaluate(() =>
    [...document.styleSheets].flatMap((sheet) =>
      [...sheet.cssRules]
        .filter((rule): rule is CSSFontFaceRule => rule instanceof CSSFontFaceRule)
        .map((rule) => ({
          family: rule.style.getPropertyValue("font-family").replace(/["']/g, ""),
          src: new URL(/url\(["']?([^"')]+)/.exec(rule.style.getPropertyValue("src"))?.[1] ?? "", sheet.href ?? location.href).href,
        })),
    ),
  );
}

/** The Latin file of typeface.css: digits, punctuation and every English and Italian word. */
const LATIN = { family: "Brand Latin", file: "noto-sans-latin-wght" };

test.describe("the brand typeface", () => {
  for (const locale of ["en", "it"] as const) {
    test(`a page in ${locale} preloads Latin alone, the file its @font-face loads`, async ({ page }) => {
      await page.context().addCookies([{ name: "aw_locale", value: locale, url: WEB_URL }]);
      await page.goto("/login");
      await expect(page.locator("html")).toHaveAttribute("lang", locale);

      const preloaded = await preloadedFonts(page);
      expect(preloaded.map((href) => href.split("/").at(-1)?.split(".")[0]), "Latin alone").toEqual([LATIN.file]);

      // The preload is the very file the Latin @font-face loads: one download, used at once.
      const face = (await fontFaces(page)).find((rule) => rule.family === LATIN.family);
      expect(face?.src).toBe(preloaded[0]);
      await page.evaluate(() => document.fonts.ready);
      const downloads = await page.evaluate(
        (file) => performance.getEntriesByType("resource").filter((entry) => entry.name.includes(`/${file}.`)).length,
        LATIN.file,
      );
      expect(downloads, "fetched once").toBe(1);
      // And it has loaded: the face of the page's own letters is ready.
      const status = await page.evaluate(
        (family) => [...document.fonts].find((font) => font.family.replace(/["']/g, "") === family)?.status,
        LATIN.family,
      );
      expect(status).toBe("loaded");
    });
  }

  for (const address of ["/en", "/it/for/hotel"]) {
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
