/**
 * The hosted chat page as a link in bio (/c/{address}), at the demo
 * restaurant: beside the chat on a wide screen and above it on a phone,
 * whether the place is open now, its week, its address with a map link and
 * a Book button that starts the booking in the chat.
 */

import { DEMO_RESTAURANT, signInAsDemoOwner } from "./support/demo";
import { expect, test } from "./support/fixtures";

const BOOK_PROMPT = "Hello! I'd like to book.";

test("on a wide screen the information sits beside the chat", async ({ page, request }) => {
  const { businessId } = await signInAsDemoOwner(request);

  await page.goto(`/c/${businessId}`);

  const panel = page.getByRole("complementary", { name: DEMO_RESTAURANT });
  await expect(panel).toBeVisible();
  await expect(panel.getByRole("heading", { level: 2, name: DEMO_RESTAURANT })).toBeVisible();
  await expect(panel.getByText(/^(Open now · until|Closed now · opens) /)).toBeVisible();
  await expect(panel.getByRole("heading", { name: "Opening hours" })).toBeVisible();
  await expect(panel.getByRole("listitem")).toHaveCount(7);
  await expect(panel.locator('li[aria-current="date"]')).toHaveCount(1);
  await expect(panel.getByRole("link", { name: "Open in maps" })).toHaveAttribute("href", "https://mtsvane-ezo.example/map");
  // The details are always open on a wide screen: no toggle.
  await expect(panel.getByRole("button", { name: "Hours and address" })).toBeHidden();

  // Two columns: the panel to the left of the chat, side by side.
  const chat = page.locator(".hc-frame");
  const [panelBox, chatBox] = [await panel.boundingBox(), await chat.boundingBox()];
  expect(panelBox && chatBox).toBeTruthy();
  expect(panelBox!.x + panelBox!.width).toBeLessThanOrEqual(chatBox!.x);
  expect(Math.abs(panelBox!.y - chatBox!.y)).toBeLessThan(2);
  // The chat's own header still names the business once at level 1.
  await expect(page.getByRole("heading", { level: 1, name: DEMO_RESTAURANT })).toBeVisible();

  // Book starts the booking in the chat: the visitor only sends it.
  const input = page.locator("[data-assistant-workshop-chat]").locator("textarea.aw-input");
  await expect(input).toBeEditable();
  await panel.getByRole("button", { name: "Book" }).click();
  await expect(input).toHaveValue(BOOK_PROMPT);
  await expect(input).toBeFocused();
});

test.describe("on a phone", () => {
  test.use({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });

  test("the information is a bar above the chat, its details behind a toggle", async ({ page, request }) => {
    const { businessId } = await signInAsDemoOwner(request);

    await page.goto(`/c/${businessId}`);

    const panel = page.getByRole("complementary", { name: DEMO_RESTAURANT });
    await expect(panel.getByRole("button", { name: "Book" })).toBeVisible();
    // The chat's header names the business: the panel's name stays hidden.
    await expect(panel.getByRole("heading", { level: 2 })).toBeHidden();
    const toggle = panel.getByRole("button", { name: "Hours and address" });
    await expect(toggle).toHaveAttribute("aria-expanded", "false");
    await expect(panel.getByRole("heading", { name: "Opening hours" })).toBeHidden();

    await toggle.click();

    await expect(toggle).toHaveAttribute("aria-expanded", "true");
    await expect(panel.getByRole("heading", { name: "Opening hours" })).toBeVisible();
    await expect(panel.getByRole("link", { name: "Open in maps" })).toBeVisible();

    // A bar above the chat, as wide as the screen, and no sideways scrolling.
    const chat = page.locator(".hc-frame");
    const [panelBox, chatBox] = [await panel.boundingBox(), await chat.boundingBox()];
    expect(panelBox!.y + panelBox!.height).toBeLessThanOrEqual(chatBox!.y + 1);
    expect(panelBox!.width).toBeGreaterThan(380);
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
  });
});
