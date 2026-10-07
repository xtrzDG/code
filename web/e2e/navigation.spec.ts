/**
 * The six sections: every section and page opens from the sidebar (the
 * open section's pages under it) and on a phone from the tab bar and
 * "More", fits the screen, and the sidebar folds to icons and stays so.
 * The tab bar's names keep their words whole in every cabinet language.
 */

import type { Page } from "@playwright/test";

import { SECTION_PAGES, visibleSections, type BusinessSection } from "../src/lib/sections";

import { WEB_URL } from "./support/env";
import { expect, test } from "./support/fixtures";
import { de, en, he, ka, ru } from "./support/messages";
import { waitForNetworkQuiet } from "./support/network";

type MessagePath = string;

/** The English text of a dictionary key ("navigation.pages.settingsTeam"). */
function text(key: MessagePath): string {
  return key.split(".").reduce<unknown>((node, part) => (node as Record<string, unknown>)[part], en) as string;
}

async function expectPageOpened(page: Page, businessId: string, path: string): Promise<void> {
  await expect(page).toHaveURL(new RegExp(`/b/${businessId}/${path}(\\?|$)`));
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await waitForNetworkQuiet(page);
  // No page failed to load its data.
  await expect(page.getByRole("button", { name: en.common.retry })).toHaveCount(0);
}

test.describe("every section of a business", () => {
  test("opens from the sidebar, with the open section's pages under it", async ({ page, owner }) => {
    await page.goto(`/b/${owner.businessId}/overview`);
    const navigation = page.getByRole("navigation", { name: en.nav.mainNavigation });

    for (const section of visibleSections("owner")) {
      await test.step(section, async () => {
        const sectionLink = navigation.getByRole("link", { name: text(`navigation.sections.${section}`), exact: true });
        await sectionLink.click();
        await expectPageOpened(page, owner.businessId, section);
        await expect(sectionLink).toHaveAttribute("aria-current", "page");

        for (const entry of SECTION_PAGES[section].slice(1)) {
          if (entry.isAdvanced) {
            await navigation.getByRole("button", { name: en.navigation.advanced }).click();
          }
          await navigation.getByRole("link", { name: text(entry.label), exact: true }).click();
          await expectPageOpened(page, owner.businessId, entry.page);
          await expect(navigation.getByRole("link", { name: text(entry.label), exact: true })).toHaveAttribute("aria-current", "page");
          // The section's own tabs mark the same page.
          const tabs = page.getByRole("navigation", { name: new RegExp(text(`navigation.sections.${section}`)) });
          await expect(tabs.locator('[aria-current="page"]')).toHaveCount(1);
        }
      });
    }
  });

  test("folds the sidebar to icons and keeps it folded", async ({ page, owner }) => {
    await page.goto(`/b/${owner.businessId}/bookings`);
    await page.getByRole("button", { name: en.navigation.collapse }).click();
    const navigation = page.getByRole("navigation", { name: en.nav.mainNavigation });
    // Folded, every section keeps its name for screen readers.
    await expect(navigation.getByRole("link", { name: en.navigation.sections.bookings, exact: true })).toHaveAttribute(
      "aria-current",
      "page",
    );
    await page.reload();
    await expect(page.getByRole("button", { name: en.navigation.expand })).toBeVisible();
    await page.getByRole("button", { name: en.navigation.expand }).click();
    await expect(page.getByRole("button", { name: en.navigation.collapse })).toBeVisible();
  });

  test("the user menu holds the theme, all businesses and signing out", async ({ page, owner }) => {
    await page.goto(`/b/${owner.businessId}/overview`);
    await page.getByRole("button", { name: en.account.menu }).click();
    const menu = page.getByRole("dialog", { name: en.account.menu });
    await menu.getByRole("radio", { name: en.theme.light }).check({ force: true });
    await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
    await expect(menu.getByRole("link", { name: en.account.businesses })).toBeVisible();
    await expect(menu.getByRole("button", { name: en.shell.signOut })).toBeVisible();
  });
});

