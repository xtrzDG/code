import type { Page } from "@playwright/test";

import { expect, test } from "./support/fixtures";
import { en, ka, ru } from "./support/messages";

/** The user menu at the bottom of the sidebar holds the language. */
async function chooseLanguage(page: Page, menuLabel: string, languageLabel: string, locale: string): Promise<void> {
  await page.getByRole("button", { name: menuLabel }).click();
  await page.getByRole("combobox", { name: languageLabel }).selectOption(locale);
  await expect(page.locator("html")).toHaveAttribute("lang", locale);
}

test("switches the interface language from the user menu and keeps it", async ({ page, owner }) => {
  await page.goto(`/b/${owner.businessId}/overview`);
  const navigation = page.getByRole("navigation", { name: en.nav.mainNavigation });

  await expect(page.locator("html")).toHaveAttribute("lang", "en");
  await expect(navigation.getByRole("link", { name: en.navigation.sections.bookings, exact: true })).toBeVisible();

  await chooseLanguage(page, en.account.menu, en.language.label, "ru");
  await expect(
    page.getByRole("navigation", { name: ru.nav.mainNavigation }).getByRole("link", { name: ru.navigation.sections.bookings, exact: true }),
  ).toBeVisible();

  await page.keyboard.press("Escape");
  await chooseLanguage(page, ru.account.menu, ru.language.label, "ka");
  const georgianNavigation = page.getByRole("navigation", { name: ka.nav.mainNavigation });
  await expect(georgianNavigation.getByRole("link", { name: ka.navigation.sections.bookings, exact: true })).toBeVisible();

  // The choice is stored (cookie and account) and survives a reload.
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("lang", "ka");
  await georgianNavigation.getByRole("link", { name: ka.navigation.sections.settings, exact: true }).click();
  await expect(page.getByRole("heading", { level: 1, name: ka.navigation.sections.settings })).toBeVisible();

  await chooseLanguage(page, ka.account.menu, ka.language.label, "en");
  await expect(navigation.getByRole("link", { name: en.navigation.sections.settings, exact: true })).toHaveAttribute("aria-current", "page");
});
