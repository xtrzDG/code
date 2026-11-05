/**
 * One truth on screen: the Inbox badge is the sum of the two tabs it stands
 * for, and the platform admin sees a margin (not "—") for the demo
 * restaurant, whose dollar provider costs reach lari through dated rates.
 */

import type { Locator, Page } from "@playwright/test";

import { signInAsPlatformAdmin } from "./support/admin";
import { signInAsDemoOwner } from "./support/demo";
import { PLATFORM_ADMIN_EMAIL } from "./support/env";
import { expect, signInContext, test } from "./support/fixtures";
import { en } from "./support/messages";

test.describe.configure({ timeout: 120_000 });

/** The number an inbox tab shows next to its name. */
async function tabCount(page: Page, view: "needs_person" | "requests"): Promise<number> {
  const tab = page.locator("label", { has: page.locator(`input[type="radio"][value="${view}"]`) });
  const number = tab.locator("span[aria-hidden]").filter({ hasText: /^\d+$/ });
  await expect(number).toBeVisible();
  return Number(await number.innerText());
}

function inboxLink(page: Page): Locator {
  return page
    .getByRole("navigation", { name: en.nav.mainNavigation })
    .getByRole("link", { name: new RegExp(`^${en.navigation.sections.inbox}`) });
}

test("the Inbox badge is the sum of the Needs a person and Requests tabs", async ({ page, context, request }) => {
  const owner = await signInAsDemoOwner(request);
  await signInContext(context, owner.token);

  await page.goto(`/b/${owner.businessId}/inbox`);
  await expect(page.locator('[data-live-status="live"]')).toBeVisible();
  const needsPerson = await tabCount(page, "needs_person");
  const requests = await tabCount(page, "requests");

  expect(needsPerson + requests).toBeGreaterThan(0);
  await expect(inboxLink(page)).toHaveAccessibleName(new RegExp(`\\b${needsPerson + requests} waiting`));
});

test("the platform admin sees the demo restaurant's margin with the rate behind it", async ({ browser, request }) => {
  const owner = await signInAsDemoOwner(request);
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 }, reducedMotion: "reduce" });
  await signInContext(context, await signInAsPlatformAdmin(request, PLATFORM_ADMIN_EMAIL));
  const page = await context.newPage();

  await page.goto(`/admin/clients/${owner.businessId}`);
  const cost = page.locator("section", { has: page.getByRole("heading", { level: 2, name: en.admin.detail.costTitle }) });
  const margin = cost
    .locator("dl > div")
    .filter({ has: page.locator("dt", { hasText: new RegExp(`^${en.admin.detail.margin}$`) }) })
    .locator("dd");

  await expect(margin).toBeVisible();
  await expect(margin).not.toHaveText(en.admin.unknown);
  await expect(margin).toHaveText(/₾|GEL/);
  await expect(cost.getByText(en.admin.detail.rateSources.nbg, { exact: false })).toBeVisible();
  await expect(cost.getByText(en.admin.detail.noRate)).toHaveCount(0);
  await context.close();
});
