/**
 * Business settings saved by two people at once: a save made from an older
 * revision is refused by the API, and the Settings tabs reload and say so
 * instead of overwriting the newer save.
 */

import type { APIRequestContext } from "@playwright/test";

import { API_URL } from "./support/env";
import { expect, test, type Owner } from "./support/fixtures";
import { en } from "./support/messages";

/** Another owner (or the platform's Telegram bot) saves the business meanwhile. */
async function saveElsewhere(request: APIRequestContext, owner: Owner, changes: Record<string, unknown>): Promise<void> {
  const response = await request.patch(`${API_URL}/v1/businesses/${owner.businessId}`, {
    data: changes,
    headers: { authorization: `Bearer ${owner.token}` },
  });
  expect(response.status(), await response.text()).toBe(200);
}

test("a general settings save after someone else's is refused, reloaded and explained", async ({
  page,
  owner,
  request,
  consoleErrors,
}) => {
  consoleErrors.allow(/status of 409/);
  await page.goto(`/b/${owner.businessId}/settings`);
  const city = page.getByRole("textbox", { name: new RegExp(`^${en.settings.general.city}`) });
  await expect(city).toHaveValue("Berlin");

  await city.fill("Potsdam");
  await saveElsewhere(request, owner, { city: "Hamburg" });
  await page.getByRole("button", { name: en.settings.general.save }).click();

  await expect(page.getByText(en.settings.general.staleDescription)).toBeVisible();
  await expect(city).toHaveValue("Hamburg");

  await city.fill("Potsdam");
  await page.getByRole("button", { name: en.settings.general.save }).click();
  await expect(page.getByText(en.settings.general.saved)).toBeVisible();
  await expect(page.getByText(en.settings.general.staleDescription)).toBeHidden();
  await page.reload();
  await expect(city).toHaveValue("Potsdam");
});

test("general settings opened after a save made elsewhere earlier still save", async ({ page, owner, request }) => {
  await page.goto(`/b/${owner.businessId}/overview`);
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  // The platform bot adds a manager: no field of the General form changes,
  // the revision does; the layout keeps the business it loaded.
  await saveElsewhere(request, owner, { manager_contacts: [{ name: "Levan", channel: "telegram", address: "777000111" }] });
  await page
    .getByRole("navigation", { name: en.nav.mainNavigation })
    .getByRole("link", { name: en.navigation.sections.settings, exact: true })
    .click();
  const city = page.getByRole("textbox", { name: new RegExp(`^${en.settings.general.city}`) });
  await expect(city).toHaveValue("Berlin");

  await city.fill("Potsdam");
  await page.getByRole("button", { name: en.settings.general.save }).click();

  await expect(page.getByText(en.settings.general.saved)).toBeVisible();
  await expect(page.getByText(en.settings.general.staleDescription)).toBeHidden();
  await expect(city).toHaveValue("Potsdam");
});

test("a general settings save after an unrelated save elsewhere keeps what was typed", async ({
  page,
  owner,
  request,
  consoleErrors,
}) => {
  consoleErrors.allow(/status of 409/);
  await page.goto(`/b/${owner.businessId}/settings`);
  const name = page.getByRole("textbox", { name: new RegExp(`^${en.settings.general.name}`) });
  const city = page.getByRole("textbox", { name: new RegExp(`^${en.settings.general.city}`) });
  await expect(city).toHaveValue("Berlin");

  await name.fill("Renamed Bistro");
  await city.fill("Potsdam");
  await saveElsewhere(request, owner, { manager_contacts: [{ name: "Levan", channel: "telegram", address: "777000111" }] });
  await page.getByRole("button", { name: en.settings.general.save }).click();

  // Nobody else changed these fields: they are saved on top of the newer
  // business, which keeps its new contact.
  await expect(page.getByText(en.settings.general.saved)).toBeVisible();
  await expect(page.getByText(en.settings.general.staleDescription)).toBeHidden();
  await page.reload();
  await expect(name).toHaveValue("Renamed Bistro");
  await expect(city).toHaveValue("Potsdam");
  const stored = await request.get(`${API_URL}/v1/businesses/${owner.businessId}`, {
    headers: { authorization: `Bearer ${owner.token}` },
  });
  const business = (await stored.json()) as { manager_contacts: { name: string }[] };
  expect(business.manager_contacts.map((contact) => contact.name)).toEqual(["Levan"]);
});

