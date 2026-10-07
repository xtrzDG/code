/**
 * The new-booking dialog fits the screen: on a laptop 900 px tall the
 * dialog stays inside the window, its body scrolls and "Book" stays in
 * sight at the bottom (the form's actions stick to the dialog's edge), in
 * every interface language; the same on a phone.
 */

import type { Page } from "@playwright/test";

import { WEB_URL } from "./support/env";
import { expect, test } from "./support/fixtures";
import { en, ka, ru } from "./support/messages";
import { waitForNetworkQuiet } from "./support/network";

const DICTIONARIES = { en, ru, ka } as const;

type Texts = (typeof DICTIONARIES)[keyof typeof DICTIONARIES];

async function openNewBooking(page: Page, businessId: string, texts: Texts) {
  await page.goto(`/b/${businessId}/bookings`);
  await waitForNetworkQuiet(page);
  await page.getByRole("button", { name: texts.bookings.newBooking }).first().click();
  const dialog = page.getByRole("dialog", { name: texts.bookings.form.title });
  await expect(dialog).toBeVisible();
  // The form loads its places and services after it opens and grows with them.
  await waitForNetworkQuiet(page);
  return dialog;
}

async function expectInsideWindow(page: Page, dialog: ReturnType<Page["getByRole"]>, submitName: string) {
  const height = page.viewportSize()?.height ?? 0;
  const submit = dialog.getByRole("button", { name: submitName });
  await expect(submit).toBeInViewport({ ratio: 1 });
  // Both edges in one measurement, so content arriving in between cannot skew them.
  const edges = await dialog.evaluate((element) => ({
    dialogBottom: element.getBoundingClientRect().bottom,
    footerBottom: element.querySelector("[data-modal-footer]")?.getBoundingClientRect().bottom ?? Number.NaN,
  }));
  expect(edges.dialogBottom, "the dialog ends inside the window").toBeLessThanOrEqual(height);
  // The actions sit at the dialog's bottom edge, not somewhere below the fold of its body.
  expect(Math.abs(edges.footerBottom - edges.dialogBottom)).toBeLessThanOrEqual(2);
}

for (const [locale, texts] of Object.entries(DICTIONARIES)) {
  test(`the new booking's actions are in sight on a 900 px tall screen (${locale})`, async ({ page, owner }) => {
    await page.context().addCookies([{ name: "aw_locale", value: locale, url: WEB_URL }]);
    await page.setViewportSize({ width: 1440, height: 900 });
    const dialog = await openNewBooking(page, owner.businessId, texts);
    await expectInsideWindow(page, dialog, texts.bookings.form.submit);
  });
}

test.describe("on a phone", () => {
  test.use({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });

  test("the new booking's actions stay in sight while the form scrolls", async ({ page, owner }) => {
    const dialog = await openNewBooking(page, owner.businessId, en);
    await expectInsideWindow(page, dialog, en.bookings.form.submit);
    await dialog.locator("[data-modal-body]").evaluate((body) => body.scrollTo({ top: body.scrollHeight }));
    await expect(dialog.getByRole("button", { name: en.bookings.form.submit })).toBeInViewport({ ratio: 1 });
  });
});
