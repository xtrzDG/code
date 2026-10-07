/**
 * What the assistant is worth: the owner's value hero and change chips on
 * the dashboard (the demo restaurant is live with a month of activity),
 * Overview → Reports (the month so far, the average check edited in place,
 * the owner's summaries, a stored report opened from a digest's link), a
 * staff member's queue of the day without the reports, the reply guard's
 * verdicts the demo really stored, topics in the cabinet's language, and
 * day 0 of a business launched through the tunnel minutes ago.
 */

import type { APIRequestContext } from "@playwright/test";

import { API_URL, WEB_URL } from "./support/env";
import { expect, signInContext, test } from "./support/fixtures";
import { signInAsPlatformAdmin } from "./support/admin";
import { DEMO_OWNER_EMAIL, signInAsDemoOwner } from "./support/demo";
import { waitingConversationOf } from "./support/inbox";
import { apiLogSize, waitForLoginCode } from "./support/login-codes";
import { en, ka, ru } from "./support/messages";
import {
  answerBusiness,
  answerChannels,
  answerHours,
  answerOffer,
  answerPeople,
  answerPlace,
  answerTry,
  expectStep,
} from "./support/tunnel";

const DEMO_RESTAURANT = "Mtsvane Ezo";
/** An address may ask for a login code every 30 seconds (live.spec.ts signs the demo owner in too). */
const LOGIN_CODE_COOLDOWN_MS = 31_000;

test.describe.configure({ timeout: 120_000 });

/**
 * Signs a demo account in, waiting out the code cooldown once if another
 * spec just asked; the demo owner's sign-in is the worker's shared one.
 */
async function signInDemo(request: APIRequestContext, email: string): Promise<{ token: string; businessId: string }> {
  if (email === DEMO_OWNER_EMAIL) {
    return signInAsDemoOwner(request);
  }
  let since = apiLogSize();
  let start = await request.post(`${API_URL}/v1/auth/otp/start`, { data: { email, locale: "en" } });
  if (start.status() === 429) {
    await new Promise((resolve) => setTimeout(resolve, LOGIN_CODE_COOLDOWN_MS));
    since = apiLogSize();
    start = await request.post(`${API_URL}/v1/auth/otp/start`, { data: { email, locale: "en" } });
  }
  expect(start.status(), await start.text()).toBe(200);
  const { challenge_id: challengeId } = (await start.json()) as { challenge_id: string };
  const code = await waitForLoginCode({ since });
  const verify = await request.post(`${API_URL}/v1/auth/otp/verify`, { data: { challenge_id: challengeId, code } });
  expect(verify.status(), await verify.text()).toBe(200);
  const token = ((await verify.json()) as { access_token: string }).access_token;
  const businesses = await request.get(`${API_URL}/v1/businesses`, { headers: { authorization: `Bearer ${token}` } });
  const restaurant = ((await businesses.json()) as { id: string; name: string }[]).find((business) => business.name === DEMO_RESTAURANT);
  expect(restaurant, "the demo restaurant is seeded").toBeDefined();
  return { token, businessId: restaurant!.id };
}

test("the owner sees what the assistant is worth, with changes against the period before", async ({ page, context, request }) => {
  const owner = await signInDemo(request, "demo@example.com");
  await signInContext(context, owner.token);
  await page.goto(`/b/${owner.businessId}/overview`);

  const hero = page.getByRole("region", { name: new RegExp(en.value.hero.title) });
  await expect(hero).toBeVisible();
  await expect(hero.getByText(en.value.hero.bookingsLabel)).toBeVisible();
  // The money estimate: the assistant's bookings times the typical check of a restaurant.
  await expect(hero.getByText(/^≈ GEL/)).toBeVisible();
  await expect(hero.getByText(/Average check GEL\s?120, typical for your kind of business/)).toBeVisible();
  // Every chip says in words how the number moved (or the card says once that the period before had nothing).
  const moved = new RegExp(`^(Up .+ vs the previous 30 days|${en.value.delta.firstPeriodNote})$`);
  await expect(page.getByText(moved).first()).toBeAttached();

  // A digest's link opens the report it is about.
  const listed = await request.get(`${API_URL}/v1/businesses/${owner.businessId}/value-reports?kind=monthly`, {
    headers: { authorization: `Bearer ${owner.token}` },
  });
  const reports = ((await listed.json()) as { items: { id: string }[] }).items;
  await hero.getByRole("link", { name: en.value.hero.reports }).click();
  await expect(page).toHaveURL(new RegExp(`/b/${owner.businessId}/overview/reports$`));
  await expect(page.getByRole("region", { name: new RegExp(en.reports.monthSoFar.title) })).toBeVisible();
  if (reports.length > 0) {
    await page.goto(`/b/${owner.businessId}/overview/reports?report=${reports[0]!.id}`);
    const opened = page.getByRole("region", { name: en.reports.opened });
    // Unfolded: every number against the period before (a table on a desktop).
    await expect(opened.getByRole("rowheader", { name: en.reports.rows.assistantBookings })).toBeVisible();
  }
});