test("a stale save whose reload fails does not claim the current settings are shown", async ({
  page,
  owner,
  request,
  consoleErrors,
}) => {
  consoleErrors.allow(/status of (409|503)/);
  await page.goto(`/b/${owner.businessId}/settings`);
  const city = page.getByRole("textbox", { name: new RegExp(`^${en.settings.general.city}`) });
  await expect(city).toHaveValue("Berlin");

  await city.fill("Potsdam");
  await saveElsewhere(request, owner, { city: "Hamburg" });
  // The reload after the refused save fails once (the save itself and later
  // reloads reach the API).
  let failedReloads = 0;
  await page.route(`**/api/backend/v1/businesses/${owner.businessId}`, (route) => {
    if (route.request().method() !== "GET" || failedReloads > 0) {
      return route.fallback();
    }
    failedReloads += 1;
    return route.fulfill({ status: 503, json: { error: "external_service_error", message: "Try later." } });
  });
  await page.getByRole("button", { name: en.settings.general.save }).click();

  await expect(page.getByText(en.settings.general.staleReloadFailed)).toBeVisible();
  await expect(page.getByText(en.settings.general.staleDescription)).toBeHidden();
  await expect(city).toHaveValue("Potsdam");

  await page.getByRole("button", { name: en.settings.general.staleReload }).click();
  await expect(page.getByText(en.settings.general.staleDescription)).toBeVisible();
  await expect(page.getByText(en.settings.general.staleReloadFailed)).toBeHidden();
  // The city was changed on both sides: it shows the stored value.
  await expect(city).toHaveValue("Hamburg");
});

test("a notification contact saved after the list changed elsewhere is refused and the list reloads", async ({
  page,
  owner,
  request,
  consoleErrors,
}) => {
  consoleErrors.allow(/status of 409/);
  // The list is drawn by the server at once; the save starts from the copy the browser loads.
  const loaded = page.waitForResponse(
    (response) =>
      response.request().method() === "GET" &&
      new URL(response.url()).pathname === `/api/backend/v1/businesses/${owner.businessId}`,
  );
  await page.goto(`/b/${owner.businessId}/settings/notifications`);
  await expect(page.getByRole("heading", { name: en.settings.contacts.empty })).toBeVisible();
  await loaded;

  await saveElsewhere(request, owner, {
    manager_contacts: [{ name: "Levan", channel: "telegram", address: "777000111" }],
  });
  await page.getByRole("button", { name: en.settings.contacts.add }).click();
  const dialog = page.getByRole("dialog", { name: en.settings.contacts.addTitle });
  await dialog.getByRole("textbox", { name: en.settings.contacts.name }).fill("Anna");
  await dialog.getByRole("textbox", { name: en.settings.contacts.address.email }).fill("anna@example.com");
  await dialog.getByRole("button", { name: en.common.save }).click();

  // The dialog keeps what was typed; the list behind it shows the new contact.
  await expect(dialog.getByText(en.settings.contacts.stale)).toBeVisible();
  await expect(page.getByText("777000111")).toBeVisible();
  await expect(dialog.getByRole("textbox", { name: en.settings.contacts.name })).toHaveValue("Anna");

  await dialog.getByRole("button", { name: en.common.save }).click();
  await expect(dialog).toBeHidden();
  await expect(page.getByText("anna@example.com")).toBeVisible();
  await expect(page.getByText("777000111")).toBeVisible();
});
