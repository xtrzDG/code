/**
 * A guest's booking page (/r/{token}) against the real API: a table booked
 * at the demo restaurant through its website chat, the written confirmation
 * in the chat, and its link opening the booking in the guest's language
 * (English, Georgian, right-to-left Hebrew) — the calendar file, a move to
 * another free time (a new link, a new confirmation in the chat, the old
 * link closed), a cancellation, and a link that does not work.
 */

import { readFileSync } from "node:fs";

import { bookThroughWebChat, bookingDate, chatAnswers, dayAfter } from "./support/booking-page";
import { DEMO_RESTAURANT, signInAsDemoOwner } from "./support/demo";
import { expect, test } from "./support/fixtures";

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
  await expect(page.getByText(DEMO_RESTAURANT, { exact: true })).toBeVisible();
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

  // Another free time, the next day.
  const nextDay = dayAfter(await bookingDate(request, booked.token));
  await page.getByRole("button", { name: "Change time" }).click();
  const move = page.getByRole("region", { name: "Choose a new time" });
  await move.getByLabel("Date").fill(nextDay);
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
    await move.getByLabel("תאריך").fill(dayAfter(await bookingDate(request, booked.token)));
    await expect(move.getByRole("group", { name: "שעות פנויות" }).getByRole("button").first()).toBeVisible();
    await move.getByRole("button", { name: "סגירה" }).click();
    await expect(move).toBeHidden();
  });
});

test("a link that does not work says so", async ({ page }) => {
  await page.goto(`/r/${"x".repeat(60)}`);

  await expect(page.getByRole("heading", { level: 1, name: "This booking cannot be opened" })).toBeVisible();
  await expect(page.getByText("This link does not work. Check that you opened all of it.")).toBeVisible();
  await expect(page.getByRole("button")).toHaveCount(0);
});
