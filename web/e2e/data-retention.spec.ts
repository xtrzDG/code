/**
 * Retention: the owner chooses in Settings → Privacy how long customers'
 * conversations are kept; a shorter period asks first (it deletes data
 * at tonight's cleanup), and the hosted chat's privacy notice tells
 * customers the period the business chose.
 */

import { nextSave, savedHint } from "./support/autosave";
import { expect, test } from "./support/fixtures";
import { openChatBusiness } from "./support/hosted-chat";
import { en } from "./support/messages";

const texts = en.privacyRetention;

test("the owner shortens how long conversations are kept, and the privacy notice names the new period", async ({
  page,
  request,
  account,
}) => {
  const business = await openChatBusiness(request, account.token);

  await page.goto(`/b/${business.id}/settings/privacy`);
  await expect(page.getByRole("heading", { name: texts.title })).toBeVisible();
  const conversations = page.getByLabel(texts.conversations.label, { exact: true });
  await expect(conversations).toHaveValue("730");
  await expect(page.getByLabel(texts.modelRecords.label, { exact: true })).toHaveValue("30");
  await expect(page.getByText(texts.noCleanupYet)).toBeVisible();
  await expect(page.getByText(texts.messagingApps)).toBeVisible();

  // A shorter period deletes data: it asks first, and goes back when not confirmed.
  await conversations.selectOption("365");
  const dialog = page.getByRole("dialog", { name: texts.shorterTitle });
  await expect(dialog).toContainText("conversations: 1 year");
  await dialog.getByRole("button", { name: en.common.cancel }).click();
  await expect(dialog).toBeHidden();
  await expect(conversations).toHaveValue("730");

  await conversations.selectOption("365");
  const saved = nextSave(page, "/privacy-settings");
  await dialog.getByRole("button", { name: texts.shorterConfirm }).click();
  await saved;
  await expect(savedHint(page, en.formFields.autosave.saved)).toBeVisible();
  await page.reload();
  await expect(conversations).toHaveValue("365");

  await page.goto(`/c/${business.slug}/privacy`);
  await expect(page.getByText(`${business.name} keeps conversations for 1 year after their last message`)).toBeVisible();
});
