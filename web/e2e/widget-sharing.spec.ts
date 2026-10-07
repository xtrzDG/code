/**
 * The website chat widget's newer parts on a host site, against the fake
 * widget API (support/widget-site.ts): starter questions from the FAQ,
 * "Talk to a person", "New conversation" (a new visitor key) and the
 * "AI assistant · can make mistakes · Privacy" footer.
 */

import { expect, test } from "./support/fixtures";
import { FakeWidgetApi, SITE, STORAGE_PREFIX, ask, chat, chatTexts, loadWidgetSource, serveSite } from "./support/widget-site";

const PRIVACY_URL = "https://app.workshop.example/c/cafe-batumi/privacy";

function apiWithStarters(): FakeWidgetApi {
  const api = new FakeWidgetApi();
  api.configExtras = {
    starter_questions: [
      { language: "en", text: "Do you have parking?" },
      { language: "en", text: "Can I bring children?" },
      { language: "ka", text: "გაქვთ პარკინგი?" },
    ],
    privacy_url: PRIVACY_URL,
  };
  return api;
}

test.beforeAll(async () => {
  await loadWidgetSource();
});

test("starter questions in the visitor's language send with one tap and step aside once they write", async ({ page }) => {
  const api = apiWithStarters();
  await serveSite(page.context(), api, { dataOpen: true });
  await page.goto(`${SITE}/`);

  const starters = chat(page).getByRole("group", { name: "Suggested questions" });
  await expect(starters.getByRole("button")).toHaveText(["Do you have parking?", "Can I bring children?"]);

  await starters.getByRole("button", { name: "Do you have parking?" }).click();

  await expect(chat(page).getByText("Answer to Do you have parking?")).toBeVisible();
  await expect(starters).toBeHidden();
  expect(api.sessionKeys).toHaveLength(1);
});

test("Talk to a person hands the conversation to staff once, in the visitor's language", async ({ page }) => {
  const api = apiWithStarters();
  await serveSite(page.context(), api, { dataOpen: true });
  await page.goto(`${SITE}/`);

  await chat(page).getByRole("button", { name: "Talk to a person" }).click();

  await expect(chat(page).getByText("A person from our team will answer here.")).toBeVisible();
  await expect(chat(page).getByRole("button", { name: "Talk to a person" })).toBeHidden();
  expect(api.handoffs).toEqual([{ session_key: expect.stringMatching(/^v1_/), language: "en" }]);
  // The notice is stored once: a reload shows it a single time.
  await page.reload();
  await expect(chat(page).getByText("A person from our team will answer here.")).toHaveCount(1);
});

test("New conversation asks first, then clears the chat and starts with a new visitor key", async ({ page }) => {
  const api = apiWithStarters();
  await serveSite(page.context(), api, { dataOpen: true });
  await page.goto(`${SITE}/`);
  await ask(page, "Is the terrace open?");
  await expect(chat(page).getByText("Answer to Is the terrace open?")).toBeVisible();

  await chat(page).getByRole("button", { name: "New conversation" }).click();
  await expect(chat(page).getByText("Start a new conversation? This chat will be cleared from this device.")).toBeVisible();
  await chat(page).getByRole("button", { name: "Cancel" }).click();
  await expect(chat(page).getByText("Answer to Is the terrace open?")).toBeVisible();

  await chat(page).getByRole("button", { name: "New conversation" }).click();
  await chat(page).getByRole("button", { name: "Start over" }).click();

  await expect(chat(page).getByText("Answer to Is the terrace open?")).toBeHidden();
  expect(await chatTexts(page)).toHaveLength(1);
  await expect(chat(page).getByRole("group", { name: "Suggested questions" })).toBeVisible();
  await ask(page, "And on Sunday?");
  await expect(chat(page).getByText("Answer to And on Sunday?")).toBeVisible();
  expect(api.sessionKeys).toHaveLength(2);
  expect(api.sessionKeys[1]).not.toBe(api.sessionKeys[0]);
  expect(await page.evaluate((prefix) => localStorage.getItem(`${prefix}session`), STORAGE_PREFIX)).toBe(api.sessionKeys[1]);
});

test("the footer says it is an AI that can make mistakes and links the privacy notice", async ({ page }) => {
  const api = apiWithStarters();
  await serveSite(page.context(), api, { dataOpen: true });
  await page.goto(`${SITE}/`);

  await expect(chat(page).getByText("AI assistant · can make mistakes")).toBeVisible();
  const privacy = chat(page).getByRole("link", { name: "Privacy" });
  await expect(privacy).toHaveAttribute("href", PRIVACY_URL);
  await expect(privacy).toHaveAttribute("target", "_blank");
});
