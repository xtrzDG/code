/**
 * The cabinet's typeface in the pictures. Its faces are `font-display:
 * optional` (src/styles/typeface.css): a file that is not there within
 * about 100 ms of being needed is dropped for the whole page, which keeps
 * the fallback font. On a busy machine even a file from the cache can miss
 * that window, and the same page would be drawn in the fallback on one run
 * and in Noto Sans on the next.
 *
 * So every browser context of the visual tests first reads the faces from
 * the stylesheet and loads them all into its cache, then declares each one
 * again on every page it opens, with `font-display: block`: a face added
 * through the CSS Font Loading API comes after the stylesheet's own and
 * wins for the same family and descriptors, so the text waits for the
 * cabinet's own file instead of taking the fallback. The files and their
 * metrics are the cabinet's; only the waiting differs.
 */

import { expect, type Page } from "@playwright/test";

import { WEB_URL } from "../support/env";

interface BrandFace {
  family: string;
  src: string;
  unicodeRange: string;
  weight: string;
  style: string;
}

/** The typeface's faces as the stylesheet declares them (the local Arial fallback left out). */
async function brandFaces(page: Page): Promise<BrandFace[]> {
  return page.evaluate(() => {
    const faces: BrandFace[] = [];
    for (const sheet of document.styleSheets) {
      for (const rule of sheet.cssRules) {
        if (!(rule instanceof CSSFontFaceRule) || !rule.style.getPropertyValue("src").includes("url(")) {
          continue;
        }
        // The addresses are relative to the stylesheet, the new faces' to the page.
        const base = sheet.href ?? location.href;
        const src = rule.style
          .getPropertyValue("src")
          .replace(/url\(\s*["']?([^"')]+)["']?\s*\)/g, (_, address: string) => `url("${new URL(address, base).href}")`);
        faces.push({
          family: rule.style.getPropertyValue("font-family").replace(/^["']|["']$/g, ""),
          src,
          unicodeRange: rule.style.getPropertyValue("unicode-range") || "U+0-10FFFF",
          weight: rule.style.getPropertyValue("font-weight") || "normal",
          style: rule.style.getPropertyValue("font-style") || "normal",
        });
      }
    }
    return faces;
  });
}

/** Loads every face of the typeface into the context's cache and makes every page of the context wait for them. */
export async function blockOnBrandFonts(page: Page): Promise<void> {
  // With a language cookie the sign-in page's prefetches of the public site
  // set none; one of them arriving late would otherwise change the
  // language a test has just chosen.
  await page.context().addCookies([{ name: "aw_locale", value: "en", url: WEB_URL, sameSite: "Lax" }]);
  await page.goto("/login");
  const faces = await brandFaces(page);
  expect(faces.length, "the stylesheet declares the typeface").toBeGreaterThan(0);
  // On every later page: the faces, waited for wherever a text needs them.
  const declare = ({ origin, declared }: { origin: string; declared: BrandFace[] }) => {
    // Only the cabinet's own pages (not about:blank): the files' addresses are its.
    if (location.origin !== origin) {
      return;
    }
    for (const face of declared) {
      const { family, src, ...descriptors } = face;
      document.fonts.add(new FontFace(family, src, { ...descriptors, display: "block" }));
    }
  };
  const origin = new URL(WEB_URL).origin;
  await page.context().addInitScript(declare, { origin, declared: faces });
  // Into the cache now, every script's file.
  await page.evaluate(async (declared) => {
    await Promise.all(declared.map(({ family, src, ...descriptors }) => new FontFace(family, src, descriptors).load()));
  }, faces);
  await page.goto("about:blank");
}
