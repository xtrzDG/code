/**
 * Closing a business and deleting an account: the owner closes the
 * business in Settings → Business (its name typed to confirm), every page
 * then counts down to the deletion, and keeping it within the 30 days
 * brings it back. An account whose owner still runs an open business is
 * not deleted (the card names the business); once the business is
 * closing, the account goes and the sign-in page opens. On a phone the
 * danger zone and the banner fit the screen.
 */

import type { Page } from "@playwright/test";

import { expect, test } from "./support/fixtures";
import { en } from "./support/messages";
import { findOverflow } from "./support/overflow";

const texts = en.closure;

async function closeBusiness(page: Page, businessId: string, name: string): Promise<void> {
  await page.goto(`/b/${businessId}/settings`);
  const zone = page.getByTestId("close-business");
  await expect(zone.getByRole("heading", { name: texts.zone.title })).toBeVisible();
  await zone.getByRole("button", { name: texts.zone.action }).click();
  const dialog = page.getByRole("dialog", { name: texts.zone.dialogTitle });
  const confirm = dialog.getByRole("button", { name: texts.zone.confirm });
  await expect(confirm).toBeDisabled();
  await dialog.getByRole("textbox").fill(name);
  await confirm.click();
  await expect(zone.getByRole("heading", { name: texts.zone.pendingTitle })).toBeVisible();
}

test("the owner closes the business, every page counts down, and keeping it brings it back", async ({ page, owner }) => {
  await closeBusiness(page, owner.businessId, owner.businessName);
  await expect(page.getByTestId("close-business")).toContainText("30 days");

  await page.goto(`/b/${owner.businessId}/bookings`);
  const banner = page.getByRole("region", { name: texts.banner.title });
  await expect(banner).toBeVisible();
  await expect(banner).toContainText(/in 30 days, on /);
  await banner.getByRole("button", { name: texts.banner.keep }).click();
  await expect(page.getByText(texts.banner.kept)).toBeVisible();
  await expect(banner).toBeHidden();

  await page.goto(`/b/${owner.businessId}/settings`);
  await expect(page.getByTestId("close-business").getByRole("button", { name: texts.zone.action })).toBeVisible();
});

test("the last owner of an open business keeps the account until the business closes", async ({ page, owner, consoleErrors }) => {
  // The first deletion is refused on purpose.
  consoleErrors.allow(/status of 409 \(Conflict\) \(http:\/\/localhost:\d+\/api\/backend\/v1\/me\)/);
  await page.goto("/account/security");
  const card = page.getByTestId("delete-account");
  const deleteAccount = async () => {
    await card.getByRole("button", { name: texts.account.action }).click();
    const dialog = page.getByRole("dialog", { name: texts.account.dialogTitle });
    await dialog.getByRole("textbox").fill(owner.email);
    await dialog.getByRole("button", { name: texts.account.confirm }).click();
  };

  await deleteAccount();
  await expect(card.getByRole("status")).toHaveText(texts.account.lastOwner.replace("{names}", owner.businessName));

  await closeBusiness(page, owner.businessId, owner.businessName);
  await page.goto("/account/security");
  await deleteAccount();
  await expect(page).toHaveURL(/\/login/);
});

test("on a phone the danger zone and the banner fit the screen", async ({ page, owner }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await closeBusiness(page, owner.businessId, owner.businessName);
  expect(await findOverflow(page)).toEqual([]);

  await page.goto(`/b/${owner.businessId}/overview`);
  await expect(page.getByRole("region", { name: texts.banner.title })).toBeVisible();
  expect(await findOverflow(page)).toEqual([]);
});
