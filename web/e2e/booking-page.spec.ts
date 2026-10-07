/**
 * A guest's booking page (/r/{token}) against the real API: a table booked
 * at the demo restaurant through its website chat, the written confirmation
 * in the chat, and its link opening the booking in the guest's language
 * (English, Georgian, right-to-left Hebrew) — the calendar file, a move to
 * another free time (a new link, a new confirmation in the chat, the old
 * link closed), a cancellation, and a link that does not work.
 */

import { readFileSync } from "node:fs";

import AxeBuilder from "@axe-core/playwright";
import type { Page } from "@playwright/test";

import { bookThroughWebChat, bookingDate, chatAnswers, dayAfter } from "./support/booking-page";
import { DEMO_RESTAURANT, signInAsDemoOwner } from "./support/demo";
import { expect, test } from "./support/fixtures";
import { waitForNetworkQuiet } from "./support/network";

/** "Thursday, October 8, 2026": a calendar day's name in English. */
function fullDate(isoDate: string): string {
  return new Intl.DateTimeFormat("en", { dateStyle: "full", timeZone: "UTC" }).format(new Date(`${isoDate}T12:00:00Z`));
}

/** "Oct 8, 2026": the date as the English date field shows it. */
function shortDate(isoDate: string): string {
  return new Intl.DateTimeFormat("en", { dateStyle: "medium", timeZone: "UTC" }).format(new Date(`${isoDate}T12:00:00Z`));
}

/** Serious and critical WCAG 2.1 A/AA violations on the page (axe-core). */
async function seriousViolations(page: Page): Promise<string[]> {
  await waitForNetworkQuiet(page);
  const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
  return results.violations
    .filter((violation) => violation.impact === "serious" || violation.impact === "critical")
    .map((violation) => `${violation.id}: ${violation.nodes.map((node) => node.target.join(" ")).join(" | ")}`);
}

test("an English guest opens the link, saves the calendar file and moves the booking", async ({ page, request }) => {
  const { businessId } = await signInAsDemoOwner(request);
  const booked = await bookThroughWebChat(request, businessId, "en");
  expect(booked.confirmation).toContain(`${DEMO_RESTAURANT}: your booking is confirmed.`);

  const response = await page.goto(booked.path);

  // The address is the key to the booking: kept out of search engines, caches and Referers.
  expect(response?.headers()["x-robots-tag"]).toBe("noindex, nofollow");
  expect(response?.headers()["referrer-policy"]).toBe("no-referrer");
  expect(response?.headers()["cache-control"]).toContain("no-store");
  await expect(page.locator('meta[name="robots"]')).toHaveAttribute("content", "noindex, nofollow");
  await expect(page).toHaveTitle(`Your booking · ${DEMO_RESTAURANT}`);
  await expect(page.locator("main")).toHaveAttribute("lang", "en");
  await expect(page.locator("main")).toHaveAttribute("dir", "ltr");

  await expect(page.getByRole("heading", { level: 1, name: "Your booking" })).toBeVisible();
  // The closed cancel dialog names the business too, in a span of its own (user content).
  await expect(page.getByText(DEMO_RESTAURANT, { exact: true }).filter({ visible: true })).toBeVisible();
  await expect(page.getByText("Confirmed", { exact: true })).toBeVisible();
  await expect(page.getByRole("definition").filter({ hasText: /\d{4}/ }).first()).toBeVisible();
  await expect(page.getByRole("link", { name: "Open in maps" })).toHaveAttribute("href", "https://mtsvane-ezo.example/map");
  const contacts = page.getByRole("region", { name: "Write to us" });
  await expect(contacts.getByRole("link", { name: "Chat" })).toHaveAttribute("href", /\/c\/[A-Za-z0-9_-]+$/);

  const download = page.waitForEvent("download");
  await page.getByRole("link", { name: "Add to calendar" }).click();
  const file = await download;
  expect(file.suggestedFilename()).toMatch(/\.ics$/);
  const calendar = readFileSync(await file.path(), "utf8");
  expect(calendar).toContain("BEGIN:VCALENDAR");
  expect(calendar).toContain(`SUMMARY:${DEMO_RESTAURANT}`);
  expect(calendar).toContain("STATUS:CONFIRMED");

  // Another free time, the next day, picked in the date field's calendar.
  const bookedDay = await bookingDate(request, booked.token);
  const nextDay = dayAfter(bookedDay);
  await page.getByRole("button", { name: "Change time" }).click();
  const move = page.getByRole("region", { name: "Choose a new time" });
  await move.getByRole("button", { name: "Open the calendar" }).click();
  const picker = move.getByRole("dialog", { name: "Calendar" });
  if (nextDay.slice(0, 7) !== bookedDay.slice(0, 7)) {
    await picker.getByRole("button", { name: "Next month" }).click();
  }
  await picker.getByRole("button", { name: fullDate(nextDay), exact: true }).click();
  await expect(picker).toBeHidden();
  await expect(move.getByRole("combobox", { name: "Date" })).toHaveValue(shortDate(nextDay));
  const times = move.getByRole("group", { name: "Free times" }).getByRole("button");
  await times.nth(1).click();
  await expect(times.nth(1)).toHaveAttribute("aria-pressed", "true");
  await move.getByRole("button", { name: /^Move to / }).click();

  await expect(page.getByText(/^Done! Your booking is moved\./)).toBeVisible();
  await expect(page).not.toHaveURL(new RegExp(booked.token));
  const newToken = new URL(page.url()).pathname.split("/").pop()!;
  expect(await bookingDate(request, newToken)).toBe(nextDay);
  // The chat has the new confirmation with the new link.
  await expect
    .poll(async () => (await chatAnswers(request, businessId, booked.sessionKey)).join("\n"))
    .toContain(`/r/${newToken}`);

  // The old link no longer opens the booking.
  await page.goto(booked.path);
  await expect(page.getByRole("heading", { level: 1, name: "This booking cannot be opened" })).toBeVisible();
  await expect(page.getByText(/^This booking was changed after the link was sent\./)).toBeVisible();
});

