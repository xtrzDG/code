/**
 * Automated accessibility audit (axe-core, WCAG 2.1 A and AA rules) of the
 * cabinet's pages in both themes and on a phone: no serious or critical
 * violation is allowed. What axe cannot judge (reading order, meaning of
 * texts) is checked by hand; see web/README.md.
 */

import AxeBuilder from "@axe-core/playwright";
import type { Page } from "@playwright/test";

import { WEB_URL } from "./support/env";
import { expect, test } from "./support/fixtures";
import { waitForNetworkQuiet } from "./support/network";
import { en } from "./support/messages";

const OWNER_PAGES = [
  "overview",
  "inbox",
  "inbox?view=all",
  "bookings",
  "customers",
  "customers/segments",
  "assistant",
  "assistant/knowledge",
  "assistant/profile",
  "assistant/channels",
  "assistant/versions",
  "settings",
  "settings/team",
  "settings/notifications",
  "settings/quick-replies",
  "settings/calls",
  "settings/reviews",
  "settings/billing",
  "settings/privacy",
  "settings/audit",
];

/** Serious and critical violations of a page, one line each. */
async function seriousViolations(page: Page): Promise<string[]> {
  const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
  return results.violations
    .filter((violation) => violation.impact === "serious" || violation.impact === "critical")
    .map((violation) => `${violation.id} (${violation.impact}): ${violation.nodes.map((node) => node.target.join(" ")).join(" | ")}`);
}

async function audit(page: Page, path: string): Promise<void> {
  await page.goto(path);
  await expect(page.getByRole("heading", { level: 1 }).first()).toBeVisible();
  await waitForNetworkQuiet(page);
  expect(await seriousViolations(page), path).toEqual([]);
}

for (const theme of ["dark", "light"] as const) {
  test(`every section passes the audit in the ${theme} theme`, async ({ page, owner }) => {
    test.setTimeout(180_000);
    await page.context().addCookies([{ name: "aw_theme", value: theme, url: WEB_URL }]);
    for (const path of OWNER_PAGES) {
      await test.step(path, () => audit(page, `/b/${owner.businessId}/${path}`));
    }
  });
}

test("the setup invitation, the tunnel, the businesses, sign-in and the offline page pass the audit", async ({ page, newOwner }) => {
  await audit(page, `/b/${newOwner.businessId}/overview`);
  for (const step of ["business", "place", "offer", "hours", "people", "channels", "try", "launch"]) {
    await test.step(step, () => audit(page, `/b/${newOwner.businessId}/setup?step=${step}`));
  }
  await audit(page, "/create");
  await audit(page, "/businesses");
  await audit(page, "/offline");
  await page.context().clearCookies();
  await audit(page, "/login");
});

test.describe("on a phone", () => {
  test.use({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });

  test("the main pages and the More sheet pass the audit", async ({ page, owner }) => {
    for (const path of ["overview", "inbox", "assistant", "settings"]) {
      await test.step(path, () => audit(page, `/b/${owner.businessId}/${path}`));
    }
    await page.getByRole("button", { name: en.navigation.more }).click();
    await expect(page.getByRole("dialog", { name: en.navigation.more })).toBeVisible();
    expect(await seriousViolations(page)).toEqual([]);
  });

  for (const theme of ["dark", "light"] as const) {
    test(`the front desk pages, the page's (i) and the filters pass the audit in the ${theme} theme`, async ({ page, owner }) => {
      test.setTimeout(120_000);
      await page.context().addCookies([{ name: "aw_theme", value: theme, url: WEB_URL }]);
      for (const path of ["bookings", "bookings?view=all", "assistant/knowledge", "assistant/channels"]) {
        await test.step(path, () => audit(page, `/b/${owner.businessId}/${path}`));
      }
      await page.getByRole("button", { name: en.chrome.pageInfo }).click();
      await expect(page.getByRole("dialog")).toBeVisible();
      expect(await seriousViolations(page), "the page's (i)").toEqual([]);

      await page.goto(`/b/${owner.businessId}/bookings?view=all`);
      await page.getByRole("button", { name: en.chrome.filters.open, exact: true }).click();
      await expect(page.getByRole("dialog", { name: en.chrome.filters.title })).toBeVisible();
      expect(await seriousViolations(page), "the filters").toEqual([]);
    });
  }
});
