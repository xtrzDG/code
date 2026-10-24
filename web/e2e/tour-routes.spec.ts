/**
 * The route tour, part one: the public pages, the demo restaurant and the
 * platform admin's pages, read from Tbilisi (support/tour.ts explains the
 * double visit). An owner's business pages are in
 * tour-routes-business.spec.ts, their settings in tour-routes-settings.spec.ts.
 */

import { ensureOnAdminTeam, signInAsPlatformAdmin } from "./support/admin";
import { signInAsDemoOwner } from "./support/demo";
import { TOUR_ADMIN_EMAIL } from "./support/env";
import { expect, signInContext, test } from "./support/fixtures";
import { openChatBusiness } from "./support/hosted-chat";
import { expectReaderZone, TOUR_TIMEOUT_MS, visitTwice } from "./support/tour";

test.describe.configure({ timeout: TOUR_TIMEOUT_MS });

test("the public pages", async ({ page, request, account }) => {
  // Its own business with the chat on, for the hosted chat page and its notice.
  const chat = await openChatBusiness(request, account.token);
  await page.context().clearCookies({ name: "aw_session" });
  for (const path of [
    "/",
    "/login",
    "/help",
    "/help/inbox",
    "/help/whats-new",
    "/status",
    `/c/${chat.slug}`,
    `/c/${chat.slug}/privacy`,
  ]) {
    await visitTwice(page, path);
  }
  await expectReaderZone(page);
});

test("the demo restaurant's conversations, bookings and value", async ({ page, request, context }) => {
  const demo = await signInAsDemoOwner(request);
  await signInContext(context, demo.token);
  const business = `/b/${demo.businessId}`;
  for (const path of [
    `${business}/overview`,
    `${business}/inbox?view=all`,
    `${business}/bookings`,
    `${business}/bookings/waitlist`,
    `${business}/overview/reports`,
  ]) {
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
  for (const path of [
    "/admin",
    "/admin/system",
    "/admin/metrics",
    "/admin/team",
    "/admin/security",
    `/admin/clients/${owner.businessId}`,
  ]) {
    await visitTwice(page, path);
  }
  await expectReaderZone(page);
});
