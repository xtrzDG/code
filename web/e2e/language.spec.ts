import { expect, test } from "./support/fixtures";
import { en, ka, ru } from "./support/messages";

test("switches the interface language and keeps it", async ({ page, owner }) => {
  await page.goto(`/b/${owner.businessId}/dashboard`);
  const languageSelect = (label: string) => page.getByRole("combobox", { name: label });
  const navigation = page.getByRole("navigation", { name: en.nav.mainNavigation });

  await expect(page.locator("html")).toHaveAttribute("lang", "en");
  await expect(navigation.getByRole("link", { name: en.nav.bookings, exact: true })).toBeVisible();

  await languageSelect(en.language.label).selectOption("ru");
  await expect(page.locator("html")).toHaveAttribute("lang", "ru");
  await expect(
    page.getByRole("navigation", { name: ru.nav.mainNavigation }).getByRole("link", { name: ru.nav.bookings, exact: true }),
  ).toBeVisible();

  await languageSelect(ru.language.label).selectOption("ka");
  await expect(page.locator("html")).toHaveAttribute("lang", "ka");
  const georgianNavigation = page.getByRole("navigation", { name: ka.nav.mainNavigation });
  await expect(georgianNavigation.getByRole("link", { name: ka.nav.bookings, exact: true })).toBeVisible();

  // The choice is stored (cookie and account) and survives a reload.
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("lang", "ka");
  await georgianNavigation.getByRole("link", { name: ka.nav.settings, exact: true }).click();
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();

  await languageSelect(ka.language.label).selectOption("en");
  await expect(page.locator("html")).toHaveAttribute("lang", "en");
  await expect(navigation.getByRole("link", { name: en.nav.settings, exact: true })).toHaveAttribute("aria-current", "page");
});
