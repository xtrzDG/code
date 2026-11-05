/**
 * The website chat's live stream and its deadline, against a fake widget
 * API (support/widget-site.ts) and the script the real API serves:
 *
 * - with a stream ticket the widget opens GET …/events?ticket=… (the
 *   visitor key never rides in a URL), shows the answer the moment the
 *   stream carries it and lets the stored text replace that draft;
 * - an answer that never comes ends in "We'll answer as soon as we can"
 *   and a handoff with the reason no_answer, not in dots that vanish.
 */

import { expect, test } from "./support/fixtures";
import { FakeWidgetApi, SITE, STREAM_TICKET, ask, chat, loadWidgetSource, serveSite } from "./support/widget-site";

test.beforeAll(async () => {
  await loadWidgetSource();
});

test("the live stream shows the answer at once and the stored text replaces its draft", async ({ page }) => {
  const api = new FakeWidgetApi();
  api.streamTickets = true;
  api.holdAnswers = true;
  await serveSite(page.context(), api, { dataOpen: true });
  await page.goto(`${SITE}/`);

  await ask(page, "A table for two at eight?");
  await expect.poll(() => api.streamRequests.length, { timeout: 10_000 }).toBeGreaterThan(0);

  // The worker claims the message, then the answer is stored; polls do not
  // show it yet, only the stream does (a guard-cleared draft).
  const stored = api.add("assistant", "Yes, we have a table for two at 20:00.");
  api.hiddenIds.add(stored.id);
  api.pushEvent("typing_started", {});
  api.pushEvent("answer_ready", { message_id: stored.id, author: "assistant", direction: "ltr", text: "Yes, a table for two at 8 pm." });

  await expect(chat(page).getByText("Yes, a table for two at 8 pm.")).toBeVisible({ timeout: 10_000 });
  await expect(chat(page).locator(".aw-typing")).toHaveCount(0);

  api.hiddenIds.delete(stored.id);
  await expect(chat(page).getByText("Yes, we have a table for two at 20:00.")).toBeVisible({ timeout: 10_000 });
  await expect(chat(page).getByText("Yes, a table for two at 8 pm.")).toHaveCount(0);

  const sessionKey = api.sessionKeys[0] ?? "";
  expect(sessionKey).toMatch(/^v1_/);
  for (const url of api.streamRequests) {
    expect(new URL(url).searchParams.get("ticket")).toBe(STREAM_TICKET);
    expect(url).not.toContain(sessionKey);
    expect(url).not.toContain("session_key");
  }
});

test("without a ticket the widget polls as before", async ({ page }) => {
  const api = new FakeWidgetApi();
  await serveSite(page.context(), api, { dataOpen: true });
  await page.goto(`${SITE}/`);

  await ask(page, "Is there parking?");

  await expect(chat(page).getByText("Answer to Is there parking?")).toBeVisible();
  expect(api.streamRequests).toEqual([]);
  expect(api.polls.length).toBeGreaterThan(0);
});

test("an answer that never comes is handed to the team with a word for the visitor", async ({ page }) => {
  const api = new FakeWidgetApi();
  api.holdAnswers = true;
  await page.clock.install();
  await serveSite(page.context(), api, { dataOpen: true });
  await page.goto(`${SITE}/`);

  await ask(page, "Can I bring my dog?");
  await expect(chat(page).locator(".aw-typing")).toBeVisible();

  await expect(async () => {
    await page.clock.fastForward(30_000);
    await expect(chat(page).getByText("We'll answer as soon as we can.")).toBeVisible({ timeout: 1_000 });
  }).toPass({ timeout: 30_000 });

  await expect(chat(page).locator(".aw-typing")).toHaveCount(0);
  await expect.poll(() => api.handoffs.length).toBe(1);
  expect(api.handoffs[0]?.reason).toBe("no_answer");
  // The team's own notice (stored by the API) is not shown twice.
  await expect(chat(page).getByText("A person from our team will answer here.")).toHaveCount(0);
});
