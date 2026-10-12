/**
 * The cabinet's motion budget on a phone (390×844, touch), against the
 * real API and the demo restaurant (support/demo.ts), along one round:
 * the Overview's periods (the numbers count to the new ones), the tab bar
 * to the Inbox, its views (rows come and go), "More", a conversation
 * opened from its row (the customer morphs into the header where the
 * browser has view transitions), back, and the tab bar to the Overview.
 *
 * The first round fetches everything; the measured rounds after it find it
 * cached, so what they measure is the motion and the rendering, not the
 * network. Between taps the test waits as a person looks at what a tap
 * brought: until the page has finished rendering it.
 *
 * - With full motion on a processor four times slower (a mid-range phone
 *   by Lighthouse's measure), every tap paints within 200 ms (INP: the
 *   slowest tap of a round, the median of three rounds, so one round slowed
 *   by a busy machine does not decide) and nothing shifts in any of them
 *   (CLS 0); the motion is really there: things move and the conversation
 *   morphs.
 * - With the device's reduced motion, and with the cabinet's own "Reduce
 *   motion" on a device that allows motion, nothing moves at all along
 *   both rounds: no CSS or Web Animation that moves, no spring, no view
 *   transition, no 3D.
 *
 * 60 frames a second on a real phone is not measured here (headless
 * Chromium on a server, SwiftShader): that needs a device run.
 */

import type { Page } from "@playwright/test";

import { uniqueSuffix } from "./support/api";
import { signInAsDemoOwner, visitorAsksForPerson } from "./support/demo";
import { expect, signInContext, test } from "./support/fixtures";
import { en } from "./support/messages";
import {
  readMotionBudget,
  recordMotionBudget,
  startMeasuring,
  throttleCpu,
  waitForMainThreadQuiet,
  type MotionBudgetReading,
} from "./support/motionBudget";
import { waitForNetworkQuiet } from "./support/network";

test.describe.configure({ timeout: 240_000 });
test.use({
  viewport: { width: 390, height: 844 },
  isMobile: true,
  hasTouch: true,
  // The trace keeps what it keeps on a failure, except DOM snapshots and the screencast: those are
  // taken in the page at every tap, and a timed round would count them as the page's own work.
  trace: { mode: "retain-on-failure", snapshots: false, screenshots: false },
});

/** Web Vitals' "good" interaction to next paint. */
const INP_BUDGET_MS = 200;
/** Lighthouse's mobile profile: a mid-range phone runs about four times slower than a desktop. */
const PHONE_CPU_SLOWDOWN = 4;
/** Timed rounds; their median is the budget's INP (Lighthouse CI also takes three runs). */
const TIMED_ROUNDS = 3;

/** Signs in as the demo owner with someone waiting in the inbox; returns the business id. */
async function demoVisit(page: Page, request: Parameters<typeof signInAsDemoOwner>[0]): Promise<string> {
  const owner = await signInAsDemoOwner(request);
  await signInContext(page.context(), owner.token);
  await visitorAsksForPerson(request, owner.businessId, `Motion budget visitor ${uniqueSuffix()}`);
  return owner.businessId;
}

async function settle(page: Page): Promise<void> {
  await waitForNetworkQuiet(page);
  await waitForMainThreadQuiet(page);
}

/** A person looks at what a tap brought before the next one: its data has come and the page has finished rendering it. */
async function look(page: Page): Promise<void> {
  await waitForNetworkQuiet(page);
  await waitForMainThreadQuiet(page, { quietMs: 500 });
}

/** One round by taps, from the Overview back to it (one document: one recording). */
async function round(page: Page): Promise<void> {
  const periods = page.getByRole("group", { name: en.dashboard.periodLabel });
  for (const period of ["30d", "7d", "today"] as const) {
    await periods.getByText(en.dashboard.periods[period], { exact: true }).tap();
    await expect(page.getByRole("radio", { name: en.dashboard.periods[period] })).toBeChecked();
    await look(page);
  }

  const tabBar = page.getByRole("navigation", { name: en.navigation.tabBar });
  // The link's name carries the badge too (", 3 waiting Inbox").
  await tabBar.getByRole("link", { name: new RegExp(en.navigation.tabLabels.inbox) }).tap();
  const rows = page.locator("[data-inbox-row]");
  await expect(rows.first()).toBeVisible();
  await look(page);
  for (const view of ["requests", "needs_person"] as const) {
    await page.locator(`[data-inbox-view="${view}"]`).tap();
    await expect(page.locator(`[data-inbox-view="${view}"] input`)).toBeChecked();
    await look(page);
  }
  await expect(rows.first()).toBeVisible();

  await tabBar.getByRole("button", { name: en.navigation.more }).tap();
  const more = page.getByRole("dialog", { name: en.navigation.more });
  await expect(more).toBeVisible();
  await look(page);
  await page.keyboard.press("Escape");
  await expect(more).toBeHidden();
  await look(page);

  // The conversation takes the whole screen on a phone (no tab bar).
  await rows.first().locator("a[href]").first().tap();
  await expect(page.locator("#conversation-title")).toBeVisible();
  await look(page);
  await page.getByRole("link", { name: en.inboxCard.back }).tap();
  await expect(rows.first()).toBeVisible();
  await look(page);

  await tabBar.getByRole("link", { name: en.navigation.sections.overview }).tap();
  await expect(periods).toBeVisible();
  await look(page);
}

