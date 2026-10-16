/**
 * The command palette with the keyboard alone: Ctrl+K opens it with the
 * focus in its text box, typing finds a customer (and their booking) and
 * a page, the arrows move the highlight and wrap, Enter opens what is
 * highlighted, Escape closes it and gives the focus back. On a phone the
 * search button in the top bar opens it.
 */

import { bookedCustomer } from "./support/customers";
import { expect, test } from "./support/fixtures";
import { en } from "./support/messages";
import { waitForNetworkQuiet } from "./support/network";

const palette = en.palette;

test.describe.configure({ timeout: 90_000 });

test("Ctrl+K finds a customer and a page with the keyboard alone", async ({ page, request, owner }) => {
  const nino = await bookedCustomer(request, owner.token, owner.businessId, { name: "Nino Beridze", phone: "+995599123456" });
  await page.goto(`/b/${owner.businessId}/overview`);
  await waitForNetworkQuiet(page);

  const dialog = page.getByRole("dialog", { name: palette.title });
  const box = dialog.getByRole("combobox", { name: palette.placeholder });
  const highlighted = dialog.locator('[role="option"][aria-selected="true"]');

  await test.step("a customer, found by name, opens with Enter", async () => {
    await page.keyboard.press("Control+k");
    await expect(dialog).toBeVisible();
    await expect(box).toBeFocused();
    await page.keyboard.type("Nino");
    await expect(dialog.getByRole("group", { name: palette.groups.customers })).toContainText("Nino Beridze");
    await expect(dialog.getByRole("group", { name: palette.groups.bookings })).toContainText("Nino Beridze");
    // The first result is highlighted and is the text box's active option.
    await expect(highlighted).toContainText("Nino Beridze");
    const activeId = await highlighted.getAttribute("id");
    await expect(box).toHaveAttribute("aria-activedescendant", activeId ?? "");
    await page.keyboard.press("Enter");
    await expect(dialog).toBeHidden();
    await expect(page).toHaveURL(new RegExp(`/customers/${nino.contactId}$`));
  });

  await test.step("a page, found by a word of its name", async () => {
    await page.keyboard.press("Control+k");
    await expect(box).toBeFocused();
    await expect(box).toHaveValue("");
    await page.keyboard.type("segm");
    await expect(highlighted).toContainText(en.navigation.pages.customersSegments);
    await page.keyboard.press("Enter");
    await expect(page).toHaveURL(new RegExp(`/b/${owner.businessId}/customers/segments$`));
  });

  await test.step("the arrows wrap and Escape closes", async () => {
    await page.keyboard.press("Control+k");
    const options = dialog.getByRole("option");
    await expect(options.first()).toHaveAttribute("aria-selected", "true");
    const count = await options.count();
    expect(count).toBeGreaterThan(2);
    await page.keyboard.press("ArrowUp");
    await expect(options.nth(count - 1)).toHaveAttribute("aria-selected", "true");
    await page.keyboard.press("ArrowDown");
    await expect(options.first()).toHaveAttribute("aria-selected", "true");
    await page.keyboard.press("ArrowDown");
    await expect(options.nth(1)).toHaveAttribute("aria-selected", "true");
    await page.keyboard.press("End");
    await expect(options.nth(count - 1)).toHaveAttribute("aria-selected", "true");
    await page.keyboard.press("Escape");
    await expect(dialog).toBeHidden();
    await expect(page).toHaveURL(new RegExp(`/b/${owner.businessId}/customers/segments$`));
  });

  await test.step("Ctrl+K closes it again", async () => {
    await page.keyboard.press("Control+k");
    await expect(dialog).toBeVisible();
    await page.keyboard.press("Control+k");
    await expect(dialog).toBeHidden();
  });
});

test.describe("on a phone", () => {
  test.use({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });

  test("the top bar's search button opens the palette", async ({ page, owner }) => {
    await page.goto(`/b/${owner.businessId}/bookings`);
    await page.getByRole("button", { name: palette.open, exact: true }).tap();
    const dialog = page.getByRole("dialog", { name: palette.title });
    await expect(dialog).toBeVisible();
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(overflow).toBeLessThanOrEqual(0);
    await page.keyboard.type("team");
    await dialog.getByRole("option", { name: new RegExp(en.navigation.pages.settingsTeam) }).tap();
    await expect(page).toHaveURL(new RegExp(`/b/${owner.businessId}/settings/team$`));
  });
});
