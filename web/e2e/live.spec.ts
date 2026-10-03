/**
 * The live cabinet: what happens elsewhere shows up in an open tab without
 * a reload. A visitor of the demo restaurant asks for a person (see
 * support/demo.ts), and the cabinet hears `handoff.created` on its event
 * stream (API → BFF → browser).
 */

import type { APIRequestContext, Page } from "@playwright/test";

import { uniqueSuffix } from "./support/api";
import { signInAsDemoOwner, visitorAsksForPerson, type DemoOwner } from "./support/demo";
import { API_URL } from "./support/env";
import { expect, signInContext, test } from "./support/fixtures";
import { en } from "./support/messages";

test.describe.configure({ timeout: 120_000 });

/** What the Inbox badge counts: customers waiting for a person and new requests. */
async function waitingCount(request: APIRequestContext, owner: DemoOwner): Promise<number> {
  const response = await request.get(`${API_URL}/v1/businesses/${owner.businessId}/attention-counts`, {
    headers: { authorization: `Bearer ${owner.token}` },
  });
  expect(response.ok(), await response.text()).toBe(true);
  const counts = (await response.json()) as { open_handoff_count: number; new_lead_count: number };
  return counts.open_handoff_count + counts.new_lead_count;
}

/** Marks the document, so a test can tell it was never reloaded. */
async function markDocument(page: Page): Promise<void> {
  await page.evaluate(() => document.documentElement.setAttribute("data-e2e-same-document", "yes"));
}

async function expectSameDocument(page: Page): Promise<void> {
  await expect(page.locator("html")).toHaveAttribute("data-e2e-same-document", "yes");
}

/** The waiting count at the start of the tab title ("(3) …"), 0 without one. */
async function titleCount(page: Page): Promise<number> {
  const match = /^\((\d+)\)/.exec(await page.title());
  return match ? Number(match[1]) : 0;
}

function inboxLink(page: Page) {
  return page
    .getByRole("navigation", { name: en.nav.mainNavigation })
    .getByRole("link", { name: new RegExp(`^${en.navigation.sections.inbox}`) });
}

test("a customer who needs a person appears at once, and the badge counts them", async ({ page, context, request }) => {
  const owner = await signInAsDemoOwner(request);
  await signInContext(context, owner.token);
  const before = await waitingCount(request, owner);

  await page.goto(`/b/${owner.businessId}/inbox`);
  await expect(page.locator('[data-live-status="live"]')).toBeVisible();
  await expect(page.getByText(en.live.updatedJustNow)).toBeVisible();
  await expect(inboxLink(page)).toHaveAccessibleName(new RegExp(`${before} waiting`));
  await expect.poll(() => titleCount(page)).toBeGreaterThan(0);
  const titleBefore = await titleCount(page);
  await markDocument(page);

  const visitor = `Live visitor ${uniqueSuffix()}`;
  await visitorAsksForPerson(request, owner.businessId, visitor);

  await expect(page.getByText(visitor)).toBeVisible();
  await expect(inboxLink(page)).toHaveAccessibleName(new RegExp(`${before + 1} waiting`));
  await expect.poll(() => titleCount(page)).toBe(titleBefore + 1);
  // On the list itself no toast: the new card is the news.
  await expect(page.getByText(en.live.needsPersonTitle)).toHaveCount(0);
  await expectSameDocument(page);
});

test("elsewhere in the cabinet a toast says so and opens the inbox", async ({ page, context, request }) => {
  const owner = await signInAsDemoOwner(request);
  await signInContext(context, owner.token);

  await page.goto(`/b/${owner.businessId}/bookings`);
  await expect(page.locator('[data-live-status="live"]')).toBeVisible();
  await markDocument(page);

  const visitor = `Live visitor ${uniqueSuffix()}`;
  await visitorAsksForPerson(request, owner.businessId, visitor);

  await expect(page.getByText(en.live.needsPersonTitle)).toBeVisible();
  await page.getByRole("button", { name: en.live.needsPersonOpen }).click();
  await expect(page).toHaveURL(new RegExp(`/b/${owner.businessId}/inbox$`));
  await expect(page.getByText(visitor)).toBeVisible();
  await expectSameDocument(page);
});
