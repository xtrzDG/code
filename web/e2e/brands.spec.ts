/**
 * Brands: an owner groups locations of a chain under one brand, sees them
 * side by side, makes a new location from an existing one and finds them
 * grouped in the business switcher; a regional manager reaches only the
 * locations assigned to them, and loses even those once removed.
 */

import type { APIRequestContext, Page } from "@playwright/test";

import { createAssistant, createBusiness, signInByEmail, uniqueEmail, uniqueSuffix } from "./support/api";
import { API_URL } from "./support/env";
import { BERLIN_SALON, expect, signInContext, test, type Owner } from "./support/fixtures";
import { en } from "./support/messages";

/** A second salon of the same owner, its assistant created. */
async function secondLocation(request: APIRequestContext, owner: Owner, name: string): Promise<string> {
  const businessId = await createBusiness(request, owner.token, { ...BERLIN_SALON, name, city: "Potsdam" });
  await createAssistant(request, owner.token, businessId);
  return businessId;
}

/** Creates a brand on /brands from the owner's first business and returns its id. */
async function createBrand(page: Page, owner: Owner, name: string): Promise<string> {
  await page.goto("/brands");
  await page.getByRole("button", { name: en.brands.create.title }).first().click();
  const dialog = page.getByRole("dialog", { name: en.brands.create.title });
  await dialog.getByLabel(en.brands.create.name).fill(name);
  await dialog.getByLabel(en.brands.create.firstLocation).selectOption(owner.businessId);
  await dialog.getByRole("button", { name: en.brands.create.submit }).click();
  await expect(page).toHaveURL(/\/brands\/brand_[^/]+$/, { timeout: 20_000 });
  await expect(page.getByRole("heading", { level: 1, name })).toBeVisible();
  return new URL(page.url()).pathname.split("/").at(-1) ?? "";
}

async function addLocation(page: Page, businessId: string): Promise<void> {
  const locations = page.getByRole("region", { name: en.brands.locations.title });
  await locations.getByRole("button", { name: en.brands.locations.add }).click();
  const dialog = page.getByRole("dialog", { name: en.brands.locations.addTitle });
  await dialog.getByLabel(en.brands.locations.pick).selectOption(businessId);
  await dialog.getByRole("button", { name: en.brands.locations.add }).click();
  await expect(dialog).toBeHidden();
}

test("an owner groups locations into a brand, clones one and switches between them", async ({ page, owner, request }) => {
  const brandName = `Morgenrot ${uniqueSuffix()}`;
  const potsdamId = await secondLocation(request, owner, "Salon Morgenrot Potsdam");
  const brandId = await createBrand(page, owner, brandName);
  await addLocation(page, potsdamId);

  // Both locations side by side, each opening its own cabinet.
  await expect(page.getByRole("link", { name: `${en.brands.overview.open}: ${owner.businessName} · Berlin` })).toBeVisible();
  await expect(page.getByRole("link", { name: /Salon Morgenrot Potsdam/ })).toHaveAttribute("href", `/b/${potsdamId}/overview`);
  await page.getByRole("button", { name: en.brands.overview.periods["7d"] }).click();
  await expect(page.getByRole("button", { name: en.brands.overview.periods["7d"] })).toHaveAttribute("aria-pressed", "true");

  // "New location from…": a copy of the profile, never the channels' accounts.
  const locations = page.getByRole("region", { name: en.brands.locations.title });
  await locations.getByRole("button", { name: en.brands.locations.clone }).click();
  const clone = page.getByRole("dialog", { name: en.brands.locations.cloneTitle });
  await expect(clone.getByText(en.brands.locations.cloneNever)).toBeVisible();
  await clone.getByLabel(en.brands.locations.source).selectOption(potsdamId);
  await clone.getByLabel(en.brands.locations.name).fill("Salon Morgenrot Spandau");
  await clone.getByLabel(en.brands.locations.city).fill("Berlin-Spandau");
  await clone.getByRole("button", { name: en.brands.locations.cloneSubmit }).click();
  await expect(clone).toBeHidden({ timeout: 20_000 });
  await expect(locations.getByText("Salon Morgenrot Spandau")).toBeVisible();

  const stored = await request.get(`${API_URL}/v1/brands/${brandId}`, { headers: { authorization: `Bearer ${owner.token}` } });
  const brand = (await stored.json()) as { locations: { name: string }[] };
  expect(brand.locations.map((location) => location.name)).toHaveLength(3);

  // The switcher lists the brand's locations under its name.
  await page.goto(`/b/${potsdamId}/overview`);
  await page.getByRole("button", { name: new RegExp(en.shell.switchBusiness) }).first().click();
  const group = page.getByRole("group", { name: brandName });
  await expect(group.getByRole("link", { name: /Salon Morgenrot Spandau/ })).toBeVisible();
  await group.getByRole("link", { name: en.brands.switcher.overview }).click();
  await expect(page).toHaveURL(new RegExp(`/brands/${brandId}$`));
});

test("a regional manager reaches only their locations, and nothing once removed", async ({ browser, page, owner, request }) => {
  const potsdamId = await secondLocation(request, owner, "Salon Morgenrot Potsdam");
  const brandId = await createBrand(page, owner, `Morgenrot ${uniqueSuffix()}`);
  await addLocation(page, potsdamId);

  // The owner invites a manager for Potsdam only.
  const managerEmail = uniqueEmail();
  await page.getByRole("link", { name: en.brands.tabs.team }).click();
  await page.getByRole("button", { name: en.brands.team.invite }).click();
  const invite = page.getByRole("dialog", { name: en.brands.team.inviteTitle });
  await invite.getByRole("radio", { name: en.brands.team.methodEmail }).check();
  await invite.getByRole("textbox", { name: en.brands.team.email }).fill(managerEmail);
  await invite.getByRole("button", { name: en.brands.team.send }).click();
  await expect(invite.getByText(en.brands.team.errors.locations)).toBeVisible();
  await invite.getByRole("checkbox", { name: /Salon Morgenrot Potsdam/ }).check();
  await invite.getByRole("button", { name: en.brands.team.send }).click();
  await expect(invite).toBeHidden();
  const member = page.getByRole("listitem").filter({ hasText: managerEmail });
  await expect(member).toBeVisible();

  const managerToken = await signInByEmail(request, managerEmail);
  const asManager = { authorization: `Bearer ${managerToken}` };
  const context = await browser.newContext({ viewport: { width: 390, height: 844 }, reducedMotion: "reduce" });
  await signInContext(context, managerToken);
  const managerPage = await context.newPage();
  await managerPage.goto(`/brands/${brandId}`);
  // Berlin is the brand's, not the manager's: locked, with no link into it.
  await expect(managerPage.getByText(en.brands.overview.locked)).toBeVisible();
  await expect(managerPage.getByRole("link", { name: /Salon Morgenrot Potsdam/ })).toBeVisible();
  await expect(managerPage.getByRole("link", { name: en.brands.tabs.team })).toHaveCount(0);
  expect((await request.get(`${API_URL}/v1/businesses/${potsdamId}`, { headers: asManager })).status()).toBe(200);
  expect([403, 404]).toContain((await request.get(`${API_URL}/v1/businesses/${owner.businessId}`, { headers: asManager })).status());

  // Removed from the brand: the next request is refused.
  await member.getByRole("button", { name: en.brands.team.remove }).click();
  await page.getByRole("dialog").getByRole("button", { name: en.brands.team.remove }).click();
  await expect(member).toHaveCount(0);
  expect([403, 404]).toContain((await request.get(`${API_URL}/v1/businesses/${potsdamId}`, { headers: asManager })).status());
  await context.close();
});
