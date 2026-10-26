/**
 * One screenshot of the visual tests: a page in a theme and a language,
 * settled, passed through the review gate (gate.ts), then compared with
 * its baseline, e2e/visual/__screenshots__/<spec>/<screen>-<width>-<theme>-<locale>.png.
 *
 * Every picture is the viewport (not the full page) at one device pixel
 * per CSS pixel: 1440×900 or the phone's 390×844. Animations are off
 * (reduced motion, `animations: "disabled"`), the caret is hidden, the
 * browser's clock stands still (clock.ts) and the fonts are the cabinet's
 * own files, waited for (fonts.ts), so a page renders the same
 * pixels on every run; `mask` paints
 * over what still changes (a QR code with a one-time token, the time of
 * something the run itself created). Checks and comparisons are soft: one
 * run lists every finding of a test, not only the first.
 */

import type { Locator, Page } from "@playwright/test";

import { WEB_URL } from "../support/env";
import { expect, test as base } from "../support/fixtures";
import { waitForNetworkQuiet } from "../support/network";
import { VISUAL_VIEW_TIME } from "./clock";
import { blockOnBrandFonts } from "./fonts";
import { reviewPage, watchConsole } from "./gate";

/** No request for this long: the page's data has come (a business page's chained reads start within it). */
const SETTLED_MS = 300;

export type Theme = "dark" | "light";
export type Locale = "ru" | "en" | "ka" | "he";

export const THEMES: readonly Theme[] = ["dark", "light"];
/** The languages of the full matrix (README "Visual tests and the review gate"). */
export const MATRIX_LOCALES: readonly Locale[] = ["ru", "en", "ka"];

export interface Shot {
  /** The screen, e.g. "restaurant-overview": the baseline's name starts with it. */
  name: string;
  path: string;
  theme: Theme;
  locale: Locale;
  /** Painted over in the picture: what changes from run to run. */
  mask?: (page: Page) => Locator[];
  /** A reading page of the public site (the landing, a help article) may be longer than four phone screens. */
  isDocument?: boolean;
}

/** The suite's `test`: the browser's clock standing still, the typeface cached, the console watched per screen. */
export const test = base.extend<{ visualPage: void }>({
  visualPage: [
    async ({ page }, use) => {
      await page.clock.setFixedTime(VISUAL_VIEW_TIME);
      await blockOnBrandFonts(page);
      watchConsole(page);
      await use();
    },
    { auto: true },
  ],
});

export { expect };

/** The theme and the language of the next page this context opens. */
export async function readAs(page: Page, theme: Theme, locale: Locale): Promise<void> {
  await page.context().addCookies([
    { name: "aw_theme", value: theme, url: WEB_URL, sameSite: "Lax" },
    { name: "aw_locale", value: locale, url: WEB_URL, sameSite: "Lax" },
  ]);
}

/** Until the page has its data, its fonts and its pictures, and nothing is loading. */
export async function settle(page: Page): Promise<void> {
  await expect(page.locator("h1").first()).toBeAttached();
  await waitForNetworkQuiet(page, { quietMs: SETTLED_MS });
  await expect(page.locator('[aria-busy="true"]:visible')).toHaveCount(0);
  await page.waitForFunction(() => [...document.images].every((image) => image.complete));
  await page.evaluate(async () => {
    await document.fonts.ready;
  });
}

/** The baseline's file name: screen, width, theme, language. */
export function shotName(shot: Pick<Shot, "name" | "theme" | "locale">, width: number): string {
  return `${shot.name}-${width}-${shot.theme}-${shot.locale}.png`;
}

/** Opens the page as `shot` says, checks it (gate.ts) and compares its picture with the baseline. */
export async function shoot(page: Page, shot: Shot): Promise<void> {
  const width = page.viewportSize()?.width ?? 0;
  const name = shotName(shot, width);
  await test.step(name, async () => {
    await readAs(page, shot.theme, shot.locale);
    const response = await page.goto(shot.path);
    expect(response?.status(), `${shot.path} answers`).toBeLessThan(400);
    await settle(page);
    await reviewPage(page, { label: `${name} (${shot.path})`, isDocument: shot.isDocument ?? false });
    await expect.soft(page, name).toHaveScreenshot(name, { mask: shot.mask?.(page) ?? [] });
  });
}

/** Every theme and language of the full matrix, at the context's width. */
export function matrix(shot: Omit<Shot, "theme" | "locale">): Shot[] {
  return THEMES.flatMap((theme) => MATRIX_LOCALES.map((locale) => ({ ...shot, theme, locale })));
}
