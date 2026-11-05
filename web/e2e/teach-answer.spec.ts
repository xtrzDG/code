/**
 * Teaching the assistant from a real conversation, in Italian: the demo
 * restaurant's owner finds Natalia's badly rated answer under the answers
 * worth improving, sees why it was rated bad, fixes the answer on the
 * assistant's bubble and keeps the question as a check; "Check now" asks it
 * of what customers get now (not fixed yet there). The next "Apply changes"
 * asks it first (the rehearsal model answers from the corrected fact,
 * LLM_PROVIDER=scripted) and "My checks" shows it passed; the check is
 * deleted at the end, so the demo stays as it was.
 */

import { signInAsDemoOwner } from "./support/demo";
import { WEB_URL } from "./support/env";
import { expect, test } from "./support/fixtures";
import { it } from "./support/messages";

/** "Apply changes" talks its quick check through before customers get the fix. */
test.describe.configure({ timeout: 240_000 });

const CUSTOMER = "Наталья";
const QUESTION = "Можно ли прийти со своим тортом на день рождения?";
const ANSWER = "Да, свой торт можно. Сервисный сбор — 20 лари: подадим на тарелках и зажжём свечи.";
const WORDS = "20 лари";

test("the owner fixes an answer in Italian and the next update keeps it right", async ({ page, context, request }) => {
  const owner = await signInAsDemoOwner(request);
  await context.addCookies([
    { name: "aw_session", value: owner.token, url: WEB_URL, httpOnly: true, sameSite: "Lax" },
    { name: "aw_locale", value: "it", url: WEB_URL, sameSite: "Lax" },
  ]);
  await page.setViewportSize({ width: 1440, height: 900 });

  // Overview: the badly rated answer waits for a fix.
  await page.goto(`/b/${owner.businessId}/overview`);
  const waiting = page.locator("[data-answers-to-improve] > li").filter({ hasText: QUESTION });
  await expect(waiting).toBeVisible();
  await expect(waiting.getByText(it.teaching.improve.badRating)).toBeVisible();
  await expect(waiting.getByText(it.teaching.rating.reasons.wrong_info)).toBeVisible();
  await waiting.getByRole("link", { name: it.teaching.improve.open }).click();

  // The conversation: why it was rated bad.
  await page.getByRole("button", { name: it.inboxCard.openDetailsOf.replace("{name}", CUSTOMER), exact: true }).click();
  const details = page.getByRole("dialog", { name: it.inboxCard.panelLabel });
  const reasons = details.getByRole("radiogroup", { name: it.teaching.rating.reasonLabel });
  await expect(reasons.getByRole("radio", { name: it.teaching.rating.reasons.wrong_info })).toHaveAttribute("aria-checked", "true");
  await expect(details.getByRole("button", { name: it.teaching.rating.fixAnswer })).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(details).toBeHidden();

  // "Fix the answer" on the assistant's bubble: the customer's question, the suggested kind.
  await page.getByRole("button", { name: it.teaching.fix.actionLabel }).first().click();
  const fix = page.getByRole("dialog", { name: it.teaching.fix.title });
  await expect(fix.getByText(QUESTION, { exact: true })).toBeVisible();
  await expect(fix.getByRole("radio", { name: it.teaching.fix.scopes.faq })).toBeChecked();
  await expect(fix.getByLabel(it.teaching.fix.question)).toHaveValue(QUESTION);
  await fix.getByLabel(it.teaching.fix.answer).fill(ANSWER);
  await fix.getByRole("button", { name: it.teaching.fix.save }).click();

  // Saved: the same question becomes a check that wants the new fee in the answer.
  const saved = page.getByRole("dialog", { name: it.teaching.fix.savedTitle });
  await expect(saved.getByText(it.teaching.fix.saved)).toBeVisible();
  await saved.getByRole("button", { name: it.teaching.fix.saveAsCheck }).click();
  const keep = page.getByRole("dialog", { name: it.teaching.checks.saveTitle });
  await expect(keep.getByLabel(it.teaching.checks.question)).toHaveValue(QUESTION);
  await keep.getByLabel(it.teaching.checks.expectedText).fill(WORDS);
  await keep.getByRole("button", { name: it.common.save, exact: true }).click();

  // "Check now": one test conversation with what customers get now, which
  // does not know the fix yet, so the check does not pass there.
  const kept = page.getByRole("dialog", { name: it.updates.checkNow.savedTitle });
  await kept.getByRole("button", { name: it.updates.checkNow.actionLabel.replace("{question}", QUESTION) }).click();
  const probe = kept.locator("[data-check-probe]");
  await expect(probe).toHaveAttribute("data-check-probe", "failed", { timeout: 60_000 });
  await expect(probe).toContainText(it.updates.checkNow.failed);
  await kept.getByRole("button", { name: it.teaching.fix.done }).click();
  await expect(kept).toBeHidden();

  // "My checks": the check waits for the next update.
  await page.goto(`/b/${owner.businessId}/assistant/checks`);
  const check = page.locator("[data-check]").filter({ hasText: QUESTION });
  await expect(check).toContainText(it.teaching.checks.sources.correction);
  await expect(check).toContainText(WORDS);
  await expect(check.locator("[data-check-result]")).toHaveAttribute("data-check-result", "none");
  await expect(check.locator("[data-check-probe]")).toHaveAttribute("data-check-probe", "failed");

  // "Apply changes": the fix is among the changes, the check runs with the quick check.
  const banner = page.getByTestId("pending-changes-banner");
  await banner.getByRole("button", { name: it.applyChanges.banner.review }).click();
  const sheet = page.getByRole("dialog", { name: it.applyChanges.sheet.title });
  await expect(sheet.getByText(QUESTION, { exact: false }).first()).toBeVisible();
  await sheet.getByRole("button", { name: it.applyChanges.sheet.apply }).click();
  await expect(banner).toBeHidden({ timeout: 180_000 });
  await expect(sheet).toBeHidden();

  await page.reload();
  await expect(check.locator("[data-check-result]")).toHaveAttribute("data-check-result", "passed");
  await expect(check).toContainText(ANSWER);

  // The check is deleted; nothing badly rated waits on the Overview any more.
  await check.getByRole("button", { name: it.teaching.checks.deleteLabel.replace("{question}", QUESTION) }).click();
  const confirm = page.getByRole("dialog", { name: it.teaching.checks.deleteTitle });
  await confirm.getByRole("button", { name: it.teaching.checks.delete, exact: true }).click();
  await expect(check).toHaveCount(0);

  await page.goto(`/b/${owner.businessId}/overview`);
  await expect(page.getByRole("heading", { name: it.teaching.improve.title })).toBeVisible();
  await expect(waiting).toHaveCount(0);
});
