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

test("a notification contact saved after the list changed elsewhere is refused and the list reloads", async ({
  page,
  owner,
  request,
  consoleErrors,
}) => {
  consoleErrors.allow(/status of 409/);
  await page.goto(`/b/${owner.businessId}/settings#notifications`);
  await expect(page.getByText(en.settings.contacts.empty)).toBeVisible();

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
