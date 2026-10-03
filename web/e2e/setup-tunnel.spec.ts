/**
 * "Create an AI assistant": the full-screen tunnel from a new account to a
 * live assistant. Eight screens, one question each (the business, where it
 * is, what it offers, its hours, who helps, where customers write, a test
 * conversation, the launch), saved as the owner goes, so a reload or a
 * later visit continues where they left off; then the finale with the
 * assistant's link and QR code, and the cabinet.
 *
 * The suite's API has no language model: the rehearsal model
 * (LLM_PROVIDER=scripted) answers the test chat, and the launch's progress
 * is played by the test (playLaunch in support/tunnel.ts) so the screens
 * stay quick to walk; apply-changes.spec.ts runs real checks.
 */

import type { Page } from "@playwright/test";

import { expect, test } from "./support/fixtures";
import { en } from "./support/messages";
import {
  answerBusiness,
  answerChannels,
  answerHours,
  answerOffer,
  answerPeople,
  answerPlace,
  answerTry,
  expectNoSidewaysScroll,
  expectStep,
  launch,
  playLaunch,
} from "./support/tunnel";

async function walkToLaunch(page: Page, email: string, onEachStep: () => Promise<void> = async () => {}): Promise<string> {
  await page.goto("/businesses");
  // An account without businesses starts in the tunnel.
  await expect(page).toHaveURL(/\/create$/);
  await onEachStep();
  await answerBusiness(page, "Salon Aurora");
  await onEachStep();
  const businessId = await answerPlace(page);
  await onEachStep();
  await answerOffer(page);
  await onEachStep();
  await answerHours(page);
  await onEachStep();
  await answerPeople(page, email);
  await onEachStep();
  await answerChannels(page);
  await onEachStep();
  await answerTry(page);
  await onEachStep();
  return businessId;
}

async function expectFinale(page: Page, businessId: string): Promise<void> {
  await expect(page.getByText("Salon Aurora").first()).toBeVisible();
  // The business's own chat page, its link to copy and its QR code.
  await expect(page.getByText(/\/c\/salon-aurora/)).toBeVisible();
  await expect(page.getByRole("img", { name: /salon-aurora/ })).toBeVisible();
  await page.getByRole("button", { name: en.tunnelLaunch.finale.open }).click();
  await expect(page).toHaveURL(new RegExp(`/b/${businessId}/overview$`));
}

test("a new owner goes from sign-in to a live assistant", async ({ page, account }) => {
  test.setTimeout(240_000);
  await playLaunch(page);
  const businessId = await walkToLaunch(page, account.email);
  await launch(page);
  await expectFinale(page, businessId);
  // The cabinet opens with its sections, and the business is on the list.
  const navigation = page.getByRole("navigation", { name: en.nav.mainNavigation });
  await expect(navigation.getByRole("link", { name: en.navigation.sections.assistant, exact: true })).toBeVisible();
  await page.goto("/businesses");
  await expect(page.getByRole("heading", { name: "Salon Aurora" })).toBeVisible();
});

test("a reload keeps the screen and a later visit continues where the owner left off", async ({ page, account }) => {
  test.setTimeout(180_000);
  expect(account.token).toBeTruthy();
  await page.goto("/create");
  await answerBusiness(page, "Salon Aurora");
  // The first two answers live in this browser until the business exists.
  await page.reload();
  await expectStep(page, en.tunnelBusiness.place.title);
  await page.getByRole("button", { name: en.tunnel.back }).click();
  await expect(page.getByLabel(en.tunnelBusiness.business.name)).toHaveValue("Salon Aurora");
  await page.getByRole("button", { name: en.tunnel.continue, exact: true }).click();
  const businessId = await answerPlace(page);

  // "Skip for now" is remembered: the offer can wait.
  await page.getByRole("button", { name: en.tunnel.skip }).click();
  await expectStep(page, en.tunnelOffer.hours.title);
  await page.reload();
  await expectStep(page, en.tunnelOffer.hours.title);
  await answerHours(page);

  // Leaving and coming back without a step opens the first one not done yet.
  await page.getByRole("link", { name: en.tunnel.exit }).click();
  await expect(page).toHaveURL(new RegExp(`/b/${businessId}/overview$`));
  await page.getByRole("link", { name: new RegExp(`${en.setup.start}|${en.setup.continue}`) }).first().click();
  await expect(page).toHaveURL(new RegExp(`/b/${businessId}/setup$`));
  await expectStep(page, en.tunnelTeam.people.title);
  // The rail shows the skipped step, and opens any step.
  const rail = page.getByRole("navigation", { name: en.tunnel.railLabel });
  await rail.getByRole("button", { name: `${en.tunnel.steps.offer} (${en.tunnel.stepState.skipped})` }).click();
  await expectStep(page, en.tunnelOffer.offer.title);
});

test.describe("on a phone", () => {
  test.use({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });

  test("the whole tunnel fits the screen, from sign-in to the cabinet", async ({ page, account }) => {
    test.setTimeout(240_000);
    await playLaunch(page);
    const businessId = await walkToLaunch(page, account.email, () => expectNoSidewaysScroll(page));
    await launch(page);
    await expectNoSidewaysScroll(page);
    await expectFinale(page, businessId);
  });
});
