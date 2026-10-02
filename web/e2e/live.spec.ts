/**
 * The live cabinet: what happens elsewhere shows up in an open tab without
 * a reload. The demo restaurant (SEED_DEMO_DATA) is live with its website
 * chat switched on, so a visitor's message through the real widget API
 * reaches its assistant; the suite's API has no model key, so the
 * assistant passes the conversation to a person, and the cabinet hears
 * `handoff.created` on its event stream (API → BFF → browser).
 */

import type { APIRequestContext, Page } from "@playwright/test";

import { signInByEmail, uniqueSuffix } from "./support/api";
import { API_URL } from "./support/env";
import { expect, signInContext, test } from "./support/fixtures";
import { en } from "./support/messages";

const DEMO_OWNER_EMAIL = "demo@example.com";
const DEMO_RESTAURANT = "Mtsvane Ezo";

test.describe.configure({ timeout: 120_000 });

interface DemoOwner {
  token: string;
  businessId: string;
}

/** An address may ask for a login code every 30 seconds. */
const LOGIN_CODE_COOLDOWN_MS = 31_000;

let demoOwner: Promise<DemoOwner> | undefined;

/** The demo owner, signed in once per worker (both tests share the address). */
function signInAsDemoOwner(request: APIRequestContext): Promise<DemoOwner> {
  demoOwner ??= signInOnce(request);
  return demoOwner;
}

async function signInOnce(request: APIRequestContext): Promise<DemoOwner> {
  if (test.info().retry > 0) {
    // A retry runs in a new worker, maybe within the cooldown of the first sign-in.
    await new Promise((resolve) => setTimeout(resolve, LOGIN_CODE_COOLDOWN_MS));
  }
  const token = await signInByEmail(request, DEMO_OWNER_EMAIL);
  const response = await request.get(`${API_URL}/v1/businesses`, { headers: { authorization: `Bearer ${token}` } });
  expect(response.ok(), await response.text()).toBe(true);
  const businesses = (await response.json()) as { id: string; name: string }[];
  const restaurant = businesses.find((business) => business.name === DEMO_RESTAURANT);
  expect(restaurant, "the demo restaurant is seeded").toBeDefined();
  return { token, businessId: restaurant!.id };
}

async function openHandoffCount(request: APIRequestContext, owner: DemoOwner): Promise<number> {
  const response = await request.get(`${API_URL}/v1/businesses/${owner.businessId}/attention-counts`, {
    headers: { authorization: `Bearer ${owner.token}` },
  });
  expect(response.ok(), await response.text()).toBe(true);
  return ((await response.json()) as { open_handoff_count: number }).open_handoff_count;
}

/** A visitor writes in the website chat; the assistant hands the chat to a person. */
async function visitorAsksForPerson(request: APIRequestContext, businessId: string, visitor: string): Promise<void> {
  const response = await request.post(`${API_URL}/v1/widget/${businessId}/messages`, {
    data: { session_key: `e2e_live_${uniqueSuffix()}_visitor`, text: "Hello, can I talk to a manager?", contact_name: visitor },
  });
  expect(response.ok(), await response.text()).toBe(true);
  expect(((await response.json()) as { is_handed_off: boolean }).is_handed_off).toBe(true);
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

function handoffsLink(page: Page) {
  return page
    .getByRole("navigation", { name: en.nav.mainNavigation })
    .getByRole("link", { name: new RegExp(`^${en.navigation.pages.messagesHandoffs}`) });
}

test("a customer who needs a person appears at once, and the badge counts them", async ({ page, context, request }) => {
  const owner = await signInAsDemoOwner(request);
  await signInContext(context, owner.token);
  const before = await openHandoffCount(request, owner);

  await page.goto(`/b/${owner.businessId}/messages/handoffs`);
  await expect(page.locator('[data-live-status="live"]')).toBeVisible();
  await expect(page.getByText(en.live.updatedJustNow)).toBeVisible();
  await expect(handoffsLink(page)).toHaveAccessibleName(new RegExp(`${before} waiting`));
  await expect.poll(() => titleCount(page)).toBeGreaterThan(0);
  const titleBefore = await titleCount(page);
  await markDocument(page);

  const visitor = `Live visitor ${uniqueSuffix()}`;
  await visitorAsksForPerson(request, owner.businessId, visitor);

  await expect(page.getByText(visitor)).toBeVisible();
  await expect(handoffsLink(page)).toHaveAccessibleName(new RegExp(`${before + 1} waiting`));
  await expect.poll(() => titleCount(page)).toBe(titleBefore + 1);
  // On the list itself no toast: the new card is the news.
  await expect(page.getByText(en.live.needsPersonTitle)).toHaveCount(0);
  await expectSameDocument(page);
});

test("elsewhere in the cabinet a toast says so and opens the handoffs", async ({ page, context, request }) => {
  const owner = await signInAsDemoOwner(request);
  await signInContext(context, owner.token);

  await page.goto(`/b/${owner.businessId}/bookings`);
  await expect(page.locator('[data-live-status="live"]')).toBeVisible();
  await markDocument(page);

  const visitor = `Live visitor ${uniqueSuffix()}`;
  await visitorAsksForPerson(request, owner.businessId, visitor);

  await expect(page.getByText(en.live.needsPersonTitle)).toBeVisible();
  await page.getByRole("button", { name: en.live.needsPersonOpen }).click();
  await expect(page).toHaveURL(new RegExp(`/b/${owner.businessId}/messages/handoffs`));
  await expect(page.getByText(visitor)).toBeVisible();
  await expectSameDocument(page);
});
