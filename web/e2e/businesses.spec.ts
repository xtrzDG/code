/**
 * Creating a business: the first two screens of "Create an AI assistant"
 * (/create), where the country brings its languages, currency and time
 * zone, and the business list that leads back into the tunnel.
 */

import type { Page } from "@playwright/test";

import { API_URL } from "./support/env";
import { expect, test } from "./support/fixtures";
import { en } from "./support/messages";

async function describeSalon(page: Page, name: string): Promise<void> {
  await page.goto("/create");
  await page.getByLabel(en.tunnelBusiness.business.name).fill(name);
  await page.locator("label").filter({ hasText: /^Beauty salons/ }).click();
  await page.getByRole("checkbox", { name: "Hair" }).check();
  await page.getByRole("button", { name: en.tunnel.continue, exact: true }).click();
  await expect(page.getByRole("heading", { level: 1, name: en.tunnelBusiness.place.title })).toBeVisible();
}

test("creates a business in another country with its languages", async ({ page, account, request }) => {
  await describeSalon(page, "Kuaför Güneş");
  await page.getByLabel(en.tunnelBusiness.place.country).selectOption("TR");

  // Turkey's defaults: Turkish and English, lira, Istanbul time (one zone, so no choice shown).
  const languages = page.getByRole("group", { name: en.tunnelBusiness.place.languages });
  await expect(languages.getByRole("checkbox", { name: /Türkçe/ })).toBeChecked();
  await expect(languages.getByRole("checkbox", { name: /English/ })).toBeChecked();
  await expect(page.getByText(/\(TRY\)/)).toBeVisible();
  await expect(page.getByLabel(en.tunnelBusiness.place.timezone)).toHaveCount(0);
  // Arabic is offered on request (and is written right to left).
  // Each language is a chip: its label is what a person taps.
  await languages.locator("label").filter({ hasText: /Arabic|العربية/ }).click();
  await expect(languages.getByRole("checkbox", { name: /Arabic|العربية/ })).toBeChecked();
  await page.getByLabel(en.tunnelBusiness.place.defaultLanguage).selectOption("tr");
  await page.getByLabel(en.tunnelBusiness.place.city).fill("İzmir");
  await page.getByLabel(en.tunnelBusiness.place.address).fill("Kıbrıs Şehitleri Cd. 1, İzmir");
  await page.getByRole("button", { name: en.tunnel.continue, exact: true }).click();

  // Created: the tunnel goes on with what the salon offers.
  await expect(page).toHaveURL(/\/b\/[^/]+\/setup\?step=offer$/, { timeout: 20_000 });
  const businessId = /\/b\/([^/]+)\/setup/.exec(new URL(page.url()).pathname)?.[1] ?? "";
  const stored = await request.get(`${API_URL}/v1/businesses/${businessId}`, { headers: { authorization: `Bearer ${account.token}` } });
  const business = (await stored.json()) as { country_code: string; city: string; languages: string[]; default_language: string; currency_code: string; timezone: string };
  expect(business).toMatchObject({ country_code: "TR", city: "İzmir", default_language: "tr", currency_code: "TRY", timezone: "Europe/Istanbul" });
  expect(business.languages).toEqual(expect.arrayContaining(["tr", "en", "ar"]));

  // The business is on the list, and its card leads back into the tunnel.
  await page.goto("/businesses");
  await page.getByRole("link", { name: /Kuaför Güneş/ }).click();
  await expect(page).toHaveURL(new RegExp(`/b/${businessId}/setup`));
});

test("a business in a country with several time zones starts in the one chosen", async ({ page, account, request }) => {
  await describeSalon(page, "Peluquería Teide");
  await page.getByLabel(en.tunnelBusiness.place.country).selectOption("ES");

  // The browser runs in Berlin, which is not a Spanish zone: Madrid first.
  const zone = page.getByLabel(en.tunnelBusiness.place.timezone);
  await expect(zone).toHaveValue("Europe/Madrid");
  await zone.selectOption("Atlantic/Canary");
  await page.getByLabel(en.tunnelBusiness.place.address).fill("Calle La Marina 1, Santa Cruz");
  await page.getByRole("button", { name: en.tunnel.continue, exact: true }).click();

  await expect(page).toHaveURL(/\/b\/[^/]+\/setup\?step=offer$/, { timeout: 20_000 });
  const businessId = /\/b\/([^/]+)\/setup/.exec(new URL(page.url()).pathname)?.[1] ?? "";
  const stored = await request.get(`${API_URL}/v1/businesses/${businessId}`, { headers: { authorization: `Bearer ${account.token}` } });
  expect(((await stored.json()) as { timezone: string }).timezone).toBe("Atlantic/Canary");
});

test("a failed creation says why and keeps every answer", async ({ page, account, consoleErrors }) => {
  expect(account.token).toBeTruthy();
  consoleErrors.allow(/Failed to load resource: the server responded with a status of 503/);
  await page.route("**/api/backend/v1/assistants", (route) =>
    route.request().method() === "POST"
      ? route.fulfill({
          status: 503,
          contentType: "application/json",
          body: JSON.stringify({ error: "backend_unavailable", message: "Maintenance" }),
        })
      : route.fallback(),
  );
  await describeSalon(page, "Panadería Sol");
  await page.getByLabel(en.tunnelBusiness.place.country).selectOption("ES");
  await page.getByLabel(en.tunnelBusiness.place.address).fill("Calle Mayor 5, Madrid");
  await page.getByRole("button", { name: en.tunnel.continue, exact: true }).click();

  const toast = page.getByRole("alert").filter({ hasText: en.errors.codes.backend_unavailable });
  await expect(toast).toBeVisible();
  await expect(page).toHaveURL(/\/create\?step=place$/);
  await expect(page.getByLabel(en.tunnelBusiness.place.address)).toHaveValue("Calle Mayor 5, Madrid");
  // The first screen kept its answers too (they live in this browser until the business exists).
  await page.reload();
  await page.getByRole("button", { name: en.tunnel.back }).click();
  await expect(page.getByLabel(en.tunnelBusiness.business.name)).toHaveValue("Panadería Sol");
});
