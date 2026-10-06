/**
 * Every route of the screenshot tour (README "Run" of the scratch tour),
 * read by a browser in Tbilisi (UTC+4, the "tz-tbilisi" project) from a
 * cabinet server in UTC (playwright.config.ts). Each page is opened twice:
 * first as a first-time reader (no `aw_tz` cookie yet: the server renders
 * times in UTC with the label, the browser switches to its own zone after
 * hydration), then reloaded with the cookie the first visit left (the
 * server renders the reader's zone itself). A date or time formatted
 * without its zone would differ between the two and React would throw its
 * hydration error (#418), which the console-clean gate turns into a
 * failure; so would any other console error.
 */

import type { Page } from "@playwright/test";

import { ensureOnAdminTeam, signInAsPlatformAdmin } from "./support/admin";
import { signInAsDemoOwner } from "./support/demo";
import { TOUR_ADMIN_EMAIL, WEB_URL } from "./support/env";
import { expect, signInContext, test } from "./support/fixtures";
import { openChatBusiness } from "./support/hosted-chat";
import { waitForNetworkQuiet } from "./support/network";

const TBILISI = "Asia/Tbilisi";

/** Opens a route as a first-time reader and again with the remembered zone. */
async function visitTwice(page: Page, path: string): Promise<void> {
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
async function expectReaderZone(page: Page): Promise<void> {
  await expect(page.getByText(/\d{1,2}:\d{2}[^\n]*\bUTC\b/)).toHaveCount(0);
}

test.describe.configure({ timeout: 240_000 });

test("the public pages", async ({ page, request, account }) => {
  // Its own business with the chat on, for the hosted chat page and its notice.
  const chat = await openChatBusiness(request, account.token);
  await page.context().clearCookies({ name: "aw_session" });
  for (const path of ["/", "/login", "/help", "/help/inbox", "/help/whats-new", "/status", `/c/${chat.slug}`, `/c/${chat.slug}/privacy`]) {
    await visitTwice(page, path);
  }
  await expectReaderZone(page);
});

test("an owner's business pages", async ({ page, owner }) => {
  const business = `/b/${owner.businessId}`;
  for (const path of [
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
  ]) {
    await visitTwice(page, path);
  }
});

test("an owner's settings and account pages", async ({ page, owner }) => {
  const settings = `/b/${owner.businessId}/settings`;
  for (const path of [
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
  ]) {
    await visitTwice(page, path);
  }
  // Account → Security: its dates are the reader's (React #418 here was the tour's finding).
  await expectReaderZone(page);
});

test("the demo restaurant's conversations, bookings and value", async ({ page, request, context }) => {
  const demo = await signInAsDemoOwner(request);
  await signInContext(context, demo.token);
  const business = `/b/${demo.businessId}`;
  for (const path of [`${business}/overview`, `${business}/inbox?view=all`, `${business}/bookings`, `${business}/bookings/waitlist`, `${business}/overview/reports`]) {
    await visitTwice(page, path);
  }
  await page.goto(`${business}/inbox?view=all`);
  await page.locator(`a[href^="${business}/inbox/conversation_"]`).first().click();
  await expect(page).toHaveURL(new RegExp(`${business}/inbox/conversation_`));
  await visitTwice(page, new URL(page.url()).pathname);
});

test("the platform admin's pages", async ({ page, request, context, owner }) => {
  await ensureOnAdminTeam(request, TOUR_ADMIN_EMAIL);
  await signInContext(context, await signInAsPlatformAdmin(request, TOUR_ADMIN_EMAIL));
  for (const path of ["/admin", "/admin/system", "/admin/metrics", "/admin/team", "/admin/security", `/admin/clients/${owner.businessId}`]) {
    await visitTwice(page, path);
  }
  await expectReaderZone(page);
});
