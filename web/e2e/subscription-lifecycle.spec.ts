/**
 * Leaving and pausing (Settings → Billing): cancelling asks why first; a
 * move to another service brings a one-time credit instead, which keeps
 * the subscription and is offered once; a reason with nothing to offer
 * cancels right away. The seasonal pause stores a subscription as
 * `paused`, a value behind a closed release gate in this release
 * (docs/operations/deploys.md): even with SUBSCRIPTION_PAUSE_ENABLED the
 * demo salon, paid monthly, sees no pause card and a season's break brings
 * no pause offer until the next release opens the gate. (The API tests
 * play that next release: pausing, billing while paused, resuming.)
 */

import type { APIRequestContext, Locator, Page } from "@playwright/test";

import { signInAsDemoOwner } from "./support/demo";
import { API_URL } from "./support/env";
import { expect, signInContext, test, type Owner } from "./support/fixtures";
import { en } from "./support/messages";

const texts = en.billingLifecycle;
const billing = en.billing;
const DEMO_SALON = "Studio Lindenblatt";

/** A toast with this text. */
function toast(page: Page, text: string): Locator {
  return page.getByRole("status").getByText(text, { exact: true });
}

/** A dictionary text with its {placeholders} matching anything. */
function pattern(text: string): RegExp {
  const escaped = text.replace(/[.*+?^$()|[\]\\]/g, "\\$&");
  return new RegExp(`^${escaped.replace(/\\?\{[a-z]+\\?\}/gi, ".+")}$`);
}

async function startTrial(request: APIRequestContext, owner: Owner): Promise<void> {
  const response = await request.post(`${API_URL}/v1/businesses/${owner.businessId}/billing/trial`, {
    headers: { authorization: `Bearer ${owner.token}` },
    data: {},
  });
  expect(response.ok(), await response.text()).toBe(true);
}

test("an owner leaving for another service takes the credit instead, and it is offered once", async ({ page, request, owner }) => {
  await startTrial(request, owner);
  await page.goto(`/b/${owner.businessId}/settings/billing`);

  await page.getByRole("button", { name: billing.cancel }).click();
  let dialog = page.getByRole("dialog", { name: billing.dialogs.cancelTitle });
  await expect(dialog.getByRole("button", { name: texts.cancel.continue })).toBeHidden();
  await dialog.getByLabel(texts.reasons.switched_provider).check();
  await dialog.getByLabel(texts.cancel.detailsLabel).fill("Our chain moves to one system for every branch");
  await dialog.getByRole("button", { name: texts.cancel.continue }).click();

  const offer = page.getByRole("dialog", { name: texts.cancel.offerTitle });
  await expect(offer.getByText(pattern(texts.offers.credit.title))).toBeVisible();
  await offer.getByRole("button", { name: texts.offers.credit.confirm }).click();
  await expect(toast(page, texts.offers.taken.credit)).toBeVisible();
  await expect(page.getByText(billing.status.trialing, { exact: true })).toBeVisible();

  // Taken once: the same reason now cancels straight away.
  await page.getByRole("button", { name: billing.cancel }).click();
  dialog = page.getByRole("dialog", { name: billing.dialogs.cancelTitle });
  await dialog.getByLabel(texts.reasons.switched_provider).check();
  await expect(dialog.getByRole("button", { name: texts.cancel.continue })).toBeHidden();
  await dialog.getByRole("button", { name: billing.dialogs.cancelConfirm }).click();
  await expect(toast(page, billing.dialogs.cancelled)).toBeVisible();
  await expect(page.getByText(billing.status.cancelled, { exact: true })).toBeVisible();
});

test("an owner closing the business cancels without an offer, and may go back from one", async ({ page, request, owner }) => {
  await startTrial(request, owner);
  await page.goto(`/b/${owner.businessId}/settings/billing`);

  await page.getByRole("button", { name: billing.cancel }).click();
  const dialog = page.getByRole("dialog", { name: billing.dialogs.cancelTitle });
  await dialog.getByLabel(texts.reasons.switched_provider).check();
  await dialog.getByRole("button", { name: texts.cancel.continue }).click();
  const offer = page.getByRole("dialog", { name: texts.cancel.offerTitle });
  await offer.getByRole("button", { name: texts.cancel.back }).click();

  await dialog.getByLabel(texts.reasons.closing_business).check();
  await dialog.getByRole("button", { name: billing.dialogs.cancelConfirm }).click();
  await expect(toast(page, billing.dialogs.cancelled)).toBeVisible();
  await expect(page.getByText(billing.status.cancelled, { exact: true })).toBeVisible();
});

test("the demo salon is offered no seasonal pause while its release gate is closed", async ({ page, context, request }) => {
  const demo = await signInAsDemoOwner(request);
  await signInContext(context, demo.token);
  const response = await request.get(`${API_URL}/v1/businesses`, { headers: { authorization: `Bearer ${demo.token}` } });
  const salon = ((await response.json()) as { id: string; name: string }[]).find((business) => business.name === DEMO_SALON);
  expect(salon, "the demo salon is seeded").toBeDefined();

  await page.goto(`/b/${salon!.id}/settings/billing`);
  await expect(page.getByRole("button", { name: billing.cancel })).toBeVisible();
  await expect(page.getByRole("region", { name: texts.pause.title })).toHaveCount(0);

  // A season's break has nothing to offer yet: the dialog cancels directly.
  await page.getByRole("button", { name: billing.cancel }).click();
  const dialog = page.getByRole("dialog", { name: billing.dialogs.cancelTitle });
  await dialog.getByLabel(texts.reasons.seasonal_break).check();
  await expect(dialog.getByRole("button", { name: texts.cancel.continue })).toBeHidden();
  await expect(dialog.getByRole("button", { name: billing.dialogs.cancelConfirm })).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(dialog).toBeHidden();
});