/** Opens the Overview and goes round once: everything is fetched (and, with full motion, the motion is seen). */
async function firstRound(page: Page, businessId: string): Promise<void> {
  await page.goto(`/b/${businessId}/overview`);
  await settle(page);
  await round(page);
  await settle(page);
}

/**
 * Goes round again `rounds` times and reads each round's own interactions
 * and layout shifts. Timed rounds (`timed`) stop the motion watch first:
 * its observers would weigh on the very taps they time; what moved in the
 * first round stays recorded.
 */
async function measuredRounds(page: Page, rounds: number, { timed = false } = {}): Promise<MotionBudgetReading[]> {
  const readings: MotionBudgetReading[] = [];
  for (let index = 0; index < rounds; index += 1) {
    await startMeasuring(page, { watchMotion: !timed });
    await round(page);
    await settle(page);
    readings.push(await readMotionBudget(page));
  }
  return readings;
}

/** The middle value: one round slowed by a busy machine does not decide, as with Lighthouse's three runs. */
function median(values: readonly number[]): number {
  const sorted = [...values].sort((first, second) => first - second);
  return sorted[Math.floor(sorted.length / 2)] ?? 0;
}

test.describe("with full motion", () => {
  test.use({ contextOptions: { reducedMotion: "no-preference" } });

  test("on a phone four times slower every tap paints within 200 ms, nothing shifts, and the motion is there", async ({
    page,
    request,
  }) => {
    const businessId = await demoVisit(page, request);
    await recordMotionBudget(page);

    await firstRound(page, businessId);
    await throttleCpu(page, PHONE_CPU_SLOWDOWN);
    const readings = await measuredRounds(page, TIMED_ROUNDS, { timed: true });
    const inp = median(readings.map((reading) => reading.inp));
    const rounds = readings.map((reading) => `${Math.round(reading.inp)} ms (${reading.slowest})`).join("; ");

    for (const reading of readings) {
      expect(reading.interactions, "the taps were measured").toBeGreaterThanOrEqual(9);
    }
    expect(inp, `INP, the median of the rounds: ${rounds}`).toBeLessThan(INP_BUDGET_MS);
    expect(readings.flatMap((reading) => reading.shifts), "layout shifts (CLS)").toEqual([]);
    const last = readings[readings.length - 1];
    expect(last?.moved.length, "things move with full motion").toBeGreaterThan(0);
    expect(last?.viewTransitions, "the row's customer morphs into the conversation header").toBeGreaterThan(0);
  });
});

/** Nothing moved along the visit (no animation that moves, no view transition, no 3D), and nothing shifted in the measured round. */
async function expectStillness(page: Page): Promise<void> {
  const reading = await readMotionBudget(page);
  expect(reading.moved, "what moved").toEqual([]);
  expect(reading.viewTransitions, "view transitions").toBe(0);
  expect(reading.canvases, "3D canvases").toBe(0);
  expect(reading.shifts, "layout shifts (CLS)").toEqual([]);
}

test("with the device's reduced motion nothing moves", async ({ page, request }) => {
  const businessId = await demoVisit(page, request);
  await recordMotionBudget(page);

  await firstRound(page, businessId);
  await measuredRounds(page, 1);
  await expectStillness(page);
});

test.describe("with the cabinet's own Reduce motion", () => {
  test.use({ contextOptions: { reducedMotion: "no-preference" } });

  test("set in More, it stills the page at once and on every later visit, though the device allows motion", async ({
    page,
    request,
  }) => {
    const businessId = await demoVisit(page, request);
    await page.goto(`/b/${businessId}/overview`);
    await page.getByRole("button", { name: en.navigation.more }).tap();
    const more = page.getByRole("dialog", { name: en.navigation.more });
    await more.getByRole("checkbox", { name: new RegExp(`^${en.account.motion}`) }).check();
    await expect(page.locator("html")).toHaveAttribute("data-motion", "reduce");
    await page.keyboard.press("Escape");
    await expect(more).toBeHidden();

    // A new visit: the server renders the setting from the cookie, so the first paint is already still.
    await recordMotionBudget(page);
    await firstRound(page, businessId);
    await measuredRounds(page, 1);
    await expect(page.locator("html")).toHaveAttribute("data-motion", "reduce");
    await expectStillness(page);
    expect((await page.context().cookies()).find((cookie) => cookie.name === "aw_motion")?.value).toBe("reduce");
  });
});
