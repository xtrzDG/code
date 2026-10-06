/**
 * The cabinet on a phone (390×844), against the real API and the demo
 * restaurant (support/demo.ts): on Inbox, Bookings, Channels and the
 * Overview the first conversation, booking, channel card or "Today" block
 * starts in the top half of the screen, and no page is taller than four
 * screens as it opens (the Overview's folded rows closed). Channels keeps
 * its cards on the page and opens the website chat, call forwarding and
 * sharing as pages of their own; the Overview's folds open on a tap and
 * stay open after a reload.
 */

import type { Locator, Page } from "@playwright/test";

import { uniqueSuffix } from "./support/api";
import { signInAsDemoOwner, visitorAsksForPerson } from "./support/demo";
import { expect, signInContext, test } from "./support/fixtures";
import { en } from "./support/messages";

test.describe.configure({ timeout: 120_000 });

const PHONE = { width: 390, height: 844 } as const;
/** The website chat's embed code needs APP_BASE_URL, which the suite's API does not set. */
const SNIPPET_UNAVAILABLE = /status of 502 \(Bad Gateway\).*\/channels\/web\/snippet/;
test.use({ viewport: PHONE, isMobile: true, hasTouch: true });

/** The page's whole height, scrolled to the end. */
function pageHeight(page: Page): Promise<number> {
  return page.evaluate(() => document.documentElement.scrollHeight);
}

async function expectInTopHalf(locator: Locator, what: string): Promise<void> {
  await expect(locator, what).toBeVisible();
  const box = await locator.boundingBox();
  expect(box, `${what} is laid out`).not.toBeNull();
  expect(box!.y, `${what} starts in the top half`).toBeLessThan(PHONE.height / 2);
}

test("the first conversation, booking, channel card and Today start in the top half; no page is taller than four screens", async ({
  page,
  request,
}) => {
  const owner = await signInAsDemoOwner(request);
  await signInContext(page.context(), owner.token);
  // At least one conversation waits for a person, whatever the other specs resolved.
  await visitorAsksForPerson(request, owner.businessId, `Phone layout visitor ${uniqueSuffix()}`);

  const pages: [string, string, (page: Page) => Locator][] = [
    ["Inbox", "inbox", (current) => current.locator("[data-inbox-row]").first()],
    [
      "Bookings",
      "bookings",
      // Today's first arrival, or the agenda's "nothing today" when the suite runs late at night.
      (current) => current.locator("[data-booking-card]").first().or(current.locator('[aria-labelledby="bookings-today"]')).first(),
    ],
    ["Channels", "assistant/channels", (current) => current.locator('section[aria-labelledby^="channel-"]').first()],
    ["Overview", "overview", (current) => current.locator("[data-today-block]")],
  ];
  for (const [name, path, first] of pages) {
    await page.goto(`/b/${owner.businessId}/${path}`);
    await expectInTopHalf(first(page), `${name}: the first card`);
    expect(await pageHeight(page), `${name}: the page's height`).toBeLessThanOrEqual(4 * PHONE.height);
  }
});

test("Channels opens the website chat, call forwarding and sharing as pages of their own, each with the way back", async ({
  page,
  request,
  consoleErrors,
}) => {
  consoleErrors.allow(SNIPPET_UNAVAILABLE);
  const owner = await signInAsDemoOwner(request);
  await signInContext(page.context(), owner.token);
  const channels = `/b/${owner.businessId}/assistant/channels`;
  await page.goto(channels);
  // On a phone the setup lives on the sub-pages: the cards' page has no website chat code nor share card.
  await expect(page.getByRole("region", { name: en.share.title })).toHaveCount(0);

  for (const subpage of ["website", "calls", "share"] as const) {
    await page.locator(`[data-channel-page="${subpage}"]`).click();
    await expect(page).toHaveURL(new RegExp(`${channels}/${subpage}$`));
    await expect(page.getByRole("link", { name: en.channelPages.back })).toBeVisible();
    expect(await pageHeight(page), `${subpage}: the page's height`).toBeLessThanOrEqual(4 * PHONE.height);
    await page.getByRole("link", { name: en.channelPages.back }).click();
    await expect(page).toHaveURL(new RegExp(`${channels}$`));
  }
  await page.goto(`${channels}/share`);
  await expect(page.getByRole("region", { name: en.share.title })).toBeVisible();
});

test("the Overview starts with Today; a folded row opens on a tap and stays open after a reload", async ({ page, request }) => {
  const owner = await signInAsDemoOwner(request);
  await signInContext(page.context(), owner.token);
  await page.goto(`/b/${owner.businessId}/overview`);

  const today = page.locator("[data-today-block]");
  await expect(today.getByRole("heading", { name: en.overviewPhone.today.title })).toBeVisible();
  const languages = page.locator('[data-phone-fold="languages"]');
  const row = languages.getByRole("button", { name: new RegExp(`^${en.dashboard.breakdown.languages}`) });
  await expect(row).toHaveAttribute("aria-expanded", "false");
  await row.click();
  await expect(row).toHaveAttribute("aria-expanded", "true");
  await expect(languages.getByRole("list")).toBeVisible();

  await page.reload();
  await expect(page.locator('[data-phone-fold="languages"]').getByRole("button", { name: new RegExp(`^${en.dashboard.breakdown.languages}`) })).toHaveAttribute(
    "aria-expanded",
    "true",
  );
});
