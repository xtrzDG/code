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

async function openNewBooking(page: Page, businessId: string, texts: typeof en) {
  await page.goto(`/b/${businessId}/bookings`);
  await waitForNetworkQuiet(page);
  await page.getByRole("button", { name: texts.bookings.newBooking }).first().click();
  return page.getByRole("dialog", { name: texts.bookings.form.title });
}

async function expectInsideWindow(page: Page, dialog: ReturnType<Page["getByRole"]>, submitName: string) {
  const height = page.viewportSize()?.height ?? 0;
  const box = await dialog.boundingBox();
  expect(box, "the dialog is on screen").not.toBeNull();
  expect((box?.y ?? 0) + (box?.height ?? 0)).toBeLessThanOrEqual(height);
  const submit = dialog.getByRole("button", { name: submitName });
  await expect(submit).toBeInViewport({ ratio: 1 });
  const footer = dialog.locator("[data-modal-footer]");
  const footerBox = await footer.boundingBox();
  // The actions sit at the dialog's bottom edge, not somewhere below the fold of its body.
  expect(Math.abs((footerBox?.y ?? 0) + (footerBox?.height ?? 0) - ((box?.y ?? 0) + (box?.height ?? 0)))).toBeLessThanOrEqual(2);
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