test.describe("in Georgian", () => {
  test.use({ locale: "ka-GE" });

  test("a Georgian guest cancels the booking from its page", async ({ page, request }) => {
    const { businessId } = await signInAsDemoOwner(request);
    const booked = await bookThroughWebChat(request, businessId, "ka");
    expect(booked.confirmation).toContain("თქვენი ჯავშანი დადასტურებულია.");

    await page.goto(booked.path);

    await expect(page.locator("main")).toHaveAttribute("lang", "ka");
    await expect(page.getByRole("heading", { level: 1, name: "თქვენი ჯავშანი" })).toBeVisible();
    await expect(page.getByText("დადასტურებულია", { exact: true })).toBeVisible();
    await expect(page.getByRole("heading", { level: 2, name: "მოგვწერეთ" })).toBeVisible();

    await page.getByRole("button", { name: "ჯავშნის გაუქმება" }).click();
    const dialog = page.getByRole("dialog", { name: "გავაუქმოთ ეს ჯავშანი?" });
    await expect(dialog).toBeVisible();
    await dialog.getByRole("button", { name: "დიახ, გაუქმება" }).click();

    await expect(dialog).toBeHidden();
    await expect(page.getByText(`ჯავშანი გაუქმებულია. ${DEMO_RESTAURANT} ინფორმირებულია.`)).toBeVisible();
    await expect(page.getByText("გაუქმებულია", { exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: "ჯავშნის გაუქმება" })).toHaveCount(0);
    await expect(page.getByRole("link", { name: "კალენდარში დამატება" })).toHaveCount(0);
  });
});

test.describe("in Hebrew", () => {
  test.use({ locale: "he-IL" });

  test("a Hebrew guest reads the booking right to left and sees the free times", async ({ page, request }) => {
    const { businessId } = await signInAsDemoOwner(request);
    const booked = await bookThroughWebChat(request, businessId, "he");
    expect(booked.confirmation).toContain("ההזמנה שלך אושרה.");

    await page.goto(booked.path);

    await expect(page.locator("main")).toHaveAttribute("dir", "rtl");
    await expect(page.locator("main")).toHaveAttribute("lang", "he");
    const card = page.locator("article");
    expect(await card.evaluate((element) => getComputedStyle(element).direction)).toBe("rtl");
    await expect(page.getByRole("heading", { level: 1, name: "ההזמנה שלכם" })).toBeVisible();
    await expect(page.getByText("מאושרת", { exact: true })).toBeVisible();
    await expect(page.getByRole("heading", { level: 2, name: "כתבו לנו" })).toBeVisible();

    await page.getByRole("button", { name: "שינוי שעה" }).click();
    const move = page.getByRole("region", { name: "בחרו שעה חדשה" });
    // The date field and its calendar speak Hebrew and read right to left.
    await move.getByRole("button", { name: "פתיחת לוח השנה" }).click();
    const calendar = move.getByRole("dialog", { name: "לוח שנה" });
    expect(await calendar.evaluate((element) => getComputedStyle(element).direction)).toBe("rtl");
    await expect(calendar.getByRole("button", { name: "החודש הבא" })).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(calendar).toBeHidden();
    await move.getByRole("combobox", { name: "תאריך" }).fill(dayAfter(await bookingDate(request, booked.token)));
    await expect(move.getByRole("group", { name: "שעות פנויות" }).getByRole("button").first()).toBeVisible();
    await move.getByRole("button", { name: "סגירה" }).click();
    await expect(move).toBeHidden();
  });
});

test("the page passes the accessibility audit in the light and the dark scheme", async ({ page, request }) => {
  const { businessId } = await signInAsDemoOwner(request);
  const booked = await bookThroughWebChat(request, businessId, "en");

  for (const colorScheme of ["light", "dark"] as const) {
    await page.emulateMedia({ colorScheme });
    await page.goto(booked.path);
    await expect(page.getByRole("heading", { level: 1, name: "Your booking" })).toBeVisible();
    expect(await seriousViolations(page), colorScheme).toEqual([]);
  }
  await page.getByRole("button", { name: "Change time" }).click();
  await expect(page.getByRole("region", { name: "Choose a new time" }).getByRole("button").first()).toBeVisible();
  expect(await seriousViolations(page), "with the move panel open").toEqual([]);
});

test("a link that does not work says so", async ({ page }) => {
  await page.goto(`/r/${"x".repeat(60)}`);

  await expect(page.getByRole("heading", { level: 1, name: "This booking cannot be opened" })).toBeVisible();
  await expect(page.getByText("This link does not work. Check that you opened all of it.")).toBeVisible();
  await expect(page.getByRole("button")).toHaveCount(0);
});
