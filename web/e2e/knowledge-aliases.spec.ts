/**
 * A knowledge item's names in the business's other languages (against the
 * real API): the owner of an English, Russian and Georgian café opens an
 * English question whose Georgian name is theirs and whose Russian name the
 * model suggested, accepts the suggestion and types one more Russian name
 * (Enter adds it, it does not save the dialog), saves, and finds the names
 * there again. Visitors of the hosted chat then get the question as a
 * starter chip in their own language: English from the title, Russian and
 * Georgian from the approved names.
 */

import type { Browser } from "@playwright/test";

import { API_URL, WEB_URL } from "./support/env";
import { expect, test } from "./support/fixtures";
import { openChatBusiness } from "./support/hosted-chat";
import { en } from "./support/messages";

const TITLE = "Do you have parking?";
const GEORGIAN = "გაქვთ პარკინგი?";
const RUSSIAN = "У вас есть парковка?";
const RUSSIAN_TYPED = "Где оставить машину?";

async function chipsFor(browser: Browser, locale: string, slug: string): Promise<string[]> {
  const context = await browser.newContext({ locale });
  try {
    const page = await context.newPage();
    await page.goto(`${WEB_URL}/c/${slug}`);
    // The widget draws its starter chips once its configuration has come.
    const chips = page.locator(".aw-starter");
    await expect(chips.first()).toBeVisible();
    return (await chips.allInnerTexts()).map((text) => text.trim());
  } finally {
    await context.close();
  }
}

test("the owner reviews a question's names in other languages and visitors get them as starter chips", async ({
  page,
  request,
  account,
  browser,
}) => {
  const business = await openChatBusiness(request, account.token, ["en", "ru", "ka"]);
  const created = await request.post(`${API_URL}/v1/businesses/${business.id}/knowledge`, {
    headers: { authorization: `Bearer ${account.token}` },
    data: {
      kind: "faq",
      title: TITLE,
      body: "Yes, free parking in the yard.",
      languages: ["en"],
      aliases: [
        { language: "ka", text: GEORGIAN, status: "approved" },
        { language: "ru", text: RUSSIAN, status: "suggested" },
      ],
    },
  });
  expect(created.status(), await created.text()).toBe(201);

  // A suggestion is searched but never offered to visitors before the owner accepts it.
  expect(await chipsFor(browser, "ru-RU", business.slug)).not.toContain(RUSSIAN);

  await page.goto(`/b/${business.id}/assistant/knowledge`);
  await page
    .getByRole("button", { name: `${en.common.edit}: ${TITLE}` })
    .first()
    .click();
  const editor = page.getByRole("dialog", { name: en.knowledge.form.editTitle });
  const names = editor.getByRole("region", { name: en.knowledge.aliases.title });
  const russian = names.getByRole("group", { name: "Russian" });
  const georgian = names.getByRole("group", { name: "Georgian" });
  await expect(georgian.getByText(GEORGIAN)).toBeVisible();
  await expect(russian.getByText(en.knowledge.aliases.suggested)).toBeVisible();

  await russian.getByRole("button", { name: en.knowledge.aliases.accept.replace("{text}", RUSSIAN) }).click();
  await expect(russian.getByText(en.knowledge.aliases.suggested)).toHaveCount(0);
  const field = russian.getByRole("textbox", {
    name: en.knowledge.aliases.placeholder.replace("{language}", "Russian"),
  });
  await field.fill(RUSSIAN_TYPED);
  await field.press("Enter");
  await expect(editor).toBeVisible();
  await expect(russian.getByText(RUSSIAN_TYPED)).toBeVisible();

  await editor.getByRole("button", { name: en.common.save, exact: true }).click();
  await expect(page.getByText(en.common.saved)).toBeVisible();
  await expect(editor).toBeHidden();

  // Opened again: the names were stored, both Russian ones the owner's.
  await page
    .getByRole("button", { name: `${en.common.edit}: ${TITLE}` })
    .first()
    .click();
  const reopened = page.getByRole("dialog", { name: en.knowledge.form.editTitle });
  const stored = reopened.getByRole("group", { name: "Russian" });
  await expect(stored.getByText(RUSSIAN, { exact: true })).toBeVisible();
  await expect(stored.getByText(RUSSIAN_TYPED)).toBeVisible();
  await expect(stored.getByText(en.knowledge.aliases.suggested)).toHaveCount(0);
  await reopened.getByRole("button", { name: en.common.cancel }).click();

  // The hosted chat: the same question in each visitor's language.
  expect(await chipsFor(browser, "en-US", business.slug)).toContain(TITLE);
  const forRussian = await chipsFor(browser, "ru-RU", business.slug);
  expect(forRussian).toContain(RUSSIAN);
  expect(forRussian).not.toContain(TITLE);
  const forGeorgian = await chipsFor(browser, "ka-GE", business.slug);
  expect(forGeorgian).toContain(GEORGIAN);
  expect(forGeorgian).not.toContain(RUSSIAN);
});
