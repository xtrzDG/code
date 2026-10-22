/**
 * The card for payments (Settings → Billing): a trial owner without a card
 * is asked to save one and told it charges nothing now; the demo salon,
 * paid monthly, shows its saved card by network, last digits and expiry
 * and offers to update it; back from the provider's page the owner sees
 * the card being confirmed. (The provider pages themselves need live
 * Flitt or Stripe keys; the API tests play them.)
 */

import type { APIRequestContext, Page } from "@playwright/test";

import { signInAsDemoOwner } from "./support/demo";
import { API_URL } from "./support/env";
import { expect, signInContext, test, type Owner } from "./support/fixtures";
import { en } from "./support/messages";

const texts = en.billingCard;
const DEMO_SALON = "Studio Lindenblatt";

async function startTrial(request: APIRequestContext, owner: Owner): Promise<void> {
  const response = await request.post(`${API_URL}/v1/businesses/${owner.businessId}/billing/trial`, {
    headers: { authorization: `Bearer ${owner.token}` },
    data: {},
  });
  expect(response.ok(), await response.text()).toBe(true);
}

function cardRegion(page: Page) {
  return page.getByRole("region", { name: texts.title });
}

test("a trial owner without a card is asked to save one that charges nothing now", async ({ page, request, owner }) => {
  await startTrial(request, owner);
  await page.goto(`/b/${owner.businessId}/settings/billing`);

  const card = cardRegion(page);
  await expect(card.getByText(texts.noCard)).toBeVisible();
  await expect(card.getByText(texts.noCardTrial)).toBeVisible();
  await expect(card.getByText(texts.facts.provider)).toBeVisible();
  await expect(card.getByText("Flitt", { exact: true })).toBeVisible();
  await expect(card.getByText(texts.noCharge)).toBeVisible();
  await expect(card.getByRole("button", { name: texts.save })).toBeVisible();
  // The trial's own notice stays until day 10 of the trial.
  await expect(page.getByText(/days? of the trial left$/)).toHaveCount(0);
});

test("the demo salon shows its saved card and offers to update it", async ({ page, context, request }) => {
  const demo = await signInAsDemoOwner(request);
  await signInContext(context, demo.token);
  const response = await request.get(`${API_URL}/v1/businesses`, { headers: { authorization: `Bearer ${demo.token}` } });
  const salon = ((await response.json()) as { id: string; name: string }[]).find((business) => business.name === DEMO_SALON);
  expect(salon, "the demo salon is seeded").toBeDefined();

  await page.goto(`/b/${salon!.id}/settings/billing`);
  const card = cardRegion(page);
  await expect(card.getByText("Mastercard •••• 4417")).toBeVisible();
  await expect(card.getByText(texts.endingIn.replace("{digits}", "4417"))).toBeAttached();
  await expect(card.getByText(/^Expires 09\/\d{2}$/)).toBeVisible();
  await expect(card.getByText(texts.facts.savedAt)).toBeVisible();
  await expect(card.getByRole("button", { name: texts.update })).toBeVisible();
  await expect(card.getByText(texts.noCard)).toHaveCount(0);
});

test("back from the provider's page the owner sees the card being confirmed", async ({ page, request, owner }) => {
  await startTrial(request, owner);
  await page.goto(`/b/${owner.businessId}/settings/billing?card=return`);

  const notice = page.getByRole("status").filter({ hasText: texts.returned.pending });
  await expect(page.getByText(texts.returned.title, { exact: true })).toBeVisible();
  await expect(notice).toBeVisible();
  await page.getByRole("button", { name: en.common.close }).click();
  await expect(page.getByText(texts.returned.title, { exact: true })).toBeHidden();
  await expect(page).toHaveURL(new RegExp(`/b/${owner.businessId}/settings/billing$`));
});
