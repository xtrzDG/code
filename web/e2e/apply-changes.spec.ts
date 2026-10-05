/**
 * One "Apply changes" in the daily cabinet, in Russian, English and
 * Georgian: the owner of the demo restaurant edits a price, the banner over
 * the page says one change is not with customers yet, its sheet names the
 * new price in the owner's words, and "Apply changes" runs the launch's
 * three stages with a quick check on the rehearsal model
 * (LLM_PROVIDER=scripted). Once customers get the new price the banner is
 * gone and a toast says what the assistant now knows. An owner's check the
 * rehearsal assistant fails is named in the sheet by its question; fixing
 * the answer it got takes the update live.
 */

import type { Page } from "@playwright/test";

import { signInAsDemoOwner } from "./support/demo";
import { WEB_URL } from "./support/env";
import { expect, test } from "./support/fixtures";
import { en, ka, ru } from "./support/messages";

/** The quick check talks a few test conversations through before customers get the change. */
test.describe.configure({ timeout: 240_000 });

const LANGUAGES = { ru, en, ka } as const;

type Messages = (typeof LANGUAGES)[keyof typeof LANGUAGES];

const escape = (text: string) => text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

/** A template's text before its first placeholder: "Price, {currency}" -> "Price, ". */
const lead = (template: string) => template.split("{")[0] ?? template;

/** Opens the first menu item, raises its price by one and saves it; returns the item's title. */
async function raiseFirstPrice(page: Page, messages: Messages): Promise<string> {
  const menu = page.getByRole("region", { name: messages.knowledge.kindGroups.menu_item });
  const edit = menu.getByRole("button", { name: new RegExp(`^${escape(messages.common.edit)}: `) }).first();
  const title = ((await edit.getAttribute("aria-label")) ?? "").slice(`${messages.common.edit}: `.length);
  await edit.click();

  const editor = page.getByRole("dialog", { name: messages.knowledge.form.editTitle });
  const price = editor.getByLabel(new RegExp(`^${escape(lead(messages.knowledge.form.price))}`));
  const current = Number((await price.inputValue()).replace(",", ".").replace(/\s/g, "")) || 10;
  await price.fill(String(Math.floor(current) + 1));
  await editor.getByRole("button", { name: messages.common.save, exact: true }).click();
  await expect(editor).toBeHidden();
  return title;
}

for (const [locale, messages] of Object.entries(LANGUAGES)) {
  test(`a new price reaches customers with one "Apply changes" (${locale})`, async ({ page, context, request }) => {
    const owner = await signInAsDemoOwner(request);
    await context.addCookies([
      { name: "aw_session", value: owner.token, url: WEB_URL, httpOnly: true, sameSite: "Lax" },
      { name: "aw_locale", value: locale, url: WEB_URL, sameSite: "Lax" },
    ]);
    await page.goto(`/b/${owner.businessId}/assistant/knowledge`);

    const banner = page.getByTestId("pending-changes-banner");
    const title = await raiseFirstPrice(page, messages);

    // The banner over the page counts the change and opens the list.
    await expect(banner).toContainText((messages.applyChanges.banner.pending.one ?? "").replace("{count}", "1"));
    await banner.getByRole("button", { name: messages.applyChanges.banner.review }).click();

    const sheet = page.getByRole("dialog", { name: messages.applyChanges.sheet.title });
    await expect(sheet.getByText(messages.applyChanges.areas.offer, { exact: true })).toBeVisible();
    await expect(sheet.getByText(title, { exact: false })).toBeVisible();

    // The launch's stages, then customers get the new price.
    await sheet.getByRole("button", { name: messages.applyChanges.sheet.apply }).click();
    await expect(sheet.getByText(messages.applyChanges.sheet.runningTitle)).toBeVisible();
    await expect(banner).toBeHidden({ timeout: 180_000 });
    await expect(sheet).toBeHidden();
    const toast = page.getByRole("status").getByText(new RegExp(`^${escape(lead(messages.applyChanges.done.knows))}.*${escape(title)}`));
    await expect(toast).toBeVisible();

    // Nothing is pending any more: the Assistant's button opens the same sheet, done.
    await page.getByRole("main").getByRole("button", { name: messages.applyChanges.sheet.apply }).click();
    await expect(sheet.getByText(messages.applyChanges.done.title)).toBeVisible();
    await sheet.getByRole("button", { name: messages.applyChanges.sheet.close, exact: true }).first().click();
    await expect(sheet).toBeHidden();
  });
}

