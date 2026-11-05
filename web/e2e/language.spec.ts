import type { Page } from "@playwright/test";

import { expect, test } from "./support/fixtures";
import { en, it } from "./support/messages";

/** The user menu at the bottom of the sidebar holds the language. */
async function chooseLanguage(
  page: Page,
  menuLabel: string,
  languageLabel: string,
  locale: string,
): Promise<void> {
  await page.getByRole("button", { name: menuLabel }).click();
  await page
    .getByRole("combobox", { name: languageLabel })
    .selectOption(locale);
  await expect(page.locator("html")).toHaveAttribute("lang", locale);
}

test("switches the interface language from the user menu and keeps it", async ({
  page,
  owner,
}) => {
  await page.goto(`/b/${owner.businessId}/overview`);
  const navigation = page.getByRole("navigation", {
    name: en.nav.mainNavigation,
  });

  await expect(page.locator("html")).toHaveAttribute("lang", "en");
  await expect(page.locator("html")).toHaveAttribute("dir", "ltr");
  await expect(
    navigation.getByRole("link", {
      name: en.navigation.sections.bookings,
      exact: true,
    }),
  ).toBeVisible();

  await chooseLanguage(page, en.account.menu, en.language.label, "it");
  const italianNavigation = page.getByRole("navigation", {
    name: it.nav.mainNavigation,
  });
  await expect(
    italianNavigation.getByRole("link", {
      name: it.navigation.sections.bookings,
      exact: true,
    }),
  ).toBeVisible();
  // Every cabinet language reads left to right.
  await expect(page.locator("html")).toHaveAttribute("dir", "ltr");

  // The choice is stored (cookie and account) and survives a reload.
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("lang", "it");
  await italianNavigation
    .getByRole("link", { name: it.navigation.sections.settings, exact: true })
    .click();
  await expect(
    page.getByRole("heading", {
      level: 1,
      name: it.navigation.sections.settings,
    }),
  ).toBeVisible();

  await chooseLanguage(page, it.account.menu, it.language.label, "en");
  await expect(
    navigation.getByRole("link", {
      name: en.navigation.sections.settings,
      exact: true,
    }),
  ).toHaveAttribute("aria-current", "page");
});
