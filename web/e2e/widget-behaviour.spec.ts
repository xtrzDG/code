/**
 * The website chat widget (assembled by the API from
 * app/gateways/http/static/widget/) on a host site, against a fake widget
 * API: polling, page changes, several tabs, screen readers and text
 * direction. The script is the one the real API serves at /widget.js, as it
 * is; everything else is faked (support/widget-site.ts).
 */

import { expect, test } from "./support/fixtures";
import { FakeWidgetApi, SITE, STORAGE_PREFIX, ask, chat, chatTexts, loadWidgetSource, serveSite } from "./support/widget-site";

test.beforeAll(async () => {
  await loadWidgetSource();
});

test("an open chat shows a staff message written without a handoff", async ({ page }) => {
  const api = new FakeWidgetApi();
  await page.clock.install();
  await serveSite(page.context(), api, { dataOpen: true });
  await page.goto(`${SITE}/`);

  await ask(page, "Is the terrace open?");
  await expect(chat(page).getByText("Answer to Is the terrace open?")).toBeVisible();
  api.add("staff", "Correction: the terrace opens at 18:00.");
  // The widget schedules its next poll after it has drawn the answer, so a
  // single jump can land before that timer exists. Keep moving the clock
  // until the staff message arrives.
  await expect(async () => {
    await page.clock.fastForward(15_000);
    await expect(chat(page).getByText("Correction: the terrace opens at 18:00.")).toBeVisible({ timeout: 1_000 });
  }).toPass({ timeout: 30_000 });
  // The visitor key travels in a header, never in the URL.
  expect(api.polls.length).toBeGreaterThan(1);
  for (const poll of api.polls) {
    expect(poll.url).not.toContain("session_key");
    expect(poll.sessionKey).toMatch(/^v1_/);
  }
});

test("a message refused as too fast can be retried once the API's wait is over", async ({ page, consoleErrors }) => {
  consoleErrors.allow(/status of 429/);
  const api = new FakeWidgetApi();
  api.refusePostsFor = 8;
  await page.clock.install();
  await serveSite(page.context(), api, { dataOpen: true });
  await page.goto(`${SITE}/`);

  await ask(page, "Table for two?");

  await expect(chat(page).getByText("Too many messages. Please wait a moment and try again.")).toBeVisible();
  const retry = chat(page).getByRole("button", { name: "Retry" });
  await expect(retry).toBeDisabled();
  await page.getByRole("textbox").fill("Hello?");
  await expect(chat(page).getByRole("button", { name: "Send" })).toBeDisabled();
  expect(api.messages).toEqual([]);

  api.refusePostsFor = null;
  await page.clock.runFor(8_100);
  await expect(retry).toBeEnabled();
  await expect(chat(page).getByRole("button", { name: "Send" })).toBeEnabled();
  await retry.click();

  await expect(chat(page).getByText("Answer to Table for two?")).toBeVisible();
  await expect(chat(page).getByText("Too many messages. Please wait a moment and try again.")).toBeHidden();
});

test("a closed chat without any exchange does not poll", async ({ page }) => {
  const api = new FakeWidgetApi();
  await page.clock.install();
  await serveSite(page.context(), api);
  await page.goto(`${SITE}/`);
  await expect(page.getByRole("button", { name: "Open chat" })).toBeVisible();

  await page.clock.fastForward(120_000);

  expect(api.polls).toEqual([]);
});

