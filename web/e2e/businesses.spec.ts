import { expect, test } from "./support/fixtures";
import { en } from "./support/messages";

test("creates a business in another country with its languages", async ({ page, account }) => {
  expect(account.token).toBeTruthy();
  await page.goto("/businesses");
  await expect(page.getByText(en.businesses.emptyTitle)).toBeVisible();
  // A new account gets the form at once; closed, it opens from the empty state.
  const dialog = page.getByRole("dialog", { name: en.businesses.createTitle });
  await expect(dialog).toBeVisible();
  await dialog.getByRole("button", { name: en.common.close }).click();
  await expect(dialog).toBeHidden();
  await page.getByRole("button", { name: en.businesses.create }).click();
  await expect(dialog).toBeVisible();
  await dialog.getByLabel(en.businesses.name).fill("Kuaför Güneş");
  await dialog.getByLabel(en.businesses.niche).selectOption("beauty_salon");
  await dialog.getByLabel(en.businesses.country).selectOption("TR");

  // Turkey's defaults: Turkish and English, lira, Istanbul time.
  const languages = dialog.getByRole("group", { name: en.businesses.languages });
  await expect(languages.getByRole("checkbox", { name: /Türkçe/ })).toBeChecked();
  await expect(languages.getByRole("checkbox", { name: /English/ })).toBeChecked();
  await expect(dialog.getByText("Europe/Istanbul", { exact: false })).toBeVisible();
  // Arabic is offered on request (and is written right to left).
  await languages.getByRole("checkbox", { name: /Arabic|العربية/ }).check();
  await dialog.getByLabel(en.businesses.defaultLanguage).selectOption("tr");
  await dialog.getByLabel(en.businesses.city).fill("İzmir");
  await dialog.getByRole("button", { name: en.businesses.submit }).click();

  await expect(dialog.getByText(en.businesses.createdTitle)).toBeVisible();
  await dialog.getByRole("link", { name: en.businesses.continueToProfile }).click();

  await expect(page).toHaveURL(/\/b\/[^/]+\/onboarding$/);
  await expect(page.getByRole("heading", { level: 1, name: en.onboarding.title })).toBeVisible();
  // The first step lists the customer languages, the default one starred.
  await expect(page.locator('[lang="tr"]').filter({ hasText: "★" })).toBeVisible();
  await expect(page.locator('[lang="ar"]')).toBeVisible();

  // The business is in the switcher's list too.
  await page.goto("/businesses");
  await expect(page.getByRole("heading", { name: "Kuaför Güneş" })).toBeVisible();
});

test("shows a failed save above the open form and keeps the form", async ({ page, account, consoleErrors }) => {
  expect(account.token).toBeTruthy();
  consoleErrors.allow(/Failed to load resource: the server responded with a status of 503/);
  await page.route("**/api/backend/v1/businesses", (route) =>
    route.request().method() === "POST"
      ? route.fulfill({
          status: 503,
          contentType: "application/json",
          body: JSON.stringify({ error: "backend_unavailable", message: "Maintenance" }),
        })
      : route.fallback(),
  );
  await page.goto("/businesses");
  const dialog = page.getByRole("dialog", { name: en.businesses.createTitle });
  await dialog.getByLabel(en.businesses.name).fill("Panadería Sol");
  await dialog.getByLabel(en.businesses.niche).selectOption("restaurant");
  await dialog.getByLabel(en.businesses.country).selectOption("ES");
  await dialog.getByRole("button", { name: en.businesses.submit }).click();

  // The toast is drawn inside the modal dialog (the page behind it is inert)
  // and can be dismissed; the form keeps what was typed.
  const toast = dialog.getByRole("alert").filter({ hasText: en.errors.codes.backend_unavailable });
  await expect(toast).toBeVisible();
  await toast.getByRole("button", { name: en.common.close }).click();
  await expect(toast).toBeHidden();
  await expect(dialog.getByLabel(en.businesses.name)).toHaveValue("Panadería Sol");
});
