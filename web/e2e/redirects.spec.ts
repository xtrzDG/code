/**
 * Addresses from before the five sections still lead where they meant:
 * bookmarks, links in old messages, the payment page's and Google's
 * returns, settings tabs that lived in the hash.
 */

import { expect, test } from "./support/fixtures";

test("old addresses open their new places and keep the query", async ({ page, owner }) => {
  const base = `/b/${owner.businessId}`;
  const moves: [string, string][] = [
    ["/dashboard?period=7d", "/overview?period=7d"],
    ["/conversations", "/messages"],
    ["/conversations/conversation_1?status=open", "/messages/conversation_1?status=open"],
    ["/handoffs?tab=resolved", "/messages/handoffs?tab=resolved"],
    ["/leads?status=new", "/messages/leads?status=new"],
    ["/knowledge/import", "/assistant/knowledge/import"],
    ["/channels?calendar=connected", "/assistant/channels?calendar=connected"],
    ["/billing", "/settings/billing"],
    ["", "/overview"],
  ];
  for (const [from, to] of moves) {
    await test.step(from, async () => {
      const response = await page.request.get(`${base}${from}`, { maxRedirects: 0 });
      expect([307, 308]).toContain(response.status());
      const location = new URL(response.headers().location ?? "", "http://localhost");
      expect(`${location.pathname}${location.search}`).toBe(`${base}${to}`);
    });
  }
});

test("a settings tab from the old hash opens its own page", async ({ page, owner }) => {
  await page.goto(`/b/${owner.businessId}/settings#team`);
  await expect(page).toHaveURL(new RegExp(`/b/${owner.businessId}/settings/team$`));
});

test("the setup flow's old steps open under Hours and rules once the assistant exists", async ({ page, owner }) => {
  await page.goto(`/b/${owner.businessId}/onboarding?step=booking_rules`);
  await expect(page).toHaveURL(new RegExp(`/b/${owner.businessId}/assistant/profile\\?step=booking_rules$`));
});
