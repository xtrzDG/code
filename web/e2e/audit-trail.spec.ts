/**
 * The audit trail in the cabinet: an owner sees the tamper check of the
 * business's log on Settings → Audit; a platform admin sees every log's
 * check and the platform's own log (a wrong sign-in code lands there with
 * the address as a digest) on Audit. Owners do not get the admin page.
 */

import AxeBuilder from "@axe-core/playwright";
import type { APIRequestContext } from "@playwright/test";

import { signInAsPlatformAdmin } from "./support/admin";
import { uniqueEmail } from "./support/api";
import { API_URL, PLATFORM_ADMIN_EMAIL, WEB_URL } from "./support/env";
import { expect, signInContext, test } from "./support/fixtures";
import { en, ru } from "./support/messages";
import { waitForNetworkQuiet } from "./support/network";

const texts = en.adminAudit;
const chain = en.auditChain;

let adminToken: Promise<string> | null = null;

/** One sign-in per test worker: the API sends an address a code at most every 30 seconds. */
function signInAsAdmin(request: APIRequestContext): Promise<string> {
  adminToken ??= signInAsPlatformAdmin(request, PLATFORM_ADMIN_EMAIL);
  return adminToken;
}

/** A sign-in code to a new address, answered with a wrong code: a failed check in the platform's log. */
async function failOneSignIn(request: APIRequestContext): Promise<void> {
  const start = await request.post(`${API_URL}/v1/auth/otp/start`, { data: { email: uniqueEmail(), locale: "en" } });
  expect(start.status(), await start.text()).toBe(200);
  const { challenge_id: challengeId } = (await start.json()) as { challenge_id: string };
  const verify = await request.post(`${API_URL}/v1/auth/otp/verify`, { data: { challenge_id: challengeId, code: "000000" } });
  expect(verify.status()).toBe(401);
}

test("the owner sees the tamper check above the audit log", async ({ page, owner }) => {
  await page.goto(`/b/${owner.businessId}/settings/audit`);

  const log = page.getByRole("region", { name: en.settings.audit.title });
  await expect(log.getByText(chain.title, { exact: true })).toBeVisible();
  // A new business's log waits for the next daily check.
  await expect(log.getByText(new RegExp(`^(${chain.status.unchecked}|${chain.status.intact})$`))).toBeVisible();
  await expect(log.getByRole("alert")).toHaveCount(0);
});

test("the owner reads the tamper check in Russian", async ({ page, owner }) => {
  await page.context().addCookies([{ name: "aw_locale", value: "ru", url: WEB_URL }]);
  await page.goto(`/b/${owner.businessId}/settings/audit`);

  await expect(page.getByText(ru.auditChain.title, { exact: true })).toBeVisible();
});

test("the platform admin finds a failed sign-in in the platform's log", async ({ browser, request }) => {
  await failOneSignIn(request);
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 }, reducedMotion: "reduce" });
  await signInContext(context, await signInAsAdmin(request));
  const page = await context.newPage();

  await page.goto("/admin");
  const navigation = page.getByRole("navigation", { name: en.nav.mainNavigation });
  await navigation.getByRole("link", { name: texts.nav }).click();
  await expect(page).toHaveURL(/\/admin\/audit$/);
  await expect(page.getByRole("heading", { level: 1, name: texts.title })).toBeVisible();
  await expect(navigation.getByRole("link", { name: texts.nav })).toHaveAttribute("aria-current", "page");
  await expect(page.getByRole("region", { name: texts.chains.title }).getByText(texts.chains.platform)).toBeVisible();

  await page.getByLabel(texts.log.event).selectOption("login_failed");
  const table = page.getByRole("table", { name: texts.log.title });
  await expect(table.getByText(texts.events.login_failed).first()).toBeVisible();
  await expect(table.getByText(texts.entities.login_destination).first()).toBeVisible();
  await expect(table.getByText(/^dest_[0-9a-f]{8}$/).first()).toBeVisible();
  await expect(table.getByText(/@/)).toHaveCount(0);
  await context.close();
});

test("the Audit page is not there for owners", async ({ page, owner, consoleErrors }) => {
  expect(owner.businessId).toBeTruthy();
  consoleErrors.allow(/status of 404 \(Not Found\) \(http:\/\/localhost:\d+\/(admin\/audit|favicon\.ico)\)/);
  const response = await page.goto("/admin/audit");

  expect(response?.status()).toBe(404);
  await expect(page.getByText(en.errors.notFoundTitle)).toBeVisible();
});

test.describe("on a phone", () => {
  test.use({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });

  for (const theme of ["dark", "light"] as const) {
    test(`the Audit page fits and passes the audit in the ${theme} theme`, async ({ page, request }) => {
      await signInContext(page.context(), await signInAsAdmin(request));
      await page.context().addCookies([{ name: "aw_theme", value: theme, url: WEB_URL }]);

      await page.goto("/admin/audit");
      await expect(page.getByRole("heading", { level: 1, name: texts.title })).toBeVisible();
      await expect(page.getByRole("region", { name: texts.chains.title }).getByText(texts.chains.platform)).toBeVisible();
      await waitForNetworkQuiet(page);
      expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
      const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
      const serious = results.violations.filter((violation) => violation.impact === "serious" || violation.impact === "critical");
      expect(serious.map((violation) => violation.id)).toEqual([]);
    });
  }
});
