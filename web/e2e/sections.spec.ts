import { BUSINESS_SECTIONS } from "../src/lib/navigation";

import { expect, test } from "./support/fixtures";
import { en } from "./support/messages";

test.describe("every section of a business", () => {
  test("opens from the sidebar without errors", async ({ page, owner }) => {
    await page.goto(`/b/${owner.businessId}/dashboard`);
    const navigation = page.getByRole("navigation", { name: en.nav.mainNavigation });

    for (const section of BUSINESS_SECTIONS) {
      await test.step(section, async () => {
        await navigation.getByRole("link", { name: en.nav[section], exact: true }).click();
        await expect(page).toHaveURL(new RegExp(`/b/${owner.businessId}/${section}(\\?|$)`));
        await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
        await expect(navigation.getByRole("link", { name: en.nav[section], exact: true })).toHaveAttribute(
          "aria-current",
          "page",
        );
        await page.waitForLoadState("networkidle");
        // No section failed to load its data.
        await expect(page.getByRole("button", { name: en.common.retry })).toHaveCount(0);
      });
    }
  });

  test.describe("on a phone", () => {
    test.use({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });

    test("opens from the menu and fits the screen", async ({ page, owner }) => {
      await page.goto(`/b/${owner.businessId}/dashboard`);

      for (const section of BUSINESS_SECTIONS) {
        await test.step(section, async () => {
          await page.getByRole("button", { name: en.nav.openMenu }).click();
          const menu = page.getByRole("dialog", { name: en.nav.mainNavigation });
          await expect(menu).toBeVisible();
          await menu.getByRole("link", { name: en.nav[section], exact: true }).click();
          await expect(menu).toBeHidden();
          await expect(page).toHaveURL(new RegExp(`/b/${owner.businessId}/${section}(\\?|$)`));
          await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
          await page.waitForLoadState("networkidle");
          // Nothing makes the page wider than the phone.
          const overflow = await page.evaluate(
            () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
          );
          expect(overflow, `${section} scrolls sideways`).toBeLessThanOrEqual(0);
        });
      }
    });
  });
});
