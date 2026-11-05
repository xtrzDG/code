/**
 * Before the assistant exists the cabinet has one thing to do: "Create an
 * AI assistant". Every section shows the invitation, the sidebar holds only
 * the entry into the setup tunnel (/b/{id}/setup, full screen), and once the
 * assistant is created the five sections open.
 */

import { createAssistant } from "./support/api";
import { expect, test } from "./support/fixtures";
import { en } from "./support/messages";

test("a new business shows only Create an AI assistant until the assistant exists", async ({ page, newOwner, request }) => {
  await page.goto(`/b/${newOwner.businessId}`);
  await expect(page).toHaveURL(new RegExp(`/b/${newOwner.businessId}/overview$`));
  await expect(page.getByRole("heading", { level: 1, name: en.setup.title })).toBeVisible();
  // The sections are not there yet; any old link shows the same invitation.
  const navigation = page.getByRole("navigation", { name: en.nav.mainNavigation });
  await expect(navigation.getByRole("link")).toHaveCount(1);
  await page.goto(`/b/${newOwner.businessId}/settings/team`);
  await expect(page.getByRole("heading", { level: 1, name: en.setup.title })).toBeVisible();

  // One button leads into the full-screen tunnel, where the owner left off
  // (the salon's services are not chosen yet, so its first screen).
  await page.getByRole("link", { name: new RegExp(`${en.setup.start}|${en.setup.continue}`) }).first().click();
  await expect(page).toHaveURL(new RegExp(`/b/${newOwner.businessId}/setup$`));
  await expect(page.getByRole("heading", { level: 1, name: en.tunnelBusiness.business.title })).toBeVisible();
  await expect(page.getByRole("navigation", { name: en.tunnel.railLabel })).toBeVisible();
  // The old address of the setup flow leads into the tunnel too.
  await page.goto(`/b/${newOwner.businessId}/onboarding`);
  await expect(page).toHaveURL(new RegExp(`/b/${newOwner.businessId}/setup$`));

  // The assistant is created: the sections open and the setup flow's old step opens its section of the business profile.
  await createAssistant(request, newOwner.token, newOwner.businessId);
  await page.goto(`/b/${newOwner.businessId}/onboarding?step=offer`);
  await expect(page).toHaveURL(new RegExp(`/b/${newOwner.businessId}/assistant/profile/offer$`));
  await expect(page.getByRole("heading", { level: 1, name: en.navigation.sections.assistant })).toBeVisible();
  for (const section of Object.values(en.navigation.sections)) {
    await expect(navigation.getByRole("link", { name: section, exact: true })).toBeVisible();
  }
});

test.describe("on a phone", () => {
  test.use({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });

  test("the invitation fits the screen and the account stays at hand", async ({ page, newOwner }) => {
    await page.goto(`/b/${newOwner.businessId}/overview`);
    await expect(page.getByRole("heading", { level: 1, name: en.setup.title })).toBeVisible();
    await expect(page.getByRole("navigation", { name: en.navigation.tabBar })).toHaveCount(0);
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(overflow).toBeLessThanOrEqual(0);

    await page.getByRole("button", { name: en.account.menu }).click();
    const sheet = page.getByRole("dialog", { name: en.navigation.more });
    await expect(sheet.getByRole("combobox", { name: en.language.label })).toBeVisible();
  });
});
