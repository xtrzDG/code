/**
 * Settings → Calls: the owner turns text-backs on with a WhatsApp template
 * (a name Meta would refuse is caught first) and sees what a caller who
 * did not get through would get; the latest text-backs list each caller
 * with what was sent; the call card shows the summary in the reader's
 * language. Missed calls only come from the telephony line, so the list
 * and the card are served by the test.
 */

import type { Page } from "@playwright/test";

import type { Schema } from "../src/api/types";

import { expect, test } from "./support/fixtures";
import { en } from "./support/messages";
import { CONVERSATION_ID, cardWithCalls, openCard, openDetails, serveCard } from "./support/conversation-card";

const calls = en.callSettings;

async function serveTextBacks(page: Page, items: Schema<"TextBackView">[]): Promise<void> {
  await page.route("**/api/backend/v1/businesses/*/text-backs*", (route) =>
    route.fulfill({ json: { items, next_cursor: null } satisfies Schema<"TextBackPage"> }),
  );
}

test("the owner turns text-backs on and the settings stay", async ({ page, owner }) => {
  await page.goto(`/b/${owner.businessId}/settings/calls`);

  await expect(page.getByRole("heading", { name: calls.summaries.title })).toBeVisible();
  await expect(page.getByRole("switch", { name: calls.summaries.toggle })).toHaveAttribute("aria-checked", "true");
  await expect(page.getByText(calls.textBack.readiness.off)).toBeVisible();
  await expect(page.getByText(calls.history.empty)).toBeVisible();

  await page.getByRole("switch", { name: calls.textBack.toggle }).click();
  // No WhatsApp number and no SMS sender on this platform: nothing can go yet.
  await expect(page.getByText(calls.textBack.readiness.none)).toBeVisible();
  await page.getByLabel(calls.textBack.template).fill("Missed call");
  await page.getByRole("button", { name: calls.textBack.save }).click();
  await expect(page.getByText(calls.textBack.templateInvalid)).toBeVisible();

  await page.getByLabel(calls.textBack.template).fill("missed_call_text_back");
  await page.getByRole("button", { name: calls.textBack.save }).click();
  await expect(page.getByText(calls.textBack.saved)).toBeVisible();

  await page.reload();
  await expect(page.getByRole("switch", { name: calls.textBack.toggle })).toHaveAttribute("aria-checked", "true");
  await expect(page.getByLabel(calls.textBack.template)).toHaveValue("missed_call_text_back");
  // The template text to register, with the business name as its parameter.
  await expect(page.getByText(/You called us and we could not answer/).first()).toBeVisible();
});

test("the SMS fallback waits until messages to missed callers are on", async ({ page, owner }) => {
  await page.goto(`/b/${owner.businessId}/settings/calls`);
  const sms = page.getByRole("switch", { name: calls.textBack.sms });
  await expect(page.getByRole("switch", { name: calls.textBack.toggle })).toHaveAttribute("aria-checked", "false");
  await expect(sms).toBeDisabled();
  await expect(sms).toHaveAccessibleDescription(calls.textBack.smsNeedsTextBack);

  await page.getByRole("switch", { name: calls.textBack.toggle }).click();
  await expect(sms).toBeEnabled();
  await expect(sms).toHaveAccessibleDescription(calls.textBack.smsHint);
});

test("the latest text-backs say what each caller got", async ({ page, owner }) => {
  const now = Date.now() * 1000;
  await serveTextBacks(page, [
    {
      id: "missed_call_00000000-0000-5000-8000-000000000001",
      reason: "busy",
      source: "pbx",
      caller_phone_number: "+995599111222",
      called_at: now - 60_000_000,
      language: "ka",
      status: "sent",
      channel: "whatsapp",
      conversation_id: CONVERSATION_ID,
      sent_at: now - 30_000_000,
    },
    {
      id: "missed_call_00000000-0000-5000-8000-000000000002",
      reason: "no_speech",
      source: "voice_platform",
      caller_phone_number: null,
      called_at: now - 600_000_000,
      language: "en",
      status: "skipped",
      skip_reason: "no_caller_number",
    },
  ]);

  await page.goto(`/b/${owner.businessId}/settings/calls`);

  const sent = page.getByRole("listitem").filter({ hasText: "+995599111222" });
  await expect(sent.getByText(calls.history.reasons.busy, { exact: false })).toBeVisible();
  await expect(sent.getByText(calls.history.statuses.sent, { exact: true })).toBeVisible();
  await expect(sent.getByText(calls.history.channels.whatsapp, { exact: true })).toBeVisible();
  await expect(sent.getByRole("link", { name: calls.history.openConversation })).toHaveAttribute(
    "href",
    `/b/${owner.businessId}/inbox/${CONVERSATION_ID}`,
  );
  const hidden = page.getByRole("listitem").filter({ hasText: calls.history.hiddenNumber });
  await expect(hidden.getByText(calls.history.statuses.skipped, { exact: true })).toBeVisible();
  await expect(
    hidden.getByText(calls.history.notSentBecause.replace("{reason}", calls.history.skipReasons.no_caller_number)),
  ).toBeVisible();
});

test("on a phone Settings → Calls fits the screen", async ({ page, owner }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(`/b/${owner.businessId}/settings/calls`);

  await expect(page.getByRole("heading", { name: calls.template.title })).toBeVisible();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(0);
});

test("the call card shows the summary in the reader's language", async ({ page, owner }) => {
  const card = cardWithCalls(owner.businessId, ["call_summarized"]);
  card.calls = (card.calls ?? []).map((call) => ({
    ...call,
    summaries: [
      { language: "ka", text: "სტუმარს ოთხკაციანი მაგიდა სურს." },
      { language: "en", text: "The caller wants a table for four on Saturday." },
    ],
  }));
  await serveCard(page, owner.businessId, card);

  await openCard(page, owner.businessId);
  await openDetails(page);

  await expect(page.getByText(en.conversations.calls.summary, { exact: true })).toBeVisible();
  await expect(page.getByText("The caller wants a table for four on Saturday.")).toBeVisible();
  await expect(page.getByText("სტუმარს ოთხკაციანი მაგიდა სურს.")).toHaveCount(0);
});
