/**
 * Teaching the assistant from a real conversation, in Russian: the demo
 * restaurant's owner finds Natalia's badly rated answer under "Ответы,
 * которые стоит улучшить", sees why it was rated bad, fixes the answer on
 * the assistant's bubble and keeps the question as a check; "Проверить
 * сейчас" asks it of what customers get now (not fixed yet there). The next
 * "Применить изменения" asks it first (the rehearsal model answers from
 * the corrected fact, LLM_PROVIDER=scripted) and "Мои проверки" shows it
 * passed; the check is deleted at the end, so the demo stays as it was.
 */

import { signInAsDemoOwner } from "./support/demo";
import { WEB_URL } from "./support/env";
import { expect, test } from "./support/fixtures";
import { ru } from "./support/messages";

/** "Apply changes" talks its quick check through before customers get the fix. */
test.describe.configure({ timeout: 240_000 });

const CUSTOMER = "Наталья";
const QUESTION = "Можно ли прийти со своим тортом на день рождения?";
const ANSWER = "Да, свой торт можно. Сервисный сбор — 20 лари: подадим на тарелках и зажжём свечи.";
const WORDS = "20 лари";

test("the owner fixes an answer in Russian and the next update keeps it right", async ({ page, context, request }) => {
  const owner = await signInAsDemoOwner(request);
  await context.addCookies([
    { name: "aw_session", value: owner.token, url: WEB_URL, httpOnly: true, sameSite: "Lax" },
    { name: "aw_locale", value: "ru", url: WEB_URL, sameSite: "Lax" },
  ]);
  await page.setViewportSize({ width: 1440, height: 900 });

  // Overview: the badly rated answer waits for a fix.
  await page.goto(`/b/${owner.businessId}/overview`);
  const waiting = page.locator("[data-answers-to-improve] > li").filter({ hasText: QUESTION });
  await expect(waiting).toBeVisible();
  await expect(waiting.getByText(ru.teaching.improve.badRating)).toBeVisible();
  await expect(waiting.getByText(ru.teaching.rating.reasons.wrong_info)).toBeVisible();
  await waiting.getByRole("link", { name: ru.teaching.improve.open }).click();

  // The conversation: why it was rated bad.
  await page.getByRole("button", { name: ru.inboxCard.openDetailsOf.replace("{name}", CUSTOMER), exact: true }).click();
  const details = page.getByRole("dialog", { name: ru.inboxCard.panelLabel });
  const reasons = details.getByRole("radiogroup", { name: ru.teaching.rating.reasonLabel });
  await expect(reasons.getByRole("radio", { name: ru.teaching.rating.reasons.wrong_info })).toHaveAttribute("aria-checked", "true");
  await expect(details.getByRole("button", { name: ru.teaching.rating.fixAnswer })).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(details).toBeHidden();

  // "Исправить ответ" on the assistant's bubble: the customer's question, the suggested kind.
  await page.getByRole("button", { name: ru.teaching.fix.actionLabel }).first().click();
  const fix = page.getByRole("dialog", { name: ru.teaching.fix.title });
  await expect(fix.getByText(QUESTION, { exact: true })).toBeVisible();
  await expect(fix.getByRole("radio", { name: ru.teaching.fix.scopes.faq })).toBeChecked();
  await expect(fix.getByLabel(ru.teaching.fix.question)).toHaveValue(QUESTION);
  await fix.getByLabel(ru.teaching.fix.answer).fill(ANSWER);
  await fix.getByRole("button", { name: ru.teaching.fix.save }).click();

  // Saved: the same question becomes a check that wants the new fee in the answer.
  const saved = page.getByRole("dialog", { name: ru.teaching.fix.savedTitle });
  await expect(saved.getByText(ru.teaching.fix.saved)).toBeVisible();
  await saved.getByRole("button", { name: ru.teaching.fix.saveAsCheck }).click();
  const keep = page.getByRole("dialog", { name: ru.teaching.checks.saveTitle });
  await expect(keep.getByLabel(ru.teaching.checks.question)).toHaveValue(QUESTION);
  await keep.getByLabel(ru.teaching.checks.expectedText).fill(WORDS);
  await keep.getByRole("button", { name: ru.common.save, exact: true }).click();

  // "Проверить сейчас": one test conversation with what customers get now, which
  // does not know the fix yet, so the check does not pass there.
  const kept = page.getByRole("dialog", { name: ru.updates.checkNow.savedTitle });
  await kept.getByRole("button", { name: ru.updates.checkNow.actionLabel.replace("{question}", QUESTION) }).click();
  const probe = kept.locator("[data-check-probe]");
  await expect(probe).toHaveAttribute("data-check-probe", "failed", { timeout: 60_000 });
  await expect(probe).toContainText(ru.updates.checkNow.failed);
  await kept.getByRole("button", { name: ru.teaching.fix.done }).click();
  await expect(kept).toBeHidden();

  // "Мои проверки": the check waits for the next update.
  await page.goto(`/b/${owner.businessId}/assistant/checks`);
  const check = page.locator("[data-check]").filter({ hasText: QUESTION });
  await expect(check).toContainText(ru.teaching.checks.sources.correction);
  await expect(check).toContainText(WORDS);
  await expect(check.locator("[data-check-result]")).toHaveAttribute("data-check-result", "none");
  await expect(check.locator("[data-check-probe]")).toHaveAttribute("data-check-probe", "failed");

  // "Применить изменения": the fix is among the changes, the check runs with the quick check.
  const banner = page.getByTestId("pending-changes-banner");
  await banner.getByRole("button", { name: ru.applyChanges.banner.review }).click();
  const sheet = page.getByRole("dialog", { name: ru.applyChanges.sheet.title });
  await expect(sheet.getByText(QUESTION, { exact: false }).first()).toBeVisible();
  await sheet.getByRole("button", { name: ru.applyChanges.sheet.apply }).click();
  await expect(banner).toBeHidden({ timeout: 180_000 });
  await expect(sheet).toBeHidden();

  await page.reload();
  await expect(check.locator("[data-check-result]")).toHaveAttribute("data-check-result", "passed");
  await expect(check).toContainText(ANSWER);

  // The check is deleted; nothing badly rated waits on the Overview any more.
  await check.getByRole("button", { name: ru.teaching.checks.deleteLabel.replace("{question}", QUESTION) }).click();
  const confirm = page.getByRole("dialog", { name: ru.teaching.checks.deleteTitle });
  await confirm.getByRole("button", { name: ru.teaching.checks.delete, exact: true }).click();
  await expect(check).toHaveCount(0);

  await page.goto(`/b/${owner.businessId}/overview`);
  await expect(page.getByRole("heading", { name: ru.teaching.improve.title })).toBeVisible();
  await expect(waiting).toHaveCount(0);
});
