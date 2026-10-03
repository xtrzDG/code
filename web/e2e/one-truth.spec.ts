/**
 * One truth on screen: the Inbox badge is the sum of the two tabs it stands
 * for, and the platform admin sees a margin (not "—") for the demo
 * restaurant, whose dollar provider costs reach lari through dated rates.
 */

import type { APIRequestContext, Locator, Page } from "@playwright/test";

import { signInAsDemoOwner } from "./support/demo";
import { API_URL, PLATFORM_ADMIN_EMAIL } from "./support/env";
import { expect, signInContext, test } from "./support/fixtures";
import { apiLogSize, waitForLoginCode } from "./support/login-codes";
import { en } from "./support/messages";

test.describe.configure({ timeout: 120_000 });

/** An address may ask for a login code every 30 seconds. */
const LOGIN_CODE_COOLDOWN_MS = 31_000;

/** The platform admin's token; waits out the cooldown when another spec just signed in. */
async function signInAsAdmin(request: APIRequestContext): Promise<string> {
  for (let attempt = 0; ; attempt += 1) {
    const since = apiLogSize();
    const start = await request.post(`${API_URL}/v1/auth/otp/start`, { data: { email: PLATFORM_ADMIN_EMAIL, locale: "en" } });
    if (start.status() === 429 && attempt === 0) {
      await new Promise((resolve) => setTimeout(resolve, LOGIN_CODE_COOLDOWN_MS));
      continue;
    }
    expect(start.status(), await start.text()).toBe(200);
    const challengeId = ((await start.json()) as { challenge_id: string }).challenge_id;
    const code = await waitForLoginCode({ since });
    const verify = await request.post(`${API_URL}/v1/auth/otp/verify`, { data: { challenge_id: challengeId, code } });
    expect(verify.status(), await verify.text()).toBe(200);
    return ((await verify.json()) as { access_token: string }).access_token;
  }
}

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
  await signInContext(context, await signInAsAdmin(request));
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