test("against a period without any activity, each card says 'first period' once instead of growth", async ({ page, context, request }) => {
  const owner = await signInDemo(request, "demo@example.com");
  await signInContext(context, owner.token);
  // The period before had nothing at all: no conversation, booking, request, handoff or call.
  await page.route(/\/api\/backend\/v1\/businesses\/[^/]+\/value(\?|$)/, async (route) => {
    const response = await route.fetch();
    const model = (await response.json()) as { previous: Record<string, number | null> };
    const quiet = Object.fromEntries(Object.keys(model.previous).map((key) => [key, 0]));
    await route.fulfill({ response, json: { ...model, previous: quiet } });
  });
  await page.goto(`/b/${owner.businessId}/overview`);

  const hero = page.getByRole("region", { name: new RegExp(en.value.hero.title) });
  // One note for the hero and one for the statistics, not a chip on every number.
  await expect(hero.getByText(en.value.delta.firstPeriodNote)).toHaveCount(1);
  await expect(page.getByText(en.value.delta.firstPeriodNote)).toHaveCount(2);
  await expect(page.getByText(en.value.delta.firstPeriod, { exact: true })).toHaveCount(0);
  // No total is presented as growth ("+41", "+1 920 GEL").
  await expect(page.getByText(/^Up .+ vs the previous/)).toHaveCount(0);
  await expect(hero.getByText(/^▲ \+/)).toHaveCount(0);
});

test("the owner sets the average check and chooses the summaries", async ({ page, owner, request }) => {
  await page.goto(`/b/${owner.businessId}/overview`);
  await page.getByRole("navigation", { name: /Overview/ }).getByRole("link", { name: en.navigation.pages.overviewReports }).click();
  await expect(page).toHaveURL(new RegExp(`/b/${owner.businessId}/overview/reports$`));

  const month = page.getByRole("region", { name: new RegExp(en.reports.monthSoFar.title) });
  // A Berlin salon starts from the typical check of beauty salons.
  await expect(month.getByText(/Average check €30, typical for your kind of business/)).toBeVisible();
  await month.getByRole("button", { name: en.value.check.change }).click();
  await month.getByLabel("Average check, EUR").fill("0");
  await month.getByRole("button", { name: en.common.save }).click();
  await expect(month.getByText(en.value.check.positive)).toBeVisible();
  await month.getByLabel("Average check, EUR").fill("45");
  await month.getByRole("button", { name: en.common.save }).click();
  await expect(month.getByText("Average check €45")).toBeVisible();

  const stored = await request.get(`${API_URL}/v1/businesses/${owner.businessId}/value/settings`, {
    headers: { authorization: `Bearer ${owner.token}` },
  });
  expect(((await stored.json()) as { average_check_minor: number }).average_check_minor).toBe(4500);

  // Summaries: the monthly report and the weekly digest are on, the daily one is off.
  const daily = page.getByRole("switch", { name: en.reports.digests.daily });
  await expect(page.getByRole("switch", { name: en.reports.digests.monthly })).toHaveAttribute("aria-checked", "true");
  await expect(daily).toHaveAttribute("aria-checked", "false");
  await daily.click();
  await expect(daily).toHaveAttribute("aria-checked", "true");
  await page.reload();
  await expect(page.getByRole("switch", { name: en.reports.digests.daily })).toHaveAttribute("aria-checked", "true");
  await expect(page.getByText(en.reports.empty.title)).toBeVisible();
});

test("staff see their queue of the day and not the reports", async ({ page, context, request }) => {
  const staff = await signInDemo(request, "staff.demo@example.com");
  await signInContext(context, staff.token);
  await page.goto(`/b/${staff.businessId}/overview`);

  await expect(page.getByRole("heading", { name: en.value.queue.title })).toBeVisible();
  await expect(page.getByRole("link", { name: new RegExp(en.value.queue.bookings) })).toBeVisible();
  await expect(page.getByRole("region", { name: new RegExp(en.value.hero.title) })).toHaveCount(0);
  await expect(page.getByRole("navigation", { name: /Overview/ })).toHaveCount(0);

  await page.goto(`/b/${staff.businessId}/overview/reports`);
  await expect(page.getByRole("heading", { name: en.navigation.ownerOnlyTitle })).toBeVisible();
});

test("the demo's guard verdicts are the stored ones: Lukas Weber's reply was held back", async ({ page, context, request }) => {
  const owner = await signInDemo(request, "demo@example.com");
  await signInContext(context, owner.token);
  const lukas = await waitingConversationOf(request, owner.token, owner.businessId, "Lukas Weber");
  await page.goto(`/b/${owner.businessId}/inbox/${lukas}`);

  // No route stands in for the API: the chip reads the verdict seeding stored.
  const chip = page.getByRole("note", { name: en.teaching.guard.label });
  await expect(chip.getByText(en.teaching.guard.handed_off)).toBeVisible();
  await expect(chip.getByText(en.teaching.guard.reasons.unverified_values)).toBeVisible();
});

