/**
 * Device sessions, the admin team and support access in the cabinet: the
 * owner sees where they are signed in; a platform admin opens the owner's
 * cabinet only with a reason, read only, under a banner; the owner sees
 * who looks and why, and ends it; the admin team lists its SUPER admin.
 */

import type { APIRequestContext } from "@playwright/test";

import { signInAsPlatformAdmin } from "./support/admin";
import { PLATFORM_ADMIN_EMAIL } from "./support/env";
import { expect, signInContext, test } from "./support/fixtures";
import { en } from "./support/messages";

const REASON = "The owner asked why bookings stopped";

let adminToken: Promise<string> | null = null;

/** One sign-in per worker: the API sends an address a code at most every 30 seconds. */
function signInAsAdmin(request: APIRequestContext): Promise<string> {
  adminToken ??= signInAsPlatformAdmin(request, PLATFORM_ADMIN_EMAIL);
  return adminToken;
}

test("the owner sees where they are signed in", async ({ page, owner }) => {
  expect(owner.businessId).toBeTruthy();
  await page.goto("/account/security");

  const devices = page.getByRole("region", { name: en.devices.title });
  await expect(devices).toBeVisible();
  await expect(devices.getByText(en.devices.thisDevice)).toBeVisible();
  await expect(devices.getByText(en.devices.onlyThis)).toBeVisible();
});

test("support opens a cabinet with a reason, read only, and the owner ends it", async ({ browser, page, owner, request }) => {
  const admin = await browser.newContext({ viewport: { width: 1280, height: 900 }, reducedMotion: "reduce" });
  await signInContext(admin, await signInAsAdmin(request));
  const adminPage = await admin.newPage();

  await adminPage.goto(`/admin/clients/${owner.businessId}`);
  await adminPage.getByRole("button", { name: en.admin.detail.openCabinet }).click();
  const dialog = adminPage.getByRole("dialog");
  const confirm = dialog.getByRole("button", { name: en.admin.detail.openCabinet });
  await expect(confirm).toBeDisabled();
  await dialog.getByLabel(en.admin.detail.reasonLabel).fill(REASON);
  await confirm.click();

  const supportBanner = adminPage.getByRole("region", { name: en.supportAccess.label });
  await expect(supportBanner.getByText(en.supportAccess.support.readOnly, { exact: false })).toBeVisible();

  await page.goto(`/b/${owner.businessId}/overview`);
  const banner = page.getByRole("region", { name: en.supportAccess.label });
  await expect(banner.getByText(en.supportAccess.owner.title)).toBeVisible();
  await expect(banner.getByText(REASON, { exact: false })).toBeVisible();
  await banner.getByRole("button", { name: en.supportAccess.owner.end }).click();
  await page.getByRole("dialog").getByRole("button", { name: en.supportAccess.owner.end }).click();
  await expect(banner).toBeHidden();

  // Support's next page is the client's admin page again.
  await adminPage.goto(`/b/${owner.businessId}/overview`);
  await expect(adminPage).toHaveURL(new RegExp(`/admin/clients/${owner.businessId}$`));
  await admin.close();
});

test("the admin team lists its SUPER admin", async ({ browser, request }) => {
  const context = await browser.newContext({ viewport: { width: 390, height: 844 }, reducedMotion: "reduce" });
  await signInContext(context, await signInAsAdmin(request));
  const page = await context.newPage();

  await page.goto("/admin/team");
  await expect(page.getByRole("heading", { level: 1, name: en.adminTeam.title })).toBeVisible();
  const me = page.getByRole("listitem").filter({ hasText: en.adminTeam.you });
  await expect(me.getByRole("combobox")).toHaveValue("super");
  await context.close();
});
