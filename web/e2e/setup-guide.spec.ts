/**
 * The setup guide on the Overview (GET …/setup → `guide`): a business being
 * set up sees its steps, a progress ring in the bar and the way back into
 * the tunnel where the owner left off; a live business is led to its first
 * customers (a test from the phone, a second channel, the link for
 * customers) and is never told to "connect every channel" again.
 */

import type { Page } from "@playwright/test";

import { signInAsDemoOwner } from "./support/demo";
import { expect, signInContext, test } from "./support/fixtures";
import { en } from "./support/messages";

const RING_LABEL = /^Setup \d+% done$/;

function guide(page: Page) {
  return page.getByRole("region", { name: new RegExp(`${en.setupGuide.titleSetup}|${en.setupGuide.titleLive}`) });
}

test("a business being set up sees the guide and goes back into the tunnel", async ({ page, owner }) => {
  await page.goto(`/b/${owner.businessId}/overview`);
  const card = guide(page);
  await expect(card.getByRole("heading", { name: en.setupGuide.titleSetup })).toBeVisible();
  // The steps of the setup, then the three after the launch, waiting.
  await expect(card.getByRole("listitem")).toHaveCount(10);
  await expect(card.getByText(en.setupGuide.afterLaunchHint)).toBeVisible();
  // The status card gave way to the guide.
  await expect(page.getByText(en.dashboard.status.onboarding.title)).toHaveCount(0);
  await expect(page.getByText(en.dashboard.status.testing.title)).toHaveCount(0);

  // The bar keeps the progress in sight on every page and leads back here.
  await page.goto(`/b/${owner.businessId}/inbox`);
  const ring = page.getByRole("link", { name: RING_LABEL }).first();
  await expect(ring).toBeVisible();
  await ring.click();
  await expect(page).toHaveURL(new RegExp(`/b/${owner.businessId}/overview#setup-guide$`));

  // "Continue setup" opens the full-screen tunnel where the owner left off.
  await guide(page).getByRole("link", { name: en.setupGuide.continueSetup }).click();
  await expect(page).toHaveURL(new RegExp(`/b/${owner.businessId}/setup`));
  await expect(page.getByRole("navigation", { name: en.tunnel.railLabel })).toBeVisible();
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
});

test("a skipped optional step can be brought back", async ({ page, owner }) => {
  await page.goto(`/b/${owner.businessId}/overview`);
  const card = guide(page);
  const skip = card.getByRole("button", { name: /^Skip “/ }).first();
  await expect(skip).toBeVisible();
  const name = (await skip.getAttribute("aria-label"))?.replace(/^Skip “|”$/g, "") ?? "";
  await skip.click();
  await expect(card.getByRole("button", { name: `Bring back “${name}”` })).toBeVisible();
  await expect(card.getByText(en.setupGuide.status.skipped).first()).toBeVisible();
  await card.getByRole("button", { name: `Bring back “${name}”` }).click();
  await expect(card.getByRole("button", { name: `Skip “${name}”` })).toBeVisible();
});

test("the live demo business is led to its first customers, not told to connect every channel", async ({ page, context, request }) => {
  const owner = await signInAsDemoOwner(request);
  await signInContext(context, owner.token);
  await page.goto(`/b/${owner.businessId}/overview`);
  // The guide is about the customers now: a test from the phone comes first.
  const live = guide(page);
  await expect(live.getByRole("heading", { name: en.setupGuide.titleLive })).toBeVisible();
  await expect(live.getByRole("heading", { name: "Try it from your phone" })).toBeVisible();
  await expect(page.getByText(/connect (every|all) channel/i)).toHaveCount(0);
  // No status card and no way back into the setup: the assistant is live.
  await expect(page.getByText(en.dashboard.status.live.title)).toHaveCount(0);
  await expect(page.getByRole("heading", { name: en.setupGuide.titleSetup })).toHaveCount(0);
  await expect(page.getByRole("link", { name: en.setupGuide.continueSetup })).toHaveCount(0);
});

test.describe("on a phone", () => {
  test.use({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });

  test("the guide fits the screen and the ring sits in the top bar", async ({ page, owner }) => {
    await page.goto(`/b/${owner.businessId}/overview`);
    await expect(guide(page).getByRole("heading", { name: en.setupGuide.titleSetup })).toBeVisible();
    await expect(page.getByRole("link", { name: RING_LABEL }).first()).toBeVisible();
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(overflow).toBeLessThanOrEqual(0);
  });
});
