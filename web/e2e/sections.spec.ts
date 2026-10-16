/**
 * Sections whose data needs care: lists whose every load is written to the
 * audit log, and "today" moving on at the business's midnight. Opening every
 * section and page: navigation.spec.ts.
 */

import { expect, test } from "./support/fixtures";
import { waitForNetworkQuiet } from "./support/network";

test.describe("lists whose every load is audited", () => {
  // The inbox views come from GET …/inbox, a search through the history from GET …/conversations.
  const lists = [
    { name: "the inbox", endpoint: "inbox", page: "inbox" },
    { name: "a search of all conversations", endpoint: "conversations", page: "inbox?view=all&status=open" },
  ] as const;
  for (const { name, endpoint, page: path } of lists) {
    test(`${name} reloads on return to the tab, never on a timer`, async ({ page, owner }) => {
      await page.clock.install();
      const loads: string[] = [];
      page.on("request", (request) => {
        if (new URL(request.url()).pathname.endsWith(`/v1/businesses/${owner.businessId}/${endpoint}`)) {
          loads.push(request.url());
        }
      });
      await page.goto(`/b/${owner.businessId}/${path}`);
      await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
      await expect.poll(() => loads.length).toBe(1);

      // An open tab does not add an audit entry every minute.
      await page.clock.fastForward(121_000);
      await waitForNetworkQuiet(page);
      expect(loads).toHaveLength(1);

      // Coming back to the tab reloads (the live stream does the rest).
      await page.evaluate(() => document.dispatchEvent(new Event("visibilitychange")));
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