test("closing the chat keeps it closed on the next page despite data-open", async ({ page }) => {
  const api = new FakeWidgetApi();
  await serveSite(page.context(), api, { dataOpen: true });
  await page.goto(`${SITE}/`);
  await expect(page.getByRole("textbox")).toBeVisible();

  await page.getByRole("button", { name: "Close chat", expanded: true }).click();
  await page.getByRole("link", { name: "Next page" }).click();

  await expect(page.getByRole("heading", { name: "Shop page /next" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Open chat", expanded: false })).toBeVisible();
  await expect(page.getByRole("textbox")).toBeHidden();
});

test("a reply to a closed chat is announced and named on the launcher", async ({ page }) => {
  const api = new FakeWidgetApi();
  const question = api.add("customer", "Can I talk to someone?");
  api.add("staff", "Hi, this is Anna");
  api.isHandedOff = true;
  await page.addInitScript(
    ({ prefix, cursor }) => {
      window.localStorage.setItem(`${prefix}handoff`, "1");
      window.localStorage.setItem(`${prefix}cursor`, cursor);
    },
    { prefix: STORAGE_PREFIX, cursor: question.id },
  );
  await serveSite(page.context(), api);
  await page.goto(`${SITE}/`);

  await expect(page.getByRole("button", { name: "Open chat (New reply)", expanded: false })).toBeVisible();
  await expect(page.getByRole("status")).toHaveText("New reply");

  await page.getByRole("button", { name: "Open chat (New reply)" }).click();
  await expect(chat(page).getByText("Hi, this is Anna")).toBeVisible();
  await page.getByRole("button", { name: "Close chat", expanded: true }).click();
  await expect(page.getByRole("button", { name: "Open chat", exact: true })).toBeVisible();
});

test("an answer written after the visitor left the page appears on the next page", async ({ page }) => {
  const api = new FakeWidgetApi();
  api.holdPosts = true;
  await page.clock.install();
  await serveSite(page.context(), api, { dataOpen: true });
  await page.goto(`${SITE}/`);

  await ask(page, "Do you deliver to Batumi?");
  await expect.poll(() => api.messages.length).toBe(2);
  await page.getByRole("link", { name: "Next page" }).click();
  await expect(page.getByRole("heading", { name: "Shop page /next" })).toBeVisible();
  await expect(chat(page).getByText("Do you deliver to Batumi?")).toBeVisible();

  // The new page asks for its position, then for what came after it.
  await expect(async () => {
    await page.clock.fastForward(5_000);
    await expect(chat(page).getByText("Answer to Do you deliver to Batumi?")).toBeVisible({ timeout: 500 });
  }).toPass({ timeout: 20_000 });
  expect((await chatTexts(page)).slice(1)).toEqual(["Do you deliver to Batumi?", "Answer to Do you deliver to Batumi?"]);
});

test("two tabs keep one ordered chat history", async ({ context }) => {
  const api = new FakeWidgetApi();
  await serveSite(context, api, { dataOpen: true });
  const first = await context.newPage();
  const second = await context.newPage();
  await first.goto(`${SITE}/`);
  await second.goto(`${SITE}/`);

  await ask(first, "parking");
  await expect(chat(first).getByText("Answer to parking")).toBeVisible();
  await ask(second, "hours");
  await expect(chat(second).getByText("Answer to hours")).toBeVisible();
  const third = await context.newPage();
  await third.goto(`${SITE}/`);

  await expect(chat(third).getByText("Answer to hours")).toBeVisible();
  expect((await chatTexts(third)).slice(1)).toEqual(["parking", "Answer to parking", "hours", "Answer to hours"]);
});

test("business messages marked right-to-left stay right-to-left", async ({ page }) => {
  const api = new FakeWidgetApi();
  await page.addInitScript((prefix) => {
    window.localStorage.setItem(
      `${prefix}history`,
      JSON.stringify([
        { role: "visitor", text: "iPhone شاشة مكسورة" },
        { role: "assistant", id: "m1", text: "Pizza Roma مفتوح يوميًا من 10:00 إلى 22:00.", direction: "rtl" },
        { role: "staff", id: "m2", text: "Hello, I will check that for you.", direction: "rtl" },
        { role: "staff", id: "m3", text: "+995 555 12 34 56", direction: "rtl" },
      ]),
    );
  }, STORAGE_PREFIX);
  await serveSite(page.context(), api, { dataOpen: true });
  await page.goto(`${SITE}/`);

  await expect(chat(page).getByText("Pizza Roma", { exact: false })).toHaveAttribute("dir", "rtl");
  await expect(chat(page).getByText("Hello, I will check that for you.")).toHaveAttribute("dir", "auto");
  await expect(chat(page).getByText("+995 555 12 34 56")).toHaveAttribute("dir", "auto");
  await expect(chat(page).getByText("iPhone شاشة مكسورة")).toHaveAttribute("dir", "auto");
});
