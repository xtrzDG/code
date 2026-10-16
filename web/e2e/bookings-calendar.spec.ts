/**
 * Bookings → Day, Week, Nights against the real API:
 *
 *  - a booking dragged to another master's column an hour later moves
 *    there (the API agrees), the calendar offers the message about the new
 *    time for the customer, and Undo in the toast puts it back;
 *  - the keyboard moves a focused booking a quarter of an hour per arrow
 *    and to the next place, Enter moves it, Escape cancels a preview, and
 *    the offered message opens as the list's reschedule shows it;
 *  - a drag near the grid's edge scrolls the grid, with the mouse down the
 *    day and with a finger sideways on a phone;
 *  - a guest house sees its rooms by night with the stays as bars, moves a
 *    stay to another room a night later with the keys, and the week's
 *    heatmap opens a day of nights;
 *  - the three views pass the accessibility audit, and the day fits a phone.
 */

import AxeBuilder from "@axe-core/playwright";
import type { Page } from "@playwright/test";

import { createAssistant, createBusiness } from "./support/api";
import { addPlace, berlinDate, bookByHand, bookingNow } from "./support/calendar";
import { expect, test } from "./support/fixtures";
import { en } from "./support/messages";

test.describe.configure({ timeout: 120_000 });

const calendar = en.bookingCalendar;
const ONE_HOUR = 56;

/** The calendar's offer to tell the customer the new time. */
const offerFor = (page: Page, name: string) => page.getByText(calendar.move.tell.title.replace("{name}", name));

async function seriousViolations(page: Page): Promise<string[]> {
  const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
  return results.violations
    .filter((violation) => violation.impact === "serious" || violation.impact === "critical")
    .map((violation) => `${violation.id}: ${violation.nodes.map((node) => node.target.join(" ")).join(" | ")}`);
}

test("a booking dragged to another master moves there, and Undo puts it back", async ({ page, request, owner }) => {
  const day = berlinDate(1);
  const nino = await addPlace(request, owner, { name: "Nino" });
  const lena = await addPlace(request, owner, { name: "Lena" });
  const booking = await bookByHand(request, owner, { name: "Anna Schmidt", date: day, time: "10:00", resourceId: nino });
  const where = async () => {
    const now = await bookingNow(request, owner, booking.id, day);
    return [now?.resource_id, now?.time];
  };

  await page.goto(`/b/${owner.businessId}/bookings?view=day&date=${day}`);
  await expect(page.getByRole("radio", { name: calendar.views.day, exact: true })).toBeChecked();
  const block = page.getByRole("button", { name: /^Anna Schmidt, / });
  await expect(block).toBeVisible();
  expect(await seriousViolations(page), "the day").toEqual([]);

  const from = await block.boundingBox();
  const lenaColumn = page.locator(`[data-calendar-column="${lena}"]`);
  const target = await lenaColumn.boundingBox();
  if (!from || !target) throw new Error("The grid is not laid out.");
  // Grab the block near its top, drop it an hour lower on Lena's column.
  await page.mouse.move(from.x + from.width / 2, from.y + 10);
  await page.mouse.down();
  await page.mouse.move(from.x + from.width / 2, from.y + 30, { steps: 4 });
  await page.mouse.move(target.x + target.width / 2, from.y + 10 + ONE_HOUR, { steps: 8 });
  await expect(lenaColumn.locator("[data-calendar-ghost]")).toBeVisible();
  await page.mouse.up();

  const toast = page.getByRole("status").filter({ hasText: "Moved to Lena" });
  await expect(toast).toBeVisible();
  await expect(lenaColumn.getByRole("button", { name: /^Anna Schmidt, 11:00/ })).toBeVisible();
  await expect.poll(where).toEqual([lena, "11:00"]);
  await expect(offerFor(page, "Anna Schmidt")).toBeVisible();

  await toast.getByRole("button", { name: en.common.undo }).click();
  await expect(page.getByText(calendar.move.undone)).toBeVisible();
  // Back where the customer knows it: nothing to tell them.
  await expect(offerFor(page, "Anna Schmidt")).toBeHidden();
  await expect(page.locator(`[data-calendar-column="${nino}"]`).getByRole("button", { name: /^Anna Schmidt, 10:00/ })).toBeVisible();
  await expect.poll(where).toEqual([nino, "10:00"]);
});

