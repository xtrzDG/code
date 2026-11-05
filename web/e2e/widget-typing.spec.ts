/**
 * The website chat widget answers asynchronously: the API accepts a message
 * at once (202) and a worker writes the answer. The widget keeps the typing
 * dots on while it polls, and takes them off when the answer (or a person)
 * arrives. The script is the one the real API serves; the API is faked
 * (support/widget-site.ts).
 */

import type { Page } from "@playwright/test";

import { expect, test } from "./support/fixtures";
import { FakeWidgetApi, SITE, ask, chat, chatTexts, loadWidgetSource, serveSite } from "./support/widget-site";

test.beforeAll(async () => {
  await loadWidgetSource();
});

function typingDots(page: Page) {
  return chat(page).locator(".aw-typing");
}

test("the typing dots stay until the worker's answer arrives", async ({ page }) => {
  const api = new FakeWidgetApi();
  api.holdAnswers = true;
  await serveSite(page.context(), api, { dataOpen: true });
  await page.goto(`${SITE}/`);

  await ask(page, "Do you have a table for four tonight?");

  await expect(typingDots(page)).toBeVisible();
  await expect(page.getByRole("status")).toHaveText("The assistant is typing…");
  // The widget keeps asking while the answer is being written.
  await expect.poll(() => api.polls.length, { timeout: 10_000 }).toBeGreaterThan(2);
  await expect(typingDots(page)).toBeVisible();
  // The visitor's own message is shown as sent, not as still on its way.
  await expect(chat(page).locator(".aw-pending")).toHaveCount(0);

  api.releaseAnswers();

  await expect(chat(page).getByText("Answer to Do you have a table for four tonight?")).toBeVisible();
  await expect(typingDots(page)).toHaveCount(0);
  expect((await chatTexts(page)).slice(1)).toEqual([
    "Do you have a table for four tonight?",
    "Answer to Do you have a table for four tonight?",
  ]);
});

test("the answer of a first visit comes within seconds of the worker writing it", async ({ page }) => {
  const api = new FakeWidgetApi();
  await serveSite(page.context(), api, { dataOpen: true });
  await page.goto(`${SITE}/`);

  const asked = Date.now();
  await ask(page, "Is there parking?");

  await expect(chat(page).getByText("Answer to Is there parking?")).toBeVisible();
  // A new visitor has no position yet: one poll finds it, the next the answer.
  expect(Date.now() - asked).toBeLessThan(4_000);
  await expect(typingDots(page)).toHaveCount(0);
});

test("when staff own the conversation the dots give way to them", async ({ page }) => {
  const api = new FakeWidgetApi();
  api.holdAnswers = true;
  api.isHandedOff = true;
  await serveSite(page.context(), api, { dataOpen: true });
  await page.goto(`${SITE}/`);

  await ask(page, "Can I bring my dog?");

  // The assistant stays silent while staff handle the chat: no dots.
  await expect(typingDots(page)).toHaveCount(0, { timeout: 10_000 });
  api.add("staff", "Of course, dogs are welcome on the terrace.");
  await expect(chat(page).getByText("Of course, dogs are welcome on the terrace.")).toBeVisible({ timeout: 15_000 });
});
