/**
 * A guest's pages on a 320 px wide screen with the keyboard alone, against
 * the real API (WCAG 2.1.1 Keyboard, 1.4.10 Reflow): the demo restaurant's
 * hosted chat page (/c/{address}) fits without sideways scrolling, the
 * guest reaches the chat with Tab, books a table by typing and Enter, and
 * the booking page the confirmation links (/r/{token}) fits too.
 */

import type { Locator, Page } from "@playwright/test";

import { BOOKING_REQUESTS } from "./support/booking-page";
import { signInAsDemoOwner } from "./support/demo";
import { expect, test } from "./support/fixtures";
import { waitForNetworkQuiet } from "./support/network";
import { findOverflow } from "./support/overflow";

test.describe.configure({ timeout: 120_000 });

/** The narrowest screen WCAG 1.4.10 asks a page to fit (320 CSS px). */
const NARROW = { width: 320, height: 640 };

/** Whether `locator` has the keyboard focus (also inside the widget's shadow root). */
function isFocused(locator: Locator): Promise<boolean> {
  return locator.evaluate((element) => (element.getRootNode() as Document | ShadowRoot).activeElement === element);
}

/** Tab (at most `limit` times) until `locator` has the focus. */
async function tabTo(page: Page, locator: Locator, limit = 40): Promise<void> {
  for (let press = 0; press < limit && !(await isFocused(locator)); press += 1) {
    await page.keyboard.press("Tab");
  }
  await expect(locator).toBeFocused();
}

test("a guest books on the hosted chat page with the keyboard alone, and both pages fit 320 px", async ({ page, request }) => {
  const { businessId } = await signInAsDemoOwner(request);
  await page.setViewportSize(NARROW);

  await page.goto(`/c/${businessId}`);
  const textbox = page.getByRole("textbox");
  await expect(textbox).toBeEditable();
  await waitForNetworkQuiet(page);
  expect(await findOverflow(page), "/c/ at 320 px").toEqual([]);

  await tabTo(page, textbox);
  await page.keyboard.type(BOOKING_REQUESTS.en);
  await page.keyboard.press("Enter");
  await expect(page.getByText(/your booking is confirmed/).first()).toBeVisible({ timeout: 20_000 });
  expect(await findOverflow(page), "/c/ at 320 px with the conversation").toEqual([]);

  // The confirmation links the guest's booking page.
  const manage = page.locator('[data-assistant-workshop-chat] a[href*="/r/"]').first();
  await expect(manage).toBeVisible();
  const href = await manage.getAttribute("href");
  expect(href).toBeTruthy();
  await page.goto(href!);
  await expect(page.getByRole("heading", { level: 1, name: "Your booking" })).toBeVisible();
  await waitForNetworkQuiet(page);
  expect(await findOverflow(page), "/r/ at 320 px").toEqual([]);

  // The keyboard reaches the page's controls.
  await page.keyboard.press("Tab");
  await expect(page.locator(":focus")).toHaveCount(1);
});