test("the keyboard moves a booking a quarter of an hour at a time and to the next place", async ({ page, request, owner }) => {
  const day = berlinDate(2);
  const nino = await addPlace(request, owner, { name: "Nino" });
  const lena = await addPlace(request, owner, { name: "Lena" });
  const booking = await bookByHand(request, owner, { name: "Lukas Weber", date: day, time: "12:00", resourceId: nino });

  await page.goto(`/b/${owner.businessId}/bookings?view=day&date=${day}`);
  const block = page.getByRole("button", { name: /^Lukas Weber, / });
  await block.focus();
  const announcement = page.locator('[role="status"][aria-live="polite"]').filter({ hasText: /Enter/ });

  // A preview that Escape drops.
  await page.keyboard.press("ArrowDown");
  await expect(page.locator(`[data-calendar-column="${nino}"] [data-calendar-ghost]`)).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.locator("[data-calendar-ghost]")).toHaveCount(0);

  for (let step = 0; step < 4; step += 1) {
    await page.keyboard.press("ArrowDown");
  }
  await page.keyboard.press("ArrowRight");
  await expect(announcement).toHaveText(calendar.move.pending.replace("{place}", "Lena").replace("{time}", "1:00 PM"));
  await expect(page.locator(`[data-calendar-column="${lena}"] [data-calendar-ghost]`)).toBeVisible();
  await page.keyboard.press("Enter");

  await expect(page.getByRole("status").filter({ hasText: "Moved to Lena" })).toBeVisible();
  await expect(page.locator(`[data-calendar-column="${lena}"]`).getByRole("button", { name: /^Lukas Weber, 1:00/ })).toBeFocused();
  await expect.poll(async () => (await bookingNow(request, owner, booking.id, day))?.time).toBe("13:00");

  // The same message the list's reschedule form shows, from the offer above the grid.
  await page.getByRole("button", { name: calendar.move.tell.show }).click();
  const message = page.getByRole("dialog", { name: en.bookings.rescheduled });
  await expect(message.getByText(en.insights.customerMessage.title)).toBeVisible();
  await expect(message.locator("p[data-user-content]")).toHaveText(/\S/);
  await message.getByRole("button", { name: en.common.done }).click();
  await expect(offerFor(page, "Lukas Weber")).toBeHidden();
});

test("a booking dragged near the grid's bottom edge scrolls the day down", async ({ page, request, owner }) => {
  const day = berlinDate(3);
  const nino = await addPlace(request, owner, { name: "Nino" });
  await bookByHand(request, owner, { name: "Mia Wagner", date: day, time: "10:00", resourceId: nino });
  // A laptop screen: the day is taller than its box.
  await page.setViewportSize({ width: 1280, height: 640 });

  await page.goto(`/b/${owner.businessId}/bookings?view=day&date=${day}`);
  const grid = page.locator(`[data-calendar-day="${day}"]`);
  const block = page.getByRole("button", { name: /^Mia Wagner, / });
  await expect(block).toBeVisible();
  const box = await grid.boundingBox();
  const from = await block.boundingBox();
  if (!box || !from) throw new Error("The grid is not laid out.");
  expect(await grid.evaluate((element) => element.scrollHeight - element.clientHeight)).toBeGreaterThan(ONE_HOUR);
  const top = await grid.evaluate((element) => element.scrollTop);

  await page.mouse.move(from.x + from.width / 2, from.y + 10);
  await page.mouse.down();
  await page.mouse.move(from.x + from.width / 2, from.y + 30, { steps: 4 });
  await page.mouse.move(from.x + from.width / 2, box.y + box.height - 6, { steps: 8 });
  await expect.poll(() => grid.evaluate((element) => element.scrollTop)).toBeGreaterThan(top + ONE_HOUR);
  // Escape drops nothing: the booking stays where it was.
  await page.keyboard.press("Escape");
  await page.mouse.up();
  await expect(page.locator("[data-calendar-ghost]")).toHaveCount(0);
  await expect(page.getByRole("button", { name: /^Mia Wagner, 10:00/ })).toBeAttached();
});

