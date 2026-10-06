/**
 * Bookings → Waitlist and Return visits. The demo restaurant (SEED_DEMO_DATA)
 * has guests waiting for a full evening, one who got a freed table and one
 * who did not answer in time: staff see them by list and take a guest off
 * it. A new business's owner turns on the return-visit message (the
 * niche's usual rule a click away, a segment needed before writing to one)
 * and the choices stay; staff have the waitlist but not the messages.
 */

import { expect, test, signInContext } from "./support/fixtures";
import { inviteStaff, signInByEmail, uniqueEmail } from "./support/api";
import { signInAsDemoOwner } from "./support/demo";
import { en } from "./support/messages";

const waitlist = en.waitlist;
const returnVisits = en.returnVisits;
const pages = en.navigation.pages;

test("the demo restaurant's waitlist by list, and a guest taken off it", async ({ page, request, context }) => {
  const demo = await signInAsDemoOwner(request);
  await signInContext(context, demo.token);
  await page.goto(`/b/${demo.businessId}/bookings`);

  const tabs = page.getByRole("navigation", { name: en.navigation.sectionPages.replace("{section}", en.navigation.sections.bookings) });
  await tabs.getByRole("link", { name: pages.bookingsWaitlist }).click();
  await expect(page).toHaveURL(new RegExp(`/b/${demo.businessId}/bookings/waitlist$`));
  await expect(page.getByRole("heading", { level: 1, name: en.navigation.sections.bookings })).toBeVisible();
  await expect(page.getByRole("heading", { level: 2, name: pages.bookingsWaitlist })).toBeVisible();

  const entries = page.getByRole("article");
  await expect(entries.first()).toBeVisible();
  const waiting = await entries.count();
  expect(waiting).toBeGreaterThan(0);
  await expect(entries.first().getByText(waitlist.status.waiting)).toBeVisible();

  await page.getByText(waitlist.filters.booked, { exact: true }).click();
  await expect(page).toHaveURL(/\?filter=booked$/);
  await expect(entries.first().getByText(waitlist.status.booked, { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: new RegExp(waitlist.remove) })).toHaveCount(0);

  await page.getByText(waitlist.filters.ended, { exact: true }).click();
  await expect(entries.first().getByText(waitlist.endReasons.no_answer)).toBeVisible();

  await page.getByText(waitlist.filters.active, { exact: true }).click();
  await expect(entries).toHaveCount(waiting);
  const last = entries.last();
  const name = (await last.getAttribute("aria-label")) ?? "";
  await last.getByRole("button", { name: new RegExp(waitlist.remove) }).click();
  const dialog = page.getByRole("dialog", { name: waitlist.removeTitle.replace("{name}", name) });
  await dialog.getByRole("button", { name: waitlist.removeConfirm }).click();
  await expect(page.getByText(waitlist.removed)).toBeVisible();
  await expect(entries).toHaveCount(waiting - 1);
  await expect(page.getByRole("article", { name })).toHaveCount(0);
});

test("the owner turns the return-visit message on, and the choices stay", async ({ page, owner }) => {
  await page.goto(`/b/${owner.businessId}/bookings/return-visits`);
  await expect(page.getByRole("heading", { level: 2, name: pages.bookingsReturnVisits })).toBeVisible();

  const toggle = page.getByRole("switch", { name: returnVisits.settings.toggle });
  await expect(toggle).toHaveAttribute("aria-checked", "false");
  await expect(page.getByText(returnVisits.messages.empty)).toBeVisible();
  await expect(page.getByRole("heading", { name: returnVisits.preview.title })).toBeVisible();

  await toggle.click();
  // A segment is needed before writing to one; this business has none yet.
  await page.getByLabel(returnVisits.settings.audience).selectOption("segment");
  await expect(page.getByText(returnVisits.settings.noSegments)).toBeVisible();
  await page.getByRole("button", { name: returnVisits.settings.save }).click();
  await expect(page.getByText(returnVisits.settings.errors.segment)).toBeVisible();

  await page.getByLabel(returnVisits.settings.audience).selectOption("all_customers");
  await page.getByLabel(returnVisits.settings.daysAfter).fill("0");
  await page.getByRole("button", { name: returnVisits.settings.save }).click();
  await expect(page.getByText(returnVisits.settings.errors.days)).toBeVisible();

  await page.getByLabel(returnVisits.settings.daysAfter).fill("42");
  await page.getByLabel(returnVisits.settings.cap).fill("50");
  await page.getByRole("button", { name: returnVisits.settings.save }).click();
  await expect(page.getByText(returnVisits.settings.saved)).toBeVisible();

  await page.reload();
  await expect(page.getByRole("switch", { name: returnVisits.settings.toggle })).toHaveAttribute("aria-checked", "true");
  await expect(page.getByLabel(returnVisits.settings.daysAfter)).toHaveValue("42");
  await expect(page.getByLabel(returnVisits.settings.cap)).toHaveValue("50");
  // The niche's usual days are one click away.
  await page.getByRole("button", { name: returnVisits.settings.useSuggested }).click();
  await expect(page.getByLabel(returnVisits.settings.daysAfter)).not.toHaveValue("42");
});

test("staff have the waitlist tab, not the return-visit messages", async ({ browser, request, owner }) => {
  const email = uniqueEmail();
  await inviteStaff(request, owner.token, owner.businessId, email);
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 }, reducedMotion: "reduce" });
  await signInContext(context, await signInByEmail(request, email));
  const page = await context.newPage();

  await page.goto(`/b/${owner.businessId}/bookings/waitlist`);
  await expect(page.getByRole("heading", { level: 2, name: pages.bookingsWaitlist })).toBeVisible();
  await expect(page.getByText(waitlist.empty.active)).toBeVisible();
  await expect(page.getByText(waitlist.settings.ownersOnly)).toBeVisible();
  await expect(page.getByRole("link", { name: pages.bookingsReturnVisits })).toHaveCount(0);

  await page.goto(`/b/${owner.businessId}/bookings/return-visits`);
  await expect(page.getByRole("heading", { level: 1, name: en.navigation.ownerOnlyTitle })).toBeVisible();
  await context.close();
});
