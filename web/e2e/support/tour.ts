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
 * Its routes (below) are every page of the cabinet; the visual tests
 * (e2e/visual) take a picture of each of them.
 */

import type { Page } from "@playwright/test";

import { policyViolations, watchPolicyViolations } from "./csp";
import { WEB_URL } from "./env";
import { expect } from "./fixtures";
import { waitForNetworkQuiet } from "./network";

const TBILISI = "Asia/Tbilisi";
/** A page walk opens every route twice and waits for the network each time. */
export const TOUR_TIMEOUT_MS = 240_000;

/**
 * Opens a route as a first-time reader and again with the remembered zone;
 * neither view may break the Content Security Policy (support/csp.ts).
 */
export async function visitTwice(page: Page, path: string): Promise<void> {
  await watchPolicyViolations(page);
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
    expect(await policyViolations(page), `${path} (${visit}) broke the Content Security Policy`).toEqual([]);
  }
  const cookie = (await page.context().cookies(WEB_URL)).find((item) => item.name === "aw_tz");
  expect(decodeURIComponent(cookie?.value ?? ""), `the browser remembered its zone on ${path}`).toBe(TBILISI);
}

/** The public pages (the hosted chat page and its notice come from `chatPageRoutes`). */
export const PUBLIC_ROUTES = ["/", "/login", "/help", "/help/inbox", "/help/whats-new", "/status"] as const;

/** A business's hosted chat page and its privacy notice. */
export function chatPageRoutes(slug: string): string[] {
  return [`/c/${slug}`, `/c/${slug}/privacy`];
}

/** The platform admin's pages, with one client's card. */
export function adminRoutes(clientBusinessId: string): string[] {
  return [
    "/admin",
    "/admin/system",
    "/admin/metrics",
    "/admin/team",
    "/admin/security",
    "/admin/niches",
    "/admin/niches/restaurant",
    `/admin/clients/${clientBusinessId}`,
  ];
}

/** An owner's business pages (the businesses first). */
export function businessRoutes(businessId: string): string[] {
  const business = `/b/${businessId}`;
  return [
    "/businesses",
    `${business}/overview`,
    `${business}/overview/reports`,
    `${business}/inbox`,
    `${business}/inbox?view=all`,
    `${business}/bookings`,
    `${business}/bookings/waitlist`,
    `${business}/bookings/return-visits`,
    `${business}/assistant`,
    `${business}/assistant/versions`,
    `${business}/assistant/checks`,
    `${business}/assistant/knowledge`,
    `${business}/assistant/knowledge/questions`,
    `${business}/assistant/knowledge/resources`,
    `${business}/assistant/knowledge/import`,
    `${business}/assistant/profile`,
    `${business}/assistant/channels`,
    `${business}/assistant/channels/website`,
    `${business}/assistant/channels/calls`,
    `${business}/assistant/channels/share`,
  ];
}

/** An owner's settings and account pages. */
export function settingsRoutes(businessId: string): string[] {
  const settings = `/b/${businessId}/settings`;
  return [
    settings,
    `${settings}/team`,
    `${settings}/billing`,
    `${settings}/privacy`,
    `${settings}/notifications`,
    `${settings}/calls`,
    `${settings}/reviews`,
    `${settings}/quick-replies`,
    `${settings}/audit`,
    "/account/security",
  ];
}

/** Times on a page without a business are in the reader's zone once it is known: never labelled "UTC". */
export async function expectReaderZone(page: Page): Promise<void> {
  await expect(page.getByText(/\d{1,2}:\d{2}[^\n]*\bUTC\b/)).toHaveCount(0);
}

/** An owner's pages are read in English and again in Italian (the platform's Intl on both sides). */
export const TOUR_LOCALES = ["en", "it"] as const;

/** Reads the cabinet in this language from now on. */
export async function readIn(page: Page, locale: (typeof TOUR_LOCALES)[number]): Promise<void> {
  await page.context().addCookies([{ name: "aw_locale", value: locale, url: WEB_URL }]);
}
