import { BUSINESS_SECTIONS } from "../src/lib/navigation";

import { expect, test } from "./support/fixtures";
import { en } from "./support/messages";

test.describe("every section of a business", () => {
  test("opens from the sidebar without errors", async ({ page, owner }) => {
    await page.goto(`/b/${owner.businessId}/dashboard`);
    const navigation = page.getByRole("navigation", { name: en.nav.mainNavigation });

    for (const section of BUSINESS_SECTIONS) {
      await test.step(section, async () => {
        await navigation.getByRole("link", { name: en.nav[section], exact: true }).click();
        await expect(page).toHaveURL(new RegExp(`/b/${owner.businessId}/${section}(\\?|$)`));
        await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
        await expect(navigation.getByRole("link", { name: en.nav[section], exact: true })).toHaveAttribute(
          "aria-current",
          "page",
        );
        await page.waitForLoadState("networkidle");
        // No section failed to load its data.
        await expect(page.getByRole("button", { name: en.common.retry })).toHaveCount(0);
      });
    }
  });

  test.describe("on a phone", () => {
    test.use({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });

    test("opens from the menu and fits the screen", async ({ page, owner }) => {
      await page.goto(`/b/${owner.businessId}/dashboard`);

      for (const section of BUSINESS_SECTIONS) {
        await test.step(section, async () => {
          await page.getByRole("button", { name: en.nav.openMenu }).click();
          const menu = page.getByRole("dialog", { name: en.nav.mainNavigation });
          await expect(menu).toBeVisible();
          await menu.getByRole("link", { name: en.nav[section], exact: true }).click();
          await expect(menu).toBeHidden();
          await expect(page).toHaveURL(new RegExp(`/b/${owner.businessId}/${section}(\\?|$)`));
          await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
          await page.waitForLoadState("networkidle");
          // Nothing makes the page wider than the phone.
          const overflow = await page.evaluate(
            () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
          );
          expect(overflow, `${section} scrolls sideways`).toBeLessThanOrEqual(0);
        });
      }
    });
  });
});

test.describe("lists whose every load is audited", () => {
  for (const section of ["handoffs", "conversations"] as const) {
    test(`${section} reload on return and on Refresh, never on a timer`, async ({ page, owner }) => {
      await page.clock.install();
      const loads: string[] = [];
      page.on("request", (request) => {
        if (new URL(request.url()).pathname.endsWith(`/v1/businesses/${owner.businessId}/${section}`)) {
          loads.push(request.url());
        }
      });
      await page.goto(`/b/${owner.businessId}/${section}`);
      await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
      await expect.poll(() => loads.length).toBe(1);

      // An open tab does not add an audit entry every minute.
      await page.clock.fastForward(121_000);
      await page.waitForLoadState("networkidle");
      expect(loads).toHaveLength(1);

      await page.getByRole("button", { name: en.insights.refresh }).first().click();
      await expect.poll(() => loads.length).toBe(2);
    });
  }
});

/** 23:58:30 today in Berlin (the owner fixture's time zone), and tomorrow's date there. */
function justBeforeBerlinMidnight(): { time: Date; today: string; tomorrow: string } {
  const parts = Object.fromEntries(
    new Intl.DateTimeFormat("en-US", {
      timeZone: "Europe/Berlin",
      timeZoneName: "shortOffset",
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    })
      .formatToParts(new Date())
      .map((part) => [part.type, part.value]),
  );
  const offsetHours = Number(/GMT([+-]\d+)/.exec(parts.timeZoneName ?? "")?.[1] ?? 0);
  const [year, month, day] = [Number(parts.year), Number(parts.month), Number(parts.day)];
  const time = new Date(Date.UTC(year, month - 1, day, 23 - offsetHours, 58, 30));
  const iso = (date: Date) => date.toISOString().slice(0, 10);
  const today = iso(new Date(Date.UTC(year, month - 1, day)));
  const tomorrow = iso(new Date(Date.UTC(year, month - 1, day + 1)));
  return { time, today, tomorrow };
}

test("today's bookings move on to the next day at local midnight", async ({ page, owner }) => {
  const { time, today, tomorrow } = justBeforeBerlinMidnight();
  await page.clock.install({ time });
  const requestedDays: string[] = [];
  page.on("request", (request) => {
    const url = new URL(request.url());
    if (url.pathname.endsWith(`/v1/businesses/${owner.businessId}/bookings`)) {
      requestedDays.push(url.searchParams.get("from") ?? "");
    }
  });
  await page.goto(`/b/${owner.businessId}/bookings?range=today`);
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await expect.poll(() => requestedDays.at(-1)).toBe(today);

  // The screen stays open across midnight: the next check asks for the new day.
  await page.clock.fastForward("03:00");

  await expect.poll(() => requestedDays.at(-1)).toBe(tomorrow);
});
