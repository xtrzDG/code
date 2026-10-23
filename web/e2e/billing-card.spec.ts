/**
 * The card for payments (Settings → Billing): a trial owner without a card
 * is asked to save one and told it charges nothing now; the demo salon,
 * paid monthly, shows its saved card by network, last digits and expiry
 * and offers to update it; back from the provider's page the owner sees
 * the card being confirmed. Updating the card leaves for the provider's
 * page under the strict policy (nonce'd styles, Trusted Types) without a
 * single violation: the page is a top-level navigation, which the policy
 * does not restrict. (The provider pages themselves need live Flitt or
 * Stripe keys; the API tests play them, and here the test serves them.)
 */

import type { APIRequestContext, Page } from "@playwright/test";

import { expectStrictPolicy } from "./support/csp";
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
  await expect(card.getByText(texts.facts.provider, { exact: true })).toBeVisible();
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

test("updating the card leaves for the provider's page without a policy violation", async ({ page, context, request }) => {
  const demo = await signInAsDemoOwner(request);
  await signInContext(context, demo.token);
  const response = await request.get(`${API_URL}/v1/businesses`, { headers: { authorization: `Bearer ${demo.token}` } });
  const salon = ((await response.json()) as { id: string; name: string }[]).find((business) => business.name === DEMO_SALON);
  expect(salon, "the demo salon is seeded").toBeDefined();
  const providerPage = "https://checkout.stripe.com/c/pay/cs_test_e2e_card_update";
  const asked: unknown[] = [];
  await page.route(`**/api/backend/v1/businesses/${salon!.id}/billing/payment-method*`, (route) => {
    if (route.request().method() !== "POST") {
      return route.fallback();
    }
    asked.push(route.request().postDataJSON());
    return route.fulfill({ json: { provider: "stripe", url: providerPage, payment_order_id: null } });
  });
  await page.route("https://checkout.stripe.com/**", (route) =>
    route.fulfill({ contentType: "text/html", body: "<!doctype html><title>Stripe Checkout</title><p>Card</p>" }),
  );
  // Violations of every document reach the test, the billing page's up to
  // the moment it is left included.
  const violations: string[] = [];
  await page.exposeFunction("__policyViolation", (line: string) => violations.push(line));
  await page.addInitScript(() => {
    document.addEventListener("securitypolicyviolation", (event) => {
      const report = (window as unknown as { __policyViolation: (line: string) => Promise<number> }).__policyViolation;
      void report(`${event.effectiveDirective} ${event.blockedURI}`);
    });
  });

  const billing = await page.goto(`/b/${salon!.id}/settings/billing`);
  expectStrictPolicy(billing?.headers()["content-security-policy"] ?? "", "the billing page");
  await cardRegion(page).getByRole("button", { name: texts.update }).click();
  await page.waitForURL(providerPage);

  expect(asked).toHaveLength(1);
  expect(violations, "the card update broke the policy").toEqual([]);
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
