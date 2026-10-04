/**
 * The platform admin reads the growth metrics (Metrics): the funnel, the
 * setup tunnel, MRR movements, margin, cohorts, sources and Web Vitals of
 * the demo data, filtered through the address. Owners get "Page not
 * found"; on a phone the page fits and passes the accessibility audit.
 */

import AxeBuilder from "@axe-core/playwright";
import type { APIRequestContext } from "@playwright/test";

import { signInAsPlatformAdmin } from "./support/admin";
import { METRICS_ADMIN_EMAIL, WEB_URL } from "./support/env";
import { expect, signInContext, test } from "./support/fixtures";
import { en } from "./support/messages";
import { waitForNetworkQuiet } from "./support/network";

const texts = en.adminMetrics;

let adminToken: Promise<string> | null = null;

/** One sign-in per test worker: the API sends an address a code at most every 30 seconds. */
function signInAsAdmin(request: APIRequestContext): Promise<string> {
  adminToken ??= signInAsPlatformAdmin(request, METRICS_ADMIN_EMAIL);
  return adminToken;
}

test("the platform admin reads the growth metrics and filters them through the address", async ({ browser, request }) => {
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 }, reducedMotion: "reduce" });
  await signInContext(context, await signInAsAdmin(request));
  const page = await context.newPage();

  await page.goto("/admin");
  const navigation = page.getByRole("navigation", { name: en.nav.mainNavigation });
  await navigation.getByRole("link", { name: texts.nav }).click();
  await expect(page).toHaveURL(/\/admin\/metrics$/);
  await expect(page.getByRole("heading", { level: 1, name: texts.title })).toBeVisible();
  await expect(navigation.getByRole("link", { name: texts.nav })).toHaveAttribute("aria-current", "page");

  const funnel = page.getByRole("region", { name: texts.funnel.title });
  for (const step of Object.values(texts.funnel.steps)) {
    await expect(funnel.getByText(step, { exact: true })).toBeVisible();
  }
  const tunnel = page.getByRole("region", { name: texts.tunnel.title });
  await expect(tunnel.getByRole("rowheader", { name: texts.tunnel.steps.hours })).toBeVisible();
  const mrr = page.getByRole("region", { name: texts.mrr.title });
  await expect(mrr.getByRole("rowheader", { name: texts.mrr.start })).toBeVisible();
  await expect(mrr.getByRole("rowheader", { name: texts.mrr.kinds.churn })).toBeVisible();
  await expect(mrr.getByRole("rowheader", { name: texts.mrr.end })).toBeVisible();
  await expect(page.getByRole("region", { name: texts.margin.title })).toBeVisible();
  // The demo owner signed up today: its month is the newest cohort.
  const cohorts = page.getByRole("region", { name: texts.cohorts.title });
  await expect(cohorts.getByRole("columnheader", { name: texts.cohorts.month })).toBeVisible();
  await expect(page.getByRole("region", { name: texts.sources.title })).toBeVisible();
  await expect(page.getByRole("region", { name: texts.vitals.title })).toBeVisible();

  const filters = page.getByRole("search", { name: texts.filters.label });
  await filters.getByLabel(texts.filters.period).selectOption("last30");
  await expect(page).toHaveURL(/\/admin\/metrics\?from=\d{4}-\d{2}-\d{2}&to=\d{4}-\d{2}-\d{2}$/);
  await filters.getByLabel(texts.filters.period).selectOption("custom");
  await expect(filters.getByLabel(texts.filters.from)).toBeVisible();
  await filters.getByRole("button", { name: texts.filters.clear }).click();
  await expect(page).toHaveURL(/\/admin\/metrics$/);

  // The address alone opens the same filtered view.
  await page.goto("/admin/metrics?country=GE");
  await expect(page.getByRole("search", { name: texts.filters.label }).getByLabel(texts.filters.country)).toHaveValue("GE");
  await expect(page.getByRole("region", { name: texts.funnel.title })).toBeVisible();
  await context.close();
});

test("the Metrics page is not there for owners", async ({ page, owner, consoleErrors }) => {
  expect(owner.businessId).toBeTruthy();
  consoleErrors.allow(/status of 404 \(Not Found\) \(http:\/\/localhost:\d+\/admin\/metrics\)/);
  const response = await page.goto("/admin/metrics");

  expect(response?.status()).toBe(404);
  await expect(page.getByText(en.errors.notFoundTitle)).toBeVisible();
});

test.describe("on a phone", () => {
  test.use({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });

  for (const theme of ["dark", "light"] as const) {
    test(`the Metrics page fits and passes the audit in the ${theme} theme`, async ({ page, request }) => {
      await signInContext(page.context(), await signInAsAdmin(request));
      await page.context().addCookies([{ name: "aw_theme", value: theme, url: WEB_URL }]);

      await page.goto("/admin/metrics");
      await expect(page.getByRole("region", { name: texts.funnel.title })).toBeVisible();
      await waitForNetworkQuiet(page);
      expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
      const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
      const serious = results.violations.filter((violation) => violation.impact === "serious" || violation.impact === "critical");
      expect(serious.map((violation) => violation.id)).toEqual([]);
    });
  }
});
