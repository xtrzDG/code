/**
 * Leaving and pausing (Settings → Billing): cancelling asks why first; a
 * move to another service brings a one-time credit instead, which keeps
 * the subscription and is offered once; a reason with nothing to offer
 * cancels right away. The demo salon, paid monthly, is offered a seasonal
 * pause from the end of its paid month at its price, for one to four
 * months with the dates of each; a trial cannot pause yet and the card
 * says why. (Scheduling the pause stops the automatic payments at the
 * payment provider, which this suite does not reach: the API tests cover it.)
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
  // A trial cannot pause yet: the card says why.
  await expect(page.getByText(texts.pause.unavailable.not_active)).toBeVisible();

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

test("the demo salon is offered a seasonal pause with its price and dates", async ({ page, context, request }) => {
  const demo = await signInAsDemoOwner(request);
  await signInContext(context, demo.token);
  const response = await request.get(`${API_URL}/v1/businesses`, { headers: { authorization: `Bearer ${demo.token}` } });
  const salon = ((await response.json()) as { id: string; name: string }[]).find((business) => business.name === DEMO_SALON);
  expect(salon, "the demo salon is seeded").toBeDefined();

  await page.goto(`/b/${salon!.id}/settings/billing`);
  const card = page.getByRole("region", { name: texts.pause.title });
  await expect(card.getByText(pattern(texts.pause.price))).toBeVisible();
  await expect(card.getByRole("button", { name: pattern(texts.pause.submit) })).toBeEnabled();

  const dates = card.getByText(pattern(texts.pause.window));
  const oneMonth = await dates.textContent();
  await card.getByText(texts.pause.months.other.replace("{count}", "4"), { exact: true }).click();
  await expect(dates).not.toHaveText(oneMonth ?? "");
  await expect(card.getByRole("radio", { name: texts.pause.months.other.replace("{count}", "4") })).toBeChecked();

  // The cancel dialog offers the same pause for a season's break.
  await page.getByRole("button", { name: billing.cancel }).click();
  const dialog = page.getByRole("dialog", { name: billing.dialogs.cancelTitle });
  await dialog.getByLabel(texts.reasons.seasonal_break).check();
  await dialog.getByRole("button", { name: texts.cancel.continue }).click();
  const offer = page.getByRole("dialog", { name: texts.cancel.offerTitle });
  await expect(offer.getByText(texts.offers.pause.title)).toBeVisible();
  await expect(offer.getByRole("button", { name: texts.offers.pause.confirm.one.replace("{count}", "1") })).toBeVisible();
  await offer.getByRole("button", { name: texts.cancel.back }).click();
  await page.keyboard.press("Escape");
  await expect(dialog).toBeHidden();
});
