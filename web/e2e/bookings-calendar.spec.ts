/**
 * Bookings → Day, Week, Nights against the real API:
 *
 *  - a booking dragged to another master's column an hour later moves
 *    there (the API agrees), and Undo in the toast puts it back;
 *  - the keyboard moves a focused booking a quarter of an hour per arrow
 *    and to the next place, Enter moves it, Escape cancels a preview;
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

  await toast.getByRole("button", { name: en.common.undo }).click();
  await expect(page.getByText(calendar.move.undone)).toBeVisible();
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
});
