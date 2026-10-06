/**
 * The platform admin's System page: the alerts, workers, queues, dead
 * letters, channels, backups and database of the e2e API, and recording a
 * personal data breach for one business, which notifies its owner and
 * writes an entry in that business's audit log. Owners get "Page not
 * found"; on a phone the page fits and passes the accessibility audit.
 */

import AxeBuilder from "@axe-core/playwright";
import type { APIRequestContext } from "@playwright/test";

import { signInAsPlatformAdmin } from "./support/admin";
import { SYSTEM_ADMIN_EMAIL, WEB_URL } from "./support/env";
import { expect, signInContext, test } from "./support/fixtures";
import { en } from "./support/messages";
import { waitForNetworkQuiet } from "./support/network";

const texts = en.adminSystem;
const form = en.adminIncident;

let adminToken: Promise<string> | null = null;

/** One sign-in per test worker: the API sends an address a code at most every 30 seconds. */
function signInAsAdmin(request: APIRequestContext): Promise<string> {
  adminToken ??= signInAsPlatformAdmin(request, SYSTEM_ADMIN_EMAIL);
  return adminToken;
}

test("the platform admin reads the system page and records a data breach that notifies the owner", async ({
  browser,
  request,
  page,
  owner,
}) => {
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 }, reducedMotion: "reduce" });
  await signInContext(context, await signInAsAdmin(request));
  const admin = await context.newPage();

  await admin.goto("/admin");
  const navigation = admin.getByRole("navigation", { name: en.nav.mainNavigation });
  await navigation.getByRole("link", { name: texts.nav }).click();
  await expect(admin).toHaveURL(/\/admin\/system$/);
  await expect(admin.getByRole("heading", { level: 1, name: texts.title })).toBeVisible();
  await expect(navigation.getByRole("link", { name: texts.nav })).toHaveAttribute("aria-current", "page");

  await expect(admin.getByRole("region", { name: texts.alerts.title })).toBeVisible();
  await expect(admin.getByRole("region", { name: texts.workers.title })).toBeVisible();
  const lanes = admin.getByRole("region", { name: texts.lanes.title });
  for (const lane of Object.values(texts.lanes.names)) {
    await expect(lanes.getByRole("rowheader", { name: lane })).toBeVisible();
  }
  await expect(admin.getByRole("region", { name: texts.deadLetters.title })).toBeVisible();
  await expect(admin.getByRole("region", { name: texts.channels.title })).toBeVisible();
  // The e2e API keeps its data in memory: no database to measure, no backups recorded.
  await expect(admin.getByRole("region", { name: texts.database.title }).getByText(texts.database.unmeasured)).toBeVisible();
  const backups = admin.getByRole("region", { name: texts.backups.title });
  await expect(backups.getByText(texts.backups.none)).toHaveCount(2);
  // In memory there is no old row to rewrite or column to fill: the embedded
  // worker's first tick finishes every post-deploy data task, which fold away.
  const dataTasks = admin.getByRole("region", { name: en.dataTasks.title });
  await expect(dataTasks.getByText(en.dataTasks.allDone)).toBeVisible();
  await expect(dataTasks.getByText(en.dataTasks.settled)).toBeVisible();
  const showDone = dataTasks.getByRole("button", { name: /^Show \d+ done tasks$/ });
  await showDone.click();
  await expect(dataTasks.getByRole("table", { name: en.dataTasks.doneCaption }).getByText("contacts.last_seen_at")).toBeVisible();
  await dataTasks.getByRole("button", { name: en.dataTasks.hideDone }).click();
  await expect(dataTasks.getByRole("table")).toHaveCount(0);

  const incidents = admin.getByRole("region", { name: texts.incidents.title });
  await incidents.getByRole("button", { name: texts.incidents.record }).click();
  const dialog = admin.getByRole("dialog", { name: form.title });
  await dialog.getByLabel(form.kind).selectOption("data_breach");
  await expect(dialog.getByLabel(form.severity)).toBeDisabled();
  await dialog.getByRole("button", { name: form.submitBreach }).click();
  await expect(dialog.getByText(form.errors.required).first()).toBeVisible();
  await expect(dialog.getByText(form.errors.noticeRequired)).toBeVisible();

  await dialog.getByLabel(form.name).fill("Support export sent to a wrong address");
  await dialog.getByLabel(form.businesses).fill(owner.businessId);
  await dialog.getByLabel(form.breach.subjects).fill("12");
  await dialog.getByLabel(form.breach.records).fill("24");
  await dialog.getByLabel(form.breach.fields.nature).fill("A support export was e-mailed to a wrong address.");
  await dialog.getByLabel(form.breach.fields.subject_categories).fill("Customers who wrote in September");
  await dialog.getByLabel(form.breach.fields.record_categories).fill("Names and phone numbers");
  await dialog.getByLabel(form.breach.fields.likely_consequences).fill("Unwanted calls are possible.");
  await dialog.getByLabel(form.breach.fields.measures).fill("The recipient confirmed deletion.");
  await dialog.getByRole("button", { name: form.submitBreach }).click();
  await expect(dialog).toBeHidden();
  await expect(admin.getByText("Incident recorded; 1 owner notified")).toBeVisible();

  await expect(incidents.getByRole("heading", { name: "Support export sent to a wrong address" })).toBeVisible();
  await expect(incidents.getByText(texts.incidents.kinds.data_breach, { exact: true })).toBeVisible();
  await expect(incidents.getByText("1 owner notified")).toBeVisible();
  await expect(incidents.getByText("Notice in: English")).toBeVisible();
  await context.close();

  // The owner's audit log names the incident.
  await page.goto(`/b/${owner.businessId}/settings/audit`);
  const entries = page.getByRole("table", { name: en.settings.audit.title });
  await expect(entries.getByRole("cell", { name: new RegExp(`^${en.settings.audit.entities.incident}`) })).toBeVisible();
});

test("the System page is not there for owners", async ({ page, owner, consoleErrors }) => {
  expect(owner.businessId).toBeTruthy();
  // The 404 page itself, and the browser's own /favicon.ico request that a 404
  // page sometimes draws in a full run.
  consoleErrors.allow(/status of 404 \(Not Found\) \(http:\/\/localhost:\d+\/(admin\/system|favicon\.ico)\)/);
  const response = await page.goto("/admin/system");

  expect(response?.status()).toBe(404);
  await expect(page.getByText(en.errors.notFoundTitle)).toBeVisible();
  await expect(page.getByRole("link", { name: texts.nav })).toHaveCount(0);
});

test.describe("on a phone", () => {
  test.use({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });

  for (const theme of ["dark", "light"] as const) {
    test(`the System page fits and passes the audit in the ${theme} theme`, async ({ page, request }) => {
      await signInContext(page.context(), await signInAsAdmin(request));
      await page.context().addCookies([{ name: "aw_theme", value: theme, url: WEB_URL }]);

      await page.goto("/admin/system");
      await expect(page.getByRole("heading", { level: 1, name: texts.title })).toBeVisible();
      await expect(page.getByRole("region", { name: texts.lanes.title })).toBeVisible();
      await waitForNetworkQuiet(page);
      expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
      const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
      const serious = results.violations.filter((violation) => violation.impact === "serious" || violation.impact === "critical");
      expect(serious.map((violation) => violation.id)).toEqual([]);
    });
  }
});
