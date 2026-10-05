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

import { WEB_URL } from "./support/env";
import { expect, test } from "./support/fixtures";
import { en, ru } from "./support/messages";
import {
  answerBusiness,
  expectBackdropBehind,
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
  await expectBackdropBehind(page, page.getByRole("heading", { level: 1, name: en.tunnelLaunch.finale.title }));
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

test.describe("the rail and the offer step", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test("the step's name sits under its own dot, and 'Saved' does not move the rail", async ({ page, newOwner }) => {
    await page.goto(`/b/${newOwner.businessId}/setup?step=offer`);
    await expectStep(page, en.tunnelOffer.offer.title);
    const rail = page.getByRole("navigation", { name: en.tunnel.railLabel });
    const dot = (await rail.locator('[aria-current="step"]').boundingBox())!;
    const label = (await rail.locator("[data-rail-label]").boundingBox())!;
    expect(label.x).toBeLessThanOrEqual(dot.x + dot.width / 2);
    expect(label.x + label.width).toBeGreaterThanOrEqual(dot.x + dot.width / 2);
    expect(label.y).toBeGreaterThanOrEqual(dot.y + dot.height - 1);

    const before = (await rail.boundingBox())!;
    await priceOf(page, 1).fill("35");
    // Leaving the line saves it.
    await page.getByRole("heading", { level: 1, name: en.tunnelOffer.offer.title }).click();
    await expect(page.locator("[data-save-slot]").getByText(en.tunnel.saved, { exact: true })).toBeVisible();
    const after = (await rail.boundingBox())!;
    expect([after.x, after.width]).toEqual([before.x, before.width]);
  });

  test("a revisit keeps the saved order and does not bring back replaced or removed examples", async ({ page, newOwner }) => {
    await page.goto(`/b/${newOwner.businessId}/setup?step=offer`);
    await expectStep(page, en.tunnelOffer.offer.title);
    const names = page.getByRole("textbox", { name: new RegExp(`^${en.tunnelOffer.offer.name} \\d+$`) });
    await expect(names.nth(2)).toBeVisible();
    const [first, replaced, removed] = [await names.nth(0).inputValue(), await names.nth(1).inputValue(), await names.nth(2).inputValue()];

    await priceOf(page, 1).fill("35");
    await names.nth(1).fill("Balayage");
    await priceOf(page, 2).fill("90");
    await page.getByRole("button", { name: en.tunnelOffer.offer.removeRow.replace("{name}", removed) }).click();
    await page.getByRole("button", { name: en.tunnelOffer.offer.addRow }).click();
    const last = await names.count();
    await names.nth(last - 1).fill("Beard trim");
    await priceOf(page, last).fill("15");
    await page.getByRole("button", { name: en.tunnel.continue, exact: true }).click();
    await expectStep(page, en.tunnelOffer.hours.title);

    await page.goto(`/b/${newOwner.businessId}/setup?step=offer`);
    await expectStep(page, en.tunnelOffer.offer.title);
    await expect(names.nth(2)).toHaveValue("Beard trim");
    const shown = await names.evaluateAll((inputs) => inputs.map((input) => (input as HTMLInputElement).value));
    // Exactly what the business sells: no untouched example comes back once lines are saved.
    expect(shown).toEqual([first, "Balayage", "Beard trim"]);
    expect(shown).not.toContain(replaced);
    expect(shown).not.toContain(removed);
    await expect(page.getByText(en.tunnelOffer.offer.suggestion, { exact: true })).toHaveCount(0);

    // In another interface language the saved lines are not doubled by the examples' own titles.
    await page.context().addCookies([{ name: "aw_locale", value: "ru", url: WEB_URL }]);
    await page.reload();
    await expectStep(page, ru.tunnelOffer.offer.title);
    const ruNames = page.getByRole("textbox", { name: new RegExp(`^${ru.tunnelOffer.offer.name} \\d+$`) });
    await expect(ruNames).toHaveCount(3);
    await expect(page.getByText(ru.tunnelOffer.offer.suggestion, { exact: true })).toHaveCount(0);
  });
});

function priceOf(page: Page, row: number) {
  return page.getByRole("textbox", { name: `${en.tunnelOffer.offer.price.replace("{currency}", "EUR")} ${row}` });
}