test.describe("on a phone", () => {
  test.use({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });

  const fits = async (page: Page, where: string) => {
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(overflow, `${where} scrolls sideways`).toBeLessThanOrEqual(0);
  };

  test("the tab bar opens four sections and More the rest", async ({ page, owner }) => {
    await page.goto(`/b/${owner.businessId}/overview`);
    const tabBar = page.getByRole("navigation", { name: en.navigation.tabBar });
    const inTabBar: BusinessSection[] = ["overview", "inbox", "bookings", "assistant"];

    for (const section of inTabBar) {
      await test.step(section, async () => {
        const place = tabBar.getByRole("link", { name: text(`navigation.sections.${section}`), exact: true });
        await place.click();
        await expectPageOpened(page, owner.businessId, section);
        await expect(place).toHaveAttribute("aria-current", "page");
        // Every place is big enough for a thumb.
        expect((await place.boundingBox())?.height ?? 0).toBeGreaterThanOrEqual(44);
        await fits(page, section);
      });
    }

    for (const entry of [...SECTION_PAGES.customers, ...SECTION_PAGES.settings]) {
      await test.step(entry.page, async () => {
        await tabBar.getByRole("button", { name: en.navigation.more }).click();
        const sheet = page.getByRole("dialog", { name: en.navigation.more });
        await expect(sheet).toBeVisible();
        await sheet.getByRole("link", { name: text(entry.label), exact: true }).click();
        await expect(sheet).toBeHidden();
        await expectPageOpened(page, owner.businessId, entry.page);
        await fits(page, entry.page);
      });
    }
  });

  test("the tab bar's names keep their words whole in every language", async ({ page, context, owner }) => {
    const languages = { en, ru, ka, he, de };
    for (const [locale, messages] of Object.entries(languages)) {
      await test.step(locale, async () => {
        await context.addCookies([{ name: "aw_locale", value: locale, url: WEB_URL, sameSite: "Lax" }]);
        await page.goto(`/b/${owner.businessId}/overview`);
        const tabBar = page.getByRole("navigation", { name: messages.navigation.tabBar });
        await expect(tabBar.locator("[data-tab-label]")).toHaveCount(5);
        // A word on two lines ("Posteingan|g") or cut with "…" is a problem; two words on two lines are not.
        const problems = await tabBar.evaluate((nav) =>
          [...nav.querySelectorAll<HTMLElement>("[data-tab-label]")].flatMap((label) => {
            const text = label.textContent ?? "";
            const found: string[] = [];
            if (label.scrollWidth > label.clientWidth + 1 || label.scrollHeight > label.clientHeight + 1) {
              found.push(`“${text}” is cut`);
            }
            const node = label.firstChild;
            let start = 0;
            for (const word of text.split(" ")) {
              if (node) {
                const range = document.createRange();
                range.setStart(node, start);
                range.setEnd(node, start + word.length);
                const lines = new Set([...range.getClientRects()].filter((rect) => rect.width > 0).map((rect) => Math.round(rect.top)));
                if (lines.size > 1) found.push(`“${word}” breaks inside`);
              }
              start += word.length + 1;
            }
            return found;
          }),
        );
        expect(problems, `the tab bar in ${locale}`).toEqual([]);
      });
    }
  });

  test("More holds the business switcher and the account", async ({ page, owner }) => {
    await page.goto(`/b/${owner.businessId}/bookings`);
    await page.getByRole("button", { name: en.navigation.more }).click();
    const sheet = page.getByRole("dialog", { name: en.navigation.more });
    await expect(sheet.getByRole("button", { name: new RegExp(en.shell.switchBusiness) })).toBeVisible();
    await expect(sheet.getByRole("combobox", { name: en.language.label })).toBeVisible();
    await expect(sheet.getByRole("group", { name: en.theme.label })).toBeVisible();
    await expect(sheet.getByRole("button", { name: en.shell.signOut })).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(sheet).toBeHidden();
  });
});
