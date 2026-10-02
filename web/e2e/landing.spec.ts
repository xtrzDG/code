import { expect, test } from "./support/fixtures";
import { en, ru } from "./support/messages";

test.describe("the public landing page", () => {
  test("shows the product and the prices of a chosen country", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { level: 1, name: en.landing.hero.title })).toBeVisible();
    // Dark is the default theme, rendered by the server.
    await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");

    const pricing = page.locator("#pricing");
    await pricing.getByLabel(en.landing.pricing.country).selectOption("GE");
    await expect(page).toHaveURL(/[?&]country=GE\b/);
    // Georgia pays in lari; the plan's own price in euros is beside it.
    await expect(pricing.getByText(/GEL|₾/).first()).toBeVisible();
    await expect(pricing.getByText(en.landing.pricing.inEuros.replace("{price}", "")).first()).toBeVisible();

    await page.getByRole("link", { name: en.landing.hero.primary }).first().click();
    await expect(page).toHaveURL(/\/login$/);
  });

  test("keeps the theme and the language the visitor picks", async ({ page }) => {
    await page.goto("/");
    const themes = page.getByRole("group", { name: en.theme.label });
    // Each theme is an icon in a label with the theme's name as its tooltip.
    await themes.getByTitle(en.theme.light).click();
    await expect(themes.getByRole("radio", { name: en.theme.light })).toBeChecked();
    await expect(page.locator("html")).toHaveAttribute("data-theme", "light");

    await page.getByRole("combobox", { name: en.language.label }).selectOption("ru");
    await expect(page.locator("html")).toHaveAttribute("lang", "ru");
    await expect(page.getByRole("heading", { level: 1, name: ru.landing.hero.title })).toBeVisible();

    // Both choices are cookies, so the server renders them after a reload.
    await page.reload();
    await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
    await expect(page.locator("html")).toHaveAttribute("lang", "ru");
    await page.getByRole("group", { name: ru.theme.label }).getByTitle(ru.theme.system).click();
    await expect(page.locator("html")).toHaveAttribute("data-theme", "system");
  });

  test("sends a signed-in user to their businesses", async ({ page, account }) => {
    expect(account.token).toBeTruthy();
    await page.goto("/");
    await expect(page).toHaveURL(/\/businesses$/);
  });
});
