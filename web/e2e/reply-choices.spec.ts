/**
 * Reply options (offer_choices) in the cabinet. The suite's rehearsal
 * model never offers options, so the first answer gets them in the real
 * API answer on its way to the page (route interception); what the tap
 * sends goes to the real API.
 *
 * - The owner's test chat: the options of the last answer are buttons, a
 *   tap sends the label as the customer's message, and the earlier
 *   options stay under their answer as a record.
 * - A conversation card: a reply to the business's Instagram story says so
 *   above the customer's words, and an answer lists the options it offered.
 * - The website chat (the real widget script, fake widget API): the options
 *   are chips under the answer until the visitor writes; a tap sends one.
 */

import type { Route } from "@playwright/test";

import { API_URL } from "./support/env";
import { signInAsDemoOwner } from "./support/demo";
import { expect, signInContext, test } from "./support/fixtures";
import { cardOf } from "./support/inbox";
import { en } from "./support/messages";
import { FakeWidgetApi, SITE, ask, chat, loadWidgetSource, serveSite } from "./support/widget-site";

test.describe.configure({ timeout: 120_000 });

const OFFER = { prompt: "Which time suits you?", options: ["18:00", "19:30", "21:00"], language: "en" };

test("a tap on an offered option in the test chat sends it as the customer's message", async ({ page, context, request }) => {
  const owner = await signInAsDemoOwner(request);
  await signInContext(context, owner.token);
  let offered = false;
  await page.route("**/api/backend/v1/businesses/*/test-chat", async (route: Route) => {
    const response = await route.fetch();
    const reply = (await response.json()) as { text?: string | null; choices?: unknown };
    if (!offered && reply.text) {
      offered = true;
      reply.text = `We have free tables tonight.\n\n${OFFER.prompt}`;
      reply.choices = OFFER;
    }
    await route.fulfill({ response, json: reply });
  });

  await page.goto(`/b/${owner.businessId}/assistant`);
  const box = page.getByRole("textbox", { name: en.assistant.chat.inputLabel });
  await box.fill("A table for two tonight?");
  await box.press("Enter");

  const choices = page.getByRole("group", { name: en.assistant.chat.choicesLabel });
  await expect(choices.getByRole("button")).toHaveText(OFFER.options);
  await choices.getByRole("button", { name: "19:30" }).click();

  // The customer's message, and the option kept under the earlier answer.
  const log = page.getByRole("log", { name: en.assistant.chat.logLabel });
  await expect(log.getByText("19:30", { exact: true })).toHaveCount(2);
  await expect(choices).toHaveCount(0);
  // The options stay under their answer, no longer to tap.
  await expect(page.getByRole("list", { name: en.assistant.chat.choicesLabel }).getByRole("listitem")).toHaveText(OFFER.options);
  await expect(page.getByRole("status")).toHaveCount(0, { timeout: 60_000 });
});

test("a conversation card shows a story reply and the options an answer offered", async ({ page, context, request }) => {
  const owner = await signInAsDemoOwner(request);
  await signInContext(context, owner.token);
  const response = await request.get(`${API_URL}/v1/businesses/${owner.businessId}/conversations`, {
    params: { limit: "50" },
    headers: { authorization: `Bearer ${owner.token}` },
  });
  expect(response.ok(), await response.text()).toBe(true);
  const items = ((await response.json()) as { items: { id: string }[] }).items;
  // A conversation where the assistant answered a customer in writing.
  let conversationId: string | null = null;
  for (const item of items) {
    const card = await cardOf(request, owner.token, owner.businessId, item.id);
    const authors = new Set(card.messages.map((message) => message.author));
    if (authors.has("customer") && authors.has("assistant")) {
      conversationId = item.id;
      break;
    }
  }
  expect(conversationId, "a demo conversation with a customer and the assistant").not.toBeNull();

  await page.route(`**/api/backend/v1/businesses/*/conversations/${conversationId!}`, async (route: Route) => {
    if (route.request().method() !== "GET") {
      return route.continue();
    }
    const card = await route.fetch();
    const body = (await card.json()) as { messages?: { author: string; context_note?: string; choices?: string[] }[] };
    const messages = body.messages ?? [];
    const customer = messages.find((message) => message.author === "customer");
    const answer = messages.find((message) => message.author === "assistant");
    if (customer) customer.context_note = "story_reply";
    if (answer) answer.choices = OFFER.options;
    await route.fulfill({ response: card, json: body });
  });

  await page.goto(`/b/${owner.businessId}/inbox/${conversationId!}`);
  await expect(page.getByText(en.inboxCard.messageContext.story_reply).first()).toBeVisible();
  const offered = page.getByRole("list", { name: en.inboxCard.offeredChoices }).first();
  await expect(offered.getByRole("listitem")).toHaveText(OFFER.options);
  // A record of what the customer saw: nothing to tap for them.
  await expect(offered.getByRole("button")).toHaveCount(0);
});

test("the website chat shows the options as chips until the visitor answers", async ({ page }) => {
  await loadWidgetSource();
  const api = new FakeWidgetApi();
  await serveSite(page.context(), api, { dataOpen: true });
  await page.goto(`${SITE}/`);

  api.nextChoices = OFFER.options;
  await ask(page, "A table for two tonight?");
  const chips = chat(page).locator(".aw-choice");
  await expect(chips).toHaveText(OFFER.options);

  await chips.filter({ hasText: "19:30" }).click();
  await expect(chat(page).getByText("Answer to 19:30")).toBeVisible();
  await expect(chips).toHaveCount(0);
  expect(api.messages.filter((message) => message.author === "customer").map((message) => message.text)).toEqual([
    "A table for two tonight?",
    "19:30",
  ]);
});
