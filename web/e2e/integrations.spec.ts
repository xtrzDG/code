/**
 * Settings → Integrations: the owner adds a webhook (an address inside a
 * network is refused; the signing secret is shown once), sends a test event
 * to an address that does not exist and reads why it failed in the delivery
 * log with the request body, pauses and deletes it; then creates an API key
 * (the token is shown once), calls the public API with it, is refused a
 * scope it was not given, and revokes it. Nothing leaves the machine: the
 * webhook's domain is under `.invalid`, which never resolves.
 */

import { API_URL } from "./support/env";
import { expect, test } from "./support/fixtures";
import { en } from "./support/messages";
import { waitForNetworkQuiet } from "./support/network";

test.describe.configure({ timeout: 120_000 });

const HOOK = "https://hooks.workshop-e2e.invalid/in";

test("webhooks: refused private address, secret once, test event logged with its body, pause and delete", async ({ page, owner, consoleErrors }) => {
  // The refused address answers 422, which the browser logs.
  consoleErrors.allow(/status of 422/);
  await page.goto(`/b/${owner.businessId}/settings/integrations`);
  await waitForNetworkQuiet(page);
  await expect(page.getByText(en.apiIntegrations.webhooks.empty)).toBeVisible();

  await page.getByRole("button", { name: en.apiIntegrations.webhooks.add }).click();
  const dialog = page.getByRole("dialog", { name: en.apiIntegrations.webhooks.dialog.addTitle });
  await dialog.getByLabel(en.apiIntegrations.webhooks.dialog.url).fill("https://127.0.0.1/in");
  await dialog.getByLabel(en.apiIntegrations.events.booking_created).check();
  await dialog.getByRole("button", { name: en.apiIntegrations.webhooks.dialog.create }).click();
  await expect(dialog.getByText(en.apiIntegrations.webhooks.reasons.not_public)).toBeVisible();

  await dialog.getByLabel(en.apiIntegrations.webhooks.dialog.url).fill(HOOK);
  await dialog.getByLabel(en.apiIntegrations.webhooks.dialog.label, { exact: false }).fill("CRM");
  await dialog.getByRole("button", { name: en.apiIntegrations.webhooks.dialog.create }).click();
  const secret = page.getByRole("dialog", { name: en.apiIntegrations.secret.webhookTitle });
  await expect(secret.getByLabel(en.apiIntegrations.secret.value)).toHaveText(/^whsec_[A-Za-z0-9_-]{43}$/);
  await secret.getByRole("button", { name: en.apiIntegrations.secret.done }).click();

  const row = page.getByRole("listitem").filter({ hasText: HOOK });
  await expect(row.getByText(en.apiIntegrations.webhooks.statuses.active, { exact: true })).toBeVisible();
  await row.getByRole("button", { name: en.apiIntegrations.webhooks.actions.menu }).click();
  await page.getByRole("menuitem", { name: en.apiIntegrations.webhooks.actions.test }).click();
  await expect(page.getByText(en.apiIntegrations.webhooks.toasts.testFailed)).toBeVisible();

  await row.getByRole("button", { name: en.apiIntegrations.webhooks.actions.menu }).click();
  await page.getByRole("menuitem", { name: en.apiIntegrations.webhooks.actions.deliveries }).click();
  const log = page.getByRole("dialog", { name: en.apiIntegrations.deliveries.title });
  const delivery = log.getByRole("listitem").filter({ hasText: en.apiIntegrations.events.webhook_test });
  await expect(delivery.getByText(en.apiIntegrations.deliveries.statuses.failed)).toBeVisible();
  await delivery.getByRole("button", { name: en.apiIntegrations.deliveries.showBody }).click();
  await expect(log.getByLabel(en.apiIntegrations.deliveries.body)).toContainText('"type": "webhook.test"');
  // The drawer's own close button (a toast over its footer has one too).
  await log.locator("header").getByRole("button", { name: en.common.close }).click();
  await expect(log).toBeHidden();

  await row.getByRole("button", { name: en.apiIntegrations.webhooks.actions.menu }).click();
  await page.getByRole("menuitem", { name: en.apiIntegrations.webhooks.actions.pause }).click();
  await expect(row.getByText(en.apiIntegrations.webhooks.statuses.paused, { exact: true })).toBeVisible();

  await row.getByRole("button", { name: en.apiIntegrations.webhooks.actions.menu }).click();
  await page.getByRole("menuitem", { name: en.apiIntegrations.webhooks.actions.delete }).click();
  await page.getByRole("button", { name: en.apiIntegrations.webhooks.deleteDialog.confirm }).click();
  await expect(page.getByText(en.apiIntegrations.webhooks.empty)).toBeVisible();
});

test("API keys: the token is shown once, works with its scopes only, and stops working when revoked", async ({ page, request, owner }) => {
  await page.goto(`/b/${owner.businessId}/settings/integrations`);
  await waitForNetworkQuiet(page);
  await page.getByRole("button", { name: en.apiIntegrations.apiKeys.add }).click();
  const dialog = page.getByRole("dialog", { name: en.apiIntegrations.apiKeys.dialog.title });
  await dialog.getByLabel(en.apiIntegrations.apiKeys.dialog.name).fill("Zapier");
  await dialog.getByLabel(en.apiIntegrations.apiKeys.scopes.bookings_read).check();
  await dialog.getByRole("button", { name: en.apiIntegrations.apiKeys.dialog.create }).click();

  const shown = page.getByRole("dialog", { name: en.apiIntegrations.secret.apiKeyTitle });
  const token = (await shown.getByLabel(en.apiIntegrations.secret.value).textContent()) ?? "";
  expect(token).toMatch(/^awk_[a-z2-7]{8}_[A-Za-z0-9]{40}$/);
  await shown.getByRole("button", { name: en.apiIntegrations.secret.done }).click();
  const row = page.getByRole("listitem").filter({ hasText: "Zapier" });
  await expect(row.getByText(`${token.slice(0, 12)}_…`)).toBeVisible();

  const headers = { authorization: `Bearer ${token}` };
  const me = await request.get(`${API_URL}/v1/public-api/me`, { headers });
  expect(me.status(), await me.text()).toBe(200);
  expect((await me.json()).business_id).toBe(owner.businessId);
  expect((await request.get(`${API_URL}/v1/public-api/bookings`, { headers })).status()).toBe(200);
  const leads = await request.get(`${API_URL}/v1/public-api/leads`, { headers });
  expect(leads.status()).toBe(403);
  expect(JSON.stringify(await leads.json())).toContain("missing_scope");

  await row.getByRole("button", { name: en.apiIntegrations.apiKeys.revoke }).click();
  await page.getByRole("button", { name: en.apiIntegrations.apiKeys.revokeDialog.confirm }).click();
  await expect(row.getByText(en.apiIntegrations.apiKeys.statuses.revoked, { exact: true })).toBeVisible();
  expect((await request.get(`${API_URL}/v1/public-api/me`, { headers })).status()).toBe(401);
});
