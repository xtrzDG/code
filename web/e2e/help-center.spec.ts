/**
 * Help and support: a page's "?" opens its guide in a drawer (links between
 * guides open in place, with a way back, and the help center has the whole
 * article); the one-time tip on the Inbox shows once per person, across
 * reloads; the public help center searches the articles; "What's new" shows
 * a dot in the account menu until it is opened; on a phone the "?" sits in
 * the top bar; the help center and the status page pass the accessibility
 * audit in both themes.
 */

import AxeBuilder from "@axe-core/playwright";

import { SUPPORT_TELEGRAM, WEB_URL } from "./support/env";
import { expect, test } from "./support/fixtures";
import { en } from "./support/messages";
import { waitForNetworkQuiet } from "./support/network";

const help = en.helpCenter;
const tips = en.coachMarks;

test("a page's ? opens its guide in a drawer, and the inbox tip shows only once", async ({ page, owner }) => {
  await page.goto(`/b/${owner.businessId}/inbox`);
  await waitForNetworkQuiet(page);

  const tip = page.getByRole("region", { name: tips.inbox.title });
  await expect(tip).toBeVisible();
  await tip.getByRole("button", { name: tips.gotIt }).click();
  await expect(tip).toBeHidden();
  await page.reload();
  await waitForNetworkQuiet(page);
  await expect(page.getByRole("heading", { level: 1, name: en.inbox.title })).toBeVisible();
  await expect(page.getByRole("region", { name: tips.inbox.title })).toHaveCount(0);

  await page.getByRole("button", { name: help.pageHelp }).click();
  const drawer = page.getByRole("dialog", { name: "Inbox" });
  await expect(drawer.getByRole("heading", { name: "Views" })).toBeVisible();
  // The support team's Telegram, from SUPPORT_TELEGRAM.
  await expect(drawer.getByRole("link", { name: new RegExp(en.helpCenter.support.telegram) })).toHaveAttribute(
    "href",
    `https://t.me/${SUPPORT_TELEGRAM}`,
  );

  // A link to another guide opens it in place, and Back returns.
  await drawer.getByRole("button", { name: "Teach the assistant" }).click();
  const teach = page.getByRole("dialog", { name: "Teach your assistant" });
  await expect(teach.getByRole("heading", { name: "Fix a wrong answer" })).toBeVisible();
  await teach.getByRole("button", { name: help.back }).click();
  await expect(page.getByRole("dialog", { name: "Inbox" })).toBeVisible();

  await page.getByRole("link", { name: help.openInCenter }).click();
  await expect(page).toHaveURL(/\/help\/inbox$/);
  await expect(page.getByRole("heading", { level: 1, name: "Inbox" })).toBeVisible();
});

test("the help center finds articles for anyone, signed in or not", async ({ page, consoleErrors }) => {
  await page.goto("/help");
  await expect(page.getByRole("heading", { level: 1, name: help.title })).toBeVisible();
  await expect(page.getByRole("heading", { name: help.topics.channels })).toBeVisible();

  await page.getByRole("searchbox", { name: help.searchLabel }).fill("BotFather token");
  const results = page.getByRole("region", { name: /found/ });
  await expect(results.getByRole("link").first()).toContainText("Telegram");
  await results.getByRole("link").first().click();
  await expect(page).toHaveURL(/\/help\/telegram$/);
  await expect(page.getByRole("heading", { level: 1, name: "Telegram" })).toBeVisible();

  // The 404 page itself.
  consoleErrors.allow(/status of 404 \(Not Found\) \(http:\/\/localhost:\d+\/help\/no-such-article\)/);
  const response = await page.goto("/help/no-such-article");
  expect(response?.status()).toBe(404);
});

test("What's new shows a dot in the account menu until it is opened", async ({ page, owner }) => {
  await page.goto(`/b/${owner.businessId}/overview`);
  await waitForNetworkQuiet(page);
  const accountButton = page.getByRole("button", { name: new RegExp(en.account.menu) });
  await expect(page.locator("[data-changelog-dot]")).toBeVisible();
  await accountButton.click();
  const panel = page.getByRole("dialog", { name: en.account.menu });
  const whatsNew = panel.getByRole("link", { name: new RegExp(help.support.whatsNew) });
  await expect(whatsNew).toContainText("1 new");
  await whatsNew.click();

  await expect(page.getByRole("heading", { level: 1, name: en.changelog.title })).toBeVisible();
  await expect(page.getByText(en.changelog.newBadge, { exact: true })).toBeVisible();
  await waitForNetworkQuiet(page);

  await page.goto(`/b/${owner.businessId}/overview`);
  await waitForNetworkQuiet(page);
  await expect(page.locator("[data-changelog-dot]")).toHaveCount(0);
});

test.describe("on a phone", () => {
  test.use({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });

  test("the ? in the top bar opens the page's guide", async ({ page, owner }) => {
    await page.goto(`/b/${owner.businessId}/assistant/channels`);
    await waitForNetworkQuiet(page);
    const tip = page.getByRole("region", { name: tips.channels.title });
    await expect(tip).toBeVisible();
    // On a phone the tip is one line just above the tab bar, not a card over the first screen.
    const tipBox = await tip.boundingBox();
    const tabBarBox = await page.getByRole("navigation", { name: en.navigation.tabBar }).boundingBox();
    expect(tipBox?.height ?? 0).toBeLessThanOrEqual(56);
    expect((tipBox?.y ?? 0) + (tipBox?.height ?? 0)).toBeLessThanOrEqual(tabBarBox?.y ?? 0);
    // The current sub-tab (Channels) is scrolled into sight in the Assistant's row.
    await expect(page.locator('nav [aria-current="page"]').filter({ hasText: en.navigation.pages.assistantChannels }).first()).toBeInViewport();
    await page.getByRole("banner").getByRole("button", { name: help.pageHelp }).click();
    const drawer = page.getByRole("dialog", { name: "Where your customers write and call" });
    await expect(drawer.getByRole("heading", { name: "Guides" })).toBeVisible();
    const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
    expect(scrollWidth).toBeLessThanOrEqual(390);
  });

  for (const theme of ["dark", "light"] as const) {
    test(`the help center and the status page pass the audit in the ${theme} theme`, async ({ page }) => {
      await page.context().addCookies([{ name: "aw_theme", value: theme, url: WEB_URL }]);
      for (const path of ["/help", "/help/call-forwarding", "/status"]) {
        await page.goto(path);
        await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
        await waitForNetworkQuiet(page);
        const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
        expect(results.violations, path).toEqual([]);
        expect(await page.evaluate(() => document.documentElement.scrollWidth), path).toBeLessThanOrEqual(390);
      }
    });
  }
});
