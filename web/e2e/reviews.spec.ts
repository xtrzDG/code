/**
 * Settings → Reviews: the owner turns feedback after visits on, picks when
 * to ask and the Google review link (malformed values are caught first),
 * and the choices stay; the numbers of the last 30 days and the latest
 * requests say what customers answered. Requests only come from visits
 * the worker asked about, so the numbers and the list are served by the
 * test.
 */

import type { Page } from "@playwright/test";

import type { Schema } from "../src/api/types";

import { nextSave, savedHint } from "./support/autosave";
import { expect, test } from "./support/fixtures";
import { en } from "./support/messages";

const reviews = en.reviewSettings;
const CONVERSATION_ID = "conversation_00000000-0000-5000-8000-0000000000aa";

async function serveNumbers(page: Page): Promise<void> {
  const now = Date.now() * 1000;
  const stats: Schema<"ReviewStatsView"> = {
    period_days: 30,
    asked_count: 12,
    answered_count: 8,
    average_score: 4.5,
    score_counts: [
      { score: 1, count: 0 },
      { score: 2, count: 1 },
      { score: 3, count: 0 },
      { score: 4, count: 1 },
      { score: 5, count: 6 },
    ],
    review_opened_count: 5,
    skipped_count: 2,
    failed_count: 0,
  };
  const items: Schema<"FeedbackRequestView">[] = [
    {
      id: "feedback_request_00000000-0000-5000-8000-000000000001",
      booking_id: "booking_00000000-0000-5000-8000-000000000001",
      contact_id: "contact_00000000-0000-5000-8000-000000000001",
      contact_name: "Nino Beridze",
      visit_ended_at: now - 3 * 3_600_000_000,
      status: "answered",
      channel: "whatsapp",
      sent_at: now - 3_600_000_000,
      score: 5,
      answered_at: now - 3_000_000_000,
      review_clicks: 1,
      conversation_id: CONVERSATION_ID,
    },
    {
      id: "feedback_request_00000000-0000-5000-8000-000000000002",
      booking_id: "booking_00000000-0000-5000-8000-000000000002",
      contact_id: "contact_00000000-0000-5000-8000-000000000002",
      contact_name: null,
      visit_ended_at: now - 26 * 3_600_000_000,
      status: "skipped",
      skip_reason: "opted_out",
      review_clicks: 0,
    },
  ];
  await page.route("**/api/backend/v1/businesses/*/review-stats", (route) => route.fulfill({ json: stats }));
  await page.route("**/api/backend/v1/businesses/*/feedback-requests*", (route) =>
    route.fulfill({ json: { items, next_cursor: null } satisfies Schema<"FeedbackRequestPage"> }),
  );
}

test("the owner turns feedback on with the review link and the settings stay", async ({ page, owner }) => {
  await page.goto(`/b/${owner.businessId}/settings/reviews`);

  const toggle = page.getByRole("switch", { name: reviews.feedback.toggle });
  await expect(toggle).toHaveAttribute("aria-checked", "false");
  await expect(page.getByText(reviews.feedback.readiness.off)).toBeVisible();
  await expect(page.getByText(reviews.stats.noAverage)).toBeVisible();
  await expect(page.getByText(reviews.requests.empty)).toBeVisible();

  // No Save button: each choice saves itself.
  await expect(page.getByRole("button", { name: en.common.save, exact: true })).toHaveCount(0);
  const path = "/review-settings";
  const switched = nextSave(page, path);
  await toggle.click();
  await switched;
  // No WhatsApp number here: only customers who wrote within a day are asked.
  await expect(page.getByText(reviews.feedback.readiness.window)).toBeVisible();
  const delayed = nextSave(page, path);
  await page.getByLabel(reviews.feedback.delay).selectOption("180");
  await delayed;
  // Values that are not valid are not saved; each field says why once it is left.
  await page.getByLabel(reviews.feedback.template).fill("Visit feedback");
  await page.getByLabel(reviews.link.label).fill("g.page/r/cafe/review");
  await page.getByLabel(reviews.feedback.delay).focus();
  await expect(page.getByText(reviews.feedback.templateInvalid)).toBeVisible();
  await expect(page.getByText(reviews.link.invalid)).toBeVisible();

  const named = nextSave(page, path);
  await page.getByLabel(reviews.feedback.template).fill("visit_feedback");
  await page.getByLabel(reviews.link.label).fill("https://g.page/r/cafe/review");
  await page.getByLabel(reviews.feedback.delay).focus();
  await named;
  await expect(page.getByText(reviews.feedback.templateInvalid)).toBeHidden();
  await expect(savedHint(page, en.formFields.autosave.saved)).toBeVisible();

  await page.reload();
  await expect(page.getByRole("switch", { name: reviews.feedback.toggle })).toHaveAttribute("aria-checked", "true");
  await expect(page.getByLabel(reviews.feedback.delay)).toHaveValue("180");
  await expect(page.getByLabel(reviews.feedback.template)).toHaveValue("visit_feedback");
  await expect(page.getByLabel(reviews.link.label)).toHaveValue("https://g.page/r/cafe/review");
  // The template text to register, with the business name as its parameter.
  await expect(page.getByText(/How was your visit\?/).first()).toBeVisible();
});

test("the numbers and the latest requests say what customers answered", async ({ page, owner }) => {
  await serveNumbers(page);

  await page.goto(`/b/${owner.businessId}/settings/reviews`);

  await expect(page.getByText(reviews.stats.averageValue.replace("{score}", "4.5"))).toBeVisible();
  await expect(page.getByText(reviews.stats.answeredShare.replace("{percent}", "67%"))).toBeVisible();
  await expect(page.getByText(reviews.stats.notAsked.replace("{count}", "2"))).toBeVisible();
  const answered = page.getByRole("listitem").filter({ hasText: "Nino Beridze" });
  await expect(answered.getByText(reviews.requests.rating.replace("{score}", "5"))).toBeVisible();
  await expect(answered.getByText(reviews.requests.openedLink, { exact: true })).toBeVisible();
  await expect(answered.getByRole("link", { name: reviews.requests.openConversation })).toHaveAttribute(
    "href",
    `/b/${owner.businessId}/inbox/${CONVERSATION_ID}`,
  );
  const skipped = page.getByRole("listitem").filter({ hasText: reviews.requests.customer });
  await expect(
    skipped.getByText(reviews.requests.notAskedBecause.replace("{reason}", reviews.requests.skipReasons.opted_out)),
  ).toBeVisible();
});

test("on a phone Settings → Reviews fits the screen", async ({ page, owner }) => {
  await serveNumbers(page);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(`/b/${owner.businessId}/settings/reviews`);

  await expect(page.getByRole("heading", { name: reviews.template.title })).toBeVisible();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(0);
});
