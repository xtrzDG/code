/**
 * The hosted chat page (/c/{address}) against the real API: a business's
 * chat on a page of its own, in the visitor's language (English, Georgian
 * and right-to-left Hebrew), at the business's current address, out of
 * search engines and under a policy that lets the page reach only the API
 * (a violation would be a console error, which fails the test). Its
 * privacy notice and an unknown address are covered too.
 */

import { uniqueSuffix } from "./support/api";
import { API_URL } from "./support/env";
import { expect, test } from "./support/fixtures";
import { openChatBusiness } from "./support/hosted-chat";

test("the chat page opens the business's chat in English at its current address, out of search engines", async ({
  page,
  request,
  account,
}) => {
  const business = await openChatBusiness(request, account.token);
  expect(business.slug).toMatch(/^cafe-shalom-[0-9a-f]+$/);

  const response = await page.goto(`/c/${business.id}?src=qr`);

  await expect(page).toHaveURL(new RegExp(`/c/${business.slug}\\?src=qr$`));
  expect(response?.headers()["x-robots-tag"]).toBe("noindex, nofollow");
  expect(response?.headers()["content-security-policy"]).toContain(`connect-src 'self' ${new URL(API_URL).origin}`);
  await expect(page.locator('meta[name="robots"]')).toHaveAttribute("content", "noindex, nofollow");
  await expect(page).toHaveTitle(business.name);
  await expect(page.locator("main")).toHaveAttribute("lang", "en");

  await expect(page.getByRole("heading", { level: 1, name: business.name })).toBeVisible();
  await expect(page.getByRole("button", { name: "Talk to a person" })).toBeVisible();
  await expect(page.getByText("AI assistant · can make mistakes")).toBeVisible();
  await expect(page.getByRole("link", { name: "Privacy" })).toHaveAttribute("href", new RegExp(`/c/${business.slug}/privacy$`));

  await page.getByRole("textbox").fill("Do you have a terrace?");
  await page.getByRole("textbox").press("Enter");
  await expect(page.locator(".aw-message", { hasText: "Do you have a terrace?" })).toBeVisible();
  // The visitor key stays in the browser, never in the address.
  const sessionKey = await page.evaluate((id) => localStorage.getItem(`aw-chat:${id}:session`), business.id);
  expect(sessionKey).toMatch(/^v1_/);
  expect(page.url()).not.toContain(sessionKey ?? "-");
});

test.describe("in Georgian", () => {
  test.use({ locale: "ka-GE" });

  test("the chat page and the chat speak Georgian", async ({ page, request, account }) => {
    const business = await openChatBusiness(request, account.token);

    await page.goto(`/c/${business.slug}`);

    await expect(page.locator("main")).toHaveAttribute("lang", "ka");
    await expect(page.getByRole("heading", { level: 1, name: business.name })).toBeVisible();
    await expect(page.getByRole("textbox")).toHaveAttribute("placeholder", "დაწერეთ შეტყობინება…");
    await expect(page.getByRole("button", { name: "ადამიანთან დაკავშირება" })).toBeVisible();
  });
});

test.describe("in Hebrew", () => {
  test.use({ locale: "he-IL" });

  test("the chat page reads right to left and Talk to a person hands the chat to staff", async ({ page, request, account }) => {
    const business = await openChatBusiness(request, account.token);

    await page.goto(`/c/${business.slug}`);

    await expect(page.locator("main")).toHaveAttribute("dir", "rtl");
    await expect(page.locator("main")).toHaveAttribute("lang", "he");
    const direction = page.locator("[data-assistant-workshop-chat]").locator(".aw");
    await expect(direction).toHaveAttribute("dir", "rtl");

    await page.getByRole("button", { name: "לדבר עם נציג" }).click();

    await expect(page.getByRole("button", { name: "לדבר עם נציג" })).toBeHidden();
    // The greeting, then what the visitor is told (the API's text or the widget's own).
    await expect(page.locator(".aw-message, .aw-notice")).toHaveCount(2);
  });
});

test("the privacy notice names the business, and an unknown address says so", async ({ page, request, account }) => {
  const business = await openChatBusiness(request, account.token);

  await page.goto(`/c/${business.slug}/privacy`);
  await expect(page.getByRole("heading", { level: 1, name: "Privacy notice" })).toBeVisible();
  await expect(page.getByText(`How ${business.name} handles what you write in its chat`)).toBeVisible();
  await page.getByRole("link", { name: "Back to the chat" }).click();
  await expect(page).toHaveURL(new RegExp(`/c/${business.slug}$`));

  const missing = await page.goto(`/c/no-chat-${uniqueSuffix()}`);
  expect(missing?.status()).toBe(404);
  await expect(page.getByRole("heading", { name: "There is no chat at this address. Check the link." })).toBeVisible();
});
