/**
 * The platform admin re-encrypts the stored tokens from the cabinet
 * (Encryption keys): a confirmation, the run queued for the API's embedded
 * worker, and the page following it until it is done. Everyone else gets
 * "Page not found".
 */

import AxeBuilder from "@axe-core/playwright";
import type { APIRequestContext } from "@playwright/test";

import { signInAsPlatformAdmin } from "./support/admin";
import { PLATFORM_ADMIN_EMAIL, WEB_URL } from "./support/env";
import { expect, signInContext, test } from "./support/fixtures";
import { en } from "./support/messages";
import { waitForNetworkQuiet } from "./support/network";

const texts = en.adminSecurity;

let adminToken: Promise<string> | null = null;

/** One sign-in per test worker: the API sends an address a code at most every 30 seconds. */
function signInAsAdmin(request: APIRequestContext): Promise<string> {
  adminToken ??= signInAsPlatformAdmin(request, PLATFORM_ADMIN_EMAIL);
  return adminToken;
}

test("the platform admin re-encrypts every stored token and sees the run finish", async ({ browser, request }) => {
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 }, reducedMotion: "reduce" });
  await signInContext(context, await signInAsAdmin(request));
  const page = await context.newPage();

  await page.goto("/admin");
  const navigation = page.getByRole("navigation", { name: en.nav.mainNavigation });
  await navigation.getByRole("link", { name: texts.nav }).click();
  await expect(page).toHaveURL(/\/admin\/security$/);
  await expect(page.getByRole("heading", { level: 1, name: texts.title })).toBeVisible();
  await expect(navigation.getByRole("link", { name: texts.nav })).toHaveAttribute("aria-current", "page");

  // The e2e API runs with its development key alone.
  const ring = page.getByRole("region", { name: texts.ring.title });
  await expect(ring.getByText(texts.ring.single)).toBeVisible();

  const run = page.getByRole("region", { name: texts.run.title });
  await run.getByRole("button", { name: texts.run.start }).click();
  const dialog = page.getByRole("dialog", { name: texts.run.confirmTitle });
  await expect(dialog.getByText(texts.run.confirmBody)).toBeVisible();
  await dialog.getByRole("button", { name: texts.run.confirm }).click();
  await expect(dialog).toBeHidden();
  await expect(page.getByText(texts.run.started)).toBeVisible();

  // The embedded worker takes the job; the page polls until it is done.
  await expect(run.getByText(texts.run.status.done, { exact: true })).toBeVisible({ timeout: 30_000 });
  await expect(run.getByText(texts.run.verdict.cleanSingle)).toBeVisible();
  await expect(run.getByRole("button", { name: texts.run.start })).toBeEnabled();
  await context.close();
});

test("the Encryption keys page is not there for owners", async ({ page, owner, consoleErrors }) => {
  expect(owner.businessId).toBeTruthy();
  // The 404 page itself, and the browser's own /favicon.ico request that a 404
  // page sometimes draws in a full run.
  consoleErrors.allow(/status of 404 \(Not Found\) \(http:\/\/localhost:\d+\/(admin\/security|favicon\.ico)\)/);
  const response = await page.goto("/admin/security");

  expect(response?.status()).toBe(404);
  await expect(page.getByText(en.errors.notFoundTitle)).toBeVisible();
  await expect(page.getByRole("link", { name: texts.nav })).toHaveCount(0);
});

test.describe("on a phone", () => {
  test.use({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });

  for (const theme of ["dark", "light"] as const) {
    test(`the Encryption keys page fits and passes the audit in the ${theme} theme`, async ({ page, request }) => {
      await signInContext(page.context(), await signInAsAdmin(request));
      await page.context().addCookies([{ name: "aw_theme", value: theme, url: WEB_URL }]);

      await page.goto("/admin/security");
      await expect(page.getByRole("heading", { level: 1, name: texts.title })).toBeVisible();
      await waitForNetworkQuiet(page);
      expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
      const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
      const serious = results.violations.filter((violation) => violation.impact === "serious" || violation.impact === "critical");
      expect(serious.map((violation) => violation.id)).toEqual([]);
    });
  }
});
