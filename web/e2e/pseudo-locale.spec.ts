/**
 * Long texts never break a layout. The pseudo-locale (accented English, 40 %
 * longer, in brackets: src/i18n/pseudo.ts) stands in for Russian and
 * Georgian, which run 20–40 % longer than English: every page of a business,
 * the setup invitation and tunnel, the business list and the sign-in page, on a desktop
 * and on a phone, fit the screen and keep every button, tab and link whole.
 * Its right-to-left twin (`ar-XB`) checks the same pages laid out as for
 * Hebrew: a box placed by a physical side would push the page sideways there.
 */

import type { Page } from "@playwright/test";

import { SECTION_PAGES, visibleSections } from "../src/lib/sections";

import { expect, test } from "./support/fixtures";
import { waitForNetworkQuiet } from "./support/network";
import { findOverflow, usePseudoLocale } from "./support/overflow";

const SCREENS = [
  { name: "desktop", viewport: { width: 1440, height: 900 }, isMobile: false },
  { name: "phone", viewport: { width: 390, height: 844 }, isMobile: true },
] as const;

const OWNER_PAGES: readonly string[] = visibleSections("owner").flatMap(
  (section) => SECTION_PAGES[section].map((entry) => entry.page),
);

test.describe.configure({ timeout: 180_000 });

async function expectFits(
  page: Page,
  path: string,
  direction: "ltr" | "rtl",
): Promise<void> {
  await page.goto(path);
  await expect(page.locator("html")).toHaveAttribute("dir", direction);
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await waitForNetworkQuiet(page);
  // The texts are the pseudo-locale's (not a page left in English).
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(/^\[.*\]$/);
  expect(
    await findOverflow(page),
    `${path} at ${page.viewportSize()?.width} px`,
  ).toEqual([]);
}

for (const direction of ["ltr", "rtl"] as const) {
  for (const screen of SCREENS) {
    test.describe(`long texts on a ${screen.name}, ${direction === "rtl" ? "right to left" : "left to right"}`, () => {
      test.use({
        viewport: screen.viewport,
        isMobile: screen.isMobile,
        hasTouch: screen.isMobile,
      });

      test("every page of a business fits", async ({
        page,
        context,
        owner,
      }) => {
        await usePseudoLocale(context, direction);
        for (const path of OWNER_PAGES) {
          await test.step(path, () =>
            expectFits(page, `/b/${owner.businessId}/${path}`, direction),
          );
        }
      });

      test("the setup invitation, every screen of the tunnel and the business list fit", async ({
        page,
        context,
        newOwner,
      }) => {
        await usePseudoLocale(context, direction);
        await test.step("setup", () =>
          expectFits(page, `/b/${newOwner.businessId}/overview`, direction));
        for (const step of [
          "business",
          "place",
          "offer",
          "hours",
          "people",
          "channels",
          "try",
          "launch",
        ]) {
          await test.step(`tunnel: ${step}`, () =>
            expectFits(
              page,
              `/b/${newOwner.businessId}/setup?step=${step}`,
              direction,
            ));
        }
        await test.step("create", () => expectFits(page, "/create", direction));
        await test.step("businesses", () =>
          expectFits(page, "/businesses", direction));
      });

      test("the sign-in page fits", async ({ page, context }) => {
        await usePseudoLocale(context, direction);
        await expectFits(page, "/login", direction);
      });
    });
  }
}
