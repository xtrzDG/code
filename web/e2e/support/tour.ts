/**
 * The route tour (e2e/tour-*.spec.ts): every route of the screenshot tour
 * (README "Run" of the scratch tour), read by a browser in Tbilisi (UTC+4,
 * the "tz-tbilisi" project of playwright.config.ts) from a cabinet server in
 * UTC. Each page is opened twice: first as a first-time reader (no `aw_tz`
 * cookie yet: the server renders times in UTC with the label, the browser
 * switches to its own zone after hydration), then reloaded with the cookie
 * the first visit left (the server renders the reader's zone itself). A
 * date or time formatted without its zone would differ between the two and
 * React would throw its hydration error (#418), which the console-clean
 * gate turns into a failure; so would any other console error.
 *
 * The tour is split into several spec files so that CI can spread it over
 * its shards (support/shards.ts); every file runs in the Tbilisi project.
 */

import type { Page } from "@playwright/test";

import { WEB_URL } from "./env";
import { expect } from "./fixtures";
import { waitForNetworkQuiet } from "./network";

const TBILISI = "Asia/Tbilisi";
/** A page walk opens every route twice and waits for the network each time. */
export const TOUR_TIMEOUT_MS = 240_000;

/** Opens a route as a first-time reader and again with the remembered zone. */
export async function visitTwice(page: Page, path: string): Promise<void> {
  // Clearing one cookie clears them all and adds the others back: a request
  // in flight meanwhile (the page a click just opened) goes without the
  // session and ends it. So the page settles first.
  await waitForNetworkQuiet(page);
  await page.context().clearCookies({ name: "aw_tz" });
  for (const visit of ["first", "remembered"] as const) {
    const response = await page.goto(path);
    expect(response?.status(), `${path} (${visit})`).toBeLessThan(400);
    await expect(page.locator("h1").first(), `${path} (${visit})`).toBeVisible();
    await waitForNetworkQuiet(page);
  }
  const cookie = (await page.context().cookies(WEB_URL)).find((item) => item.name === "aw_tz");
  expect(decodeURIComponent(cookie?.value ?? ""), `the browser remembered its zone on ${path}`).toBe(TBILISI);
}

/** Times on a page without a business are in the reader's zone once it is known: never labelled "UTC". */
export async function expectReaderZone(page: Page): Promise<void> {
  await expect(page.getByText(/\d{1,2}:\d{2}[^\n]*\bUTC\b/)).toHaveCount(0);
}

/** An owner's pages are read in English and again in Hebrew (right to left, the platform's Intl on both sides). */
export const TOUR_LOCALES = ["en", "he"] as const;

/** Reads the cabinet in this language from now on. */
export async function readIn(page: Page, locale: (typeof TOUR_LOCALES)[number]): Promise<void> {
  await page.context().addCookies([{ name: "aw_locale", value: locale, url: WEB_URL }]);
}