test("topics read in the cabinet's language, the catch-all from its dictionary", async ({ page, context, request }) => {
  const owner = await signInDemo(request, "demo@example.com");
  await signInContext(context, owner.token);
  for (const [locale, messages] of [["en", en], ["ka", ka]] as const) {
    await context.addCookies([{ name: "aw_locale", value: locale, url: WEB_URL, sameSite: "Lax" }]);
    await page.goto(`/b/${owner.businessId}/overview`);
    const card = page.getByRole("region", { name: messages.topics.title });
    await expect(card.locator("[data-topic-kind]").first()).toBeVisible();
    // The Russian owner's restaurant: no Russian label on an English or Georgian cabinet.
    expect(await card.locator("[data-topic-kind]").allInnerTexts()).not.toContainEqual(expect.stringMatching(/[А-Яа-яЁё]/));
    await expect(card.locator('[data-topic-kind="other"]').first()).toHaveText(messages.topics.otherTopic);
  }
});

const escapeRegExp = (text: string) => text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

/** Platform support, who switches the test business on without the launch's full checks. */
const LAUNCH_ADMIN_EMAIL = "launch-admin@e2e.workshop.example";

/**
 * Goes live the short way: the owner accepts the agreement, builds the
 * assistant and lets support make changes; support opens the cabinet with
 * a reason and switches the assistant on without the launch's full checks
 * on the rehearsal model (setup-tunnel.spec.ts and apply-changes.spec.ts
 * walk the launch itself). Going live starts the free trial.
 */
async function goLive(request: APIRequestContext, ownerToken: string, businessId: string): Promise<void> {
  const owner = { authorization: `Bearer ${ownerToken}` };
  const base = `${API_URL}/v1/businesses/${businessId}`;
  const agreed = await request.post(`${base}/dpa`, { headers: owner });
  expect(agreed.status(), await agreed.text()).toBe(201);
  const built = await request.post(`${base}/assistant-versions`, { data: { run_autotests: false }, headers: owner });
  expect(built.ok(), await built.text()).toBe(true);
  const versionId = ((await built.json()) as { id: string }).id;
  const support = { authorization: `Bearer ${await signInAsPlatformAdmin(request, LAUNCH_ADMIN_EMAIL)}` };
  const opened = await request.post(`${API_URL}/v1/admin/clients/${businessId}/open`, {
    data: { reason: "Switch the test assistant on" },
    headers: support,
  });
  expect(opened.ok(), await opened.text()).toBe(true);
  const allowed = await request.put(`${base}/support-access/write-access`, { data: { is_allowed: true, hours: 1 }, headers: owner });
  expect(allowed.ok(), await allowed.text()).toBe(true);
  const published = await request.post(`${base}/assistant-versions/${versionId}/publish`, {
    data: { accept_failed_tests: true },
    headers: support,
  });
  expect(published.ok(), await published.text()).toBe(true);
}

test("a business launched minutes ago reads 'ready', counted since its launch, in ru, en and ka", async ({ page, account, request }) => {
  test.setTimeout(240_000);
  await page.goto("/create");
  await answerBusiness(page, "Salon Erste Stunde");
  const businessId = await answerPlace(page);
  await answerOffer(page);
  await answerHours(page);
  await answerPeople(page, account.email);
  await answerChannels(page);
  await answerTry(page);
  await expectStep(page, en.tunnelLaunch.launch.title);
  await goLive(request, account.token, businessId);

  for (const messages of [ru, en, ka]) {
    const locale = messages === ru ? "ru" : messages === en ? "en" : "ka";
    await page.context().addCookies([{ name: "aw_locale", value: locale, url: WEB_URL, sameSite: "Lax" }]);
    await page.goto(`/b/${businessId}/overview`);
    const ready = page.getByRole("region", { name: new RegExp(messages.value.ready.title) });
    await expect(ready.getByText(messages.value.ready.lead)).toBeVisible();
    // Since today, never a 30-day range from before the business existed.
    const [before, after] = messages.value.hero.since.split("{date}");
    const sinceLaunch = ready.getByText(new RegExp(`^${escapeRegExp(before ?? "")}[^–]+${escapeRegExp(after ?? "")}$`)).first();
    await expect(sinceLaunch).toBeVisible();
    await expect(page.getByText(messages.dashboard.periodSince.split("{date}")[0]!).first()).toBeVisible();
    // The free trial costs nothing: no "≈ 0.0×" and no plan price for these days.
    await expect(ready.getByText(messages.value.hero.trialUntil.split("{date}")[0]!)).toBeVisible();
    await expect(page.getByText(/0[.,]0\s*×/)).toHaveCount(0);
    await expect(page.getByText(messages.value.hero.returnHint.split("{price}")[0]!)).toHaveCount(0);
    // A sample, labelled as one, and the chat page to try the assistant.
    await expect(ready.getByText(messages.value.ready.sampleLabel, { exact: true })).toBeVisible();
    await expect(ready.getByRole("img", { name: new RegExp(messages.value.ready.qrAlt.split("{link}")[0]!) })).toBeVisible();
    // The statistics wait for the first conversation in one card.
    await expect(page.getByText(messages.dashboard.statsEmptyTitle)).toBeVisible();
  }
});