test("a guest house sees its rooms by night, moves a stay with the keys and opens nights from the week", async ({
  page,
  request,
  account,
}) => {
  const businessId = await createBusiness(request, account.token, {
    name: "Pension Alpenblick",
    niche_key: "hotel",
    country_code: "AT",
    city: "Innsbruck",
    languages: ["de", "en"],
    default_language: "en",
  });
  await createAssistant(request, account.token, businessId);
  const house = { token: account.token, businessId };
  const doubles = await addPlace(request, house, { name: "Doppelzimmer", byNight: true, units: 2 });
  const suite = await addPlace(request, house, { name: "Suite", byNight: true });
  const arrival = berlinDate(1);
  const stay = await bookByHand(request, house, { name: "Jonas Weber", date: arrival, nights: 2, resourceId: doubles });

  await page.goto(`/b/${businessId}/bookings?view=nights&date=${arrival}`);
  await expect(page.getByRole("radio", { name: calendar.views.nights })).toBeChecked();
  const bar = page.getByRole("button", { name: /^Jonas Weber, / });
  await expect(bar).toContainText(en.bookings.nights.other.replace("{count}", "2"));
  await expect(page.locator(`[data-calendar-room="${doubles}"]`).getByRole("button", { name: /1 of 2 taken$/ })).toHaveCount(2);
  expect(await seriousViolations(page), "the nights").toEqual([]);

  await bar.focus();
  await page.keyboard.press("ArrowDown");
  await page.keyboard.press("ArrowRight");
  await expect(page.locator(`[data-calendar-room="${suite}"] [data-calendar-ghost]`)).toBeVisible();
  await page.keyboard.press("Enter");
  await expect(page.getByRole("status").filter({ hasText: "Moved to Suite" })).toBeVisible();
  await expect(page.locator(`[data-calendar-room="${suite}"]`).getByRole("button", { name: /^Jonas Weber, / })).toBeVisible();
  await expect
    .poll(async () => {
      const now = await bookingNow(request, house, stay.id, arrival);
      return [now?.resource_id, now?.date, now?.end_date];
    })
    .toEqual([suite, berlinDate(2), berlinDate(4)]);

  await page.getByRole("radio", { name: calendar.views.week }).check({ force: true });
  const heatmap = page.getByRole("table", { name: /^How full each place is/ });
  await expect(heatmap).toBeVisible();
  expect(await seriousViolations(page), "the week").toEqual([]);
  await heatmap.getByRole("button", { name: new RegExp(`^Suite, `) }).first().click();
  await expect(page).toHaveURL(/view=nights/);
  await expect(page.getByRole("radio", { name: calendar.views.nights })).toBeChecked();
});

test.describe("on a phone", () => {
  test.use({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });

  test("the day fits the screen, scrolls its places sideways and opens a booking", async ({ page, request, owner }) => {
    const day = berlinDate(1);
    const nino = await addPlace(request, owner, { name: "Nino" });
    await addPlace(request, owner, { name: "Lena" });
    await addPlace(request, owner, { name: "Mariam" });
    await bookByHand(request, owner, { name: "Sofia Klein", date: day, time: "15:00", resourceId: nino });

    await page.goto(`/b/${owner.businessId}/bookings?view=day&date=${day}`);
    await expect(page.getByRole("radio", { name: calendar.views.day, exact: true })).toBeChecked();
    const block = page.getByRole("button", { name: /^Sofia Klein, / });
    await expect(block).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBe(0);
    await block.click();
    await expect(page.getByRole("dialog", { name: "Sofia Klein" })).toBeVisible();
  });

  test("a finger holding a booking at the grid's side scrolls the places sideways", async ({ page, request, owner }) => {
    const day = berlinDate(2);
    const nino = await addPlace(request, owner, { name: "Nino" });
    await addPlace(request, owner, { name: "Lena" });
    const mariam = await addPlace(request, owner, { name: "Mariam" });
    await bookByHand(request, owner, { name: "Elif Kaya", date: day, time: "10:00", resourceId: nino });

    await page.goto(`/b/${owner.businessId}/bookings?view=day&date=${day}`);
    const grid = page.locator(`[data-calendar-day="${day}"]`);
    const block = page.getByRole("button", { name: /^Elif Kaya, / });
    await expect(block).toBeVisible();
    const box = await grid.boundingBox();
    const from = await block.boundingBox();
    if (!box || !from) throw new Error("The grid is not laid out.");
    expect(await grid.evaluate((element) => element.scrollLeft)).toBe(0);

    const touch = await page.context().newCDPSession(page);
    const finger = (type: "touchStart" | "touchMove" | "touchEnd", x = 0, y = 0) =>
      touch.send("Input.dispatchTouchEvent", { type, touchPoints: type === "touchEnd" ? [] : [{ x, y }] });
    const y = from.y + 12;
    await finger("touchStart", from.x + from.width / 2, y);
    // A long press grabs it.
    await expect(page.locator("[data-calendar-ghost]")).toBeVisible();
    for (let step = 1; step <= 6; step += 1) {
      await finger("touchMove", from.x + from.width / 2 + ((box.x + box.width - 4 - from.x - from.width / 2) * step) / 6, y);
    }
    await expect.poll(() => grid.evaluate((element) => element.scrollLeft)).toBeGreaterThan(0);
    await expect(page.locator(`[data-calendar-column="${mariam}"] [data-calendar-ghost]`)).toBeVisible();
    await finger("touchEnd");
    await expect(page.getByRole("status").filter({ hasText: "Moved to Mariam" })).toBeVisible();
  });
});