/** The owner's check the rehearsal assistant fails until its answer is fixed. */
const DOG_QUESTION = "Можно прийти с собакой?";
const DOG_WORDS = "с собакой можно";
const DOG_ANSWER = "Да, с собакой можно: для неё есть место на веранде.";

test("a check that fails is named in the sheet, its answer fixed, and the update goes live", async ({ page, context, request }) => {
  const owner = await signInAsDemoOwner(request);
  await context.addCookies([
    { name: "aw_session", value: owner.token, url: WEB_URL, httpOnly: true, sameSite: "Lax" },
    { name: "aw_locale", value: "ru", url: WEB_URL, sameSite: "Lax" },
  ]);
  await page.setViewportSize({ width: 1440, height: 900 });

  // "Мои проверки": a new check takes the language of its question.
  await page.goto(`/b/${owner.businessId}/assistant/checks`);
  await page.getByRole("button", { name: ru.teaching.checks.add }).first().click();
  const editor = page.getByRole("dialog", { name: ru.teaching.checks.newTitle });
  await expect(editor.getByLabel(ru.teaching.checks.language)).toHaveValue("");
  await editor.getByLabel(ru.teaching.checks.question).fill(DOG_QUESTION);
  await editor.getByLabel(ru.teaching.checks.expectedText).fill(DOG_WORDS);
  await editor.getByRole("button", { name: ru.common.save, exact: true }).click();
  const saved = page.getByRole("dialog", { name: ru.updates.checkNow.savedTitle });
  await saved.getByRole("button", { name: ru.teaching.fix.done }).click();
  await expect(saved).toBeHidden();

  // The sheet counts the new check: it is not "everything is with customers".
  const banner = page.getByTestId("pending-changes-banner");
  await banner.getByRole("button", { name: ru.applyChanges.banner.review }).click();
  const sheet = page.getByRole("dialog", { name: ru.applyChanges.sheet.title });
  await expect(sheet.getByText(ru.updates.pending.added.replace("{question}", DOG_QUESTION))).toBeVisible();
  await expect(sheet.getByText(ru.applyChanges.sheet.nothing)).toHaveCount(0);

  // The update stops on the check, named by its question and what the answer must do.
  await sheet.getByRole("button", { name: ru.applyChanges.sheet.apply }).click();
  const named = ru.updates.failed.one
    .replace("{question}", DOG_QUESTION)
    .replace("{expectation}", ru.updates.expectation.must_mention.replace("{text}", DOG_WORDS));
  await expect(sheet.getByText(named)).toBeVisible({ timeout: 180_000 });
  await expect(sheet.getByRole("link", { name: ru.updates.failed.openCheck })).toBeVisible();

  // "Исправить ответ" on the test answer, then back to "Применить изменения".
  await sheet.getByRole("button", { name: ru.updates.failed.fixAnswer }).click();
  const fix = page.getByRole("dialog", { name: ru.teaching.fix.title });
  await expect(fix.getByLabel(ru.teaching.fix.question)).toHaveValue(DOG_QUESTION);
  await fix.getByLabel(ru.teaching.fix.answer).fill(DOG_ANSWER);
  await fix.getByRole("button", { name: ru.teaching.fix.save }).click();
  const fixed = page.getByRole("dialog", { name: ru.teaching.fix.savedTitle });
  await fixed.getByRole("button", { name: ru.updates.failed.applyAfterFix }).click();
  await expect(sheet).toBeVisible();
  await sheet.getByRole("button", { name: ru.applyChanges.sheet.tryAgain }).click();

  // Customers get the fixed answer: the banner goes and the check passed.
  await expect(banner).toBeHidden({ timeout: 180_000 });
  await page.goto(`/b/${owner.businessId}/assistant/checks`);
  const check = page.locator("[data-check]").filter({ hasText: DOG_QUESTION });
  await expect(check.locator("[data-check-result]")).toHaveAttribute("data-check-result", "passed");
  await expect(check).toContainText(DOG_WORDS);

  // The check goes, so the demo stays as it was.
  await check.getByRole("button", { name: ru.teaching.checks.deleteLabel.replace("{question}", DOG_QUESTION) }).click();
  const confirm = page.getByRole("dialog", { name: ru.teaching.checks.deleteTitle });
  await confirm.getByRole("button", { name: ru.teaching.checks.delete, exact: true }).click();
  await expect(check).toHaveCount(0);

  // The test chat talks to what customers get now or with your changes: no version numbers.
  await page.goto(`/b/${owner.businessId}/assistant`);
  await expect(page.getByLabel(ru.updates.chat.target).locator("option")).toHaveText([ru.updates.chat.live, ru.updates.chat.changes]);
});
