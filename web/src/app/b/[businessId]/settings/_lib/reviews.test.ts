import { describe, expect, it } from "vitest";

import { en } from "@/i18n/messages/en";
import { ka } from "@/i18n/messages/ka";
import { ru } from "@/i18n/messages/ru";
import { createTranslator } from "@/i18n/translate";

import {
  answeredShare,
  delayOptions,
  delayText,
  feedbackReadiness,
  hasErrors,
  isSameReviewSettings,
  isWebLink,
  READINESS_TEXTS,
  REQUEST_STATUS_LABELS,
  reviewSettingsBody,
  reviewSettingsErrors,
  reviewSettingsForm,
  scoreBars,
  SKIP_REASON_LABELS,
  type ReviewSettingsView,
  type ReviewStatsView,
} from "./reviews";

const VIEW: ReviewSettingsView = {
  is_feedback_enabled: false,
  delay_minutes: 120,
  feedback_template_name: null,
  google_review_url: null,
  is_whatsapp_connected: false,
  is_link_tracked: true,
  template_previews: [],
};

const STATS: ReviewStatsView = {
  period_days: 30,
  asked_count: 8,
  answered_count: 4,
  average_score: 4.5,
  score_counts: [
    { score: 1, count: 0 },
    { score: 2, count: 0 },
    { score: 3, count: 1 },
    { score: 4, count: 0 },
    { score: 5, count: 3 },
  ],
  review_opened_count: 2,
  skipped_count: 1,
  failed_count: 0,
};

describe("the review settings form", () => {
  it("starts from the stored settings and saves trimmed values", () => {
    const form = reviewSettingsForm({ ...VIEW, feedback_template_name: "visit_feedback" });

    expect(form).toEqual({ isFeedbackEnabled: false, delayMinutes: 120, templateName: "visit_feedback", reviewUrl: "" });
    expect(reviewSettingsBody({ ...form, templateName: "  ", reviewUrl: " https://g.page/r/x/review " })).toEqual({
      is_feedback_enabled: false,
      delay_minutes: 120,
      feedback_template_name: null,
      google_review_url: "https://g.page/r/x/review",
    });
  });

  it("knows when nothing changed", () => {
    const form = reviewSettingsForm(VIEW);

    expect(isSameReviewSettings(form, VIEW)).toBe(true);
    expect(isSameReviewSettings({ ...form, reviewUrl: "  " }, VIEW)).toBe(true);
    expect(isSameReviewSettings({ ...form, delayMinutes: 60 }, VIEW)).toBe(false);
    expect(isSameReviewSettings({ ...form, reviewUrl: "https://g.page/r/x/review" }, VIEW)).toBe(false);
  });

  it("accepts only template names Meta accepts and full web links", () => {
    const form = reviewSettingsForm(VIEW);

    expect(hasErrors(reviewSettingsErrors(form))).toBe(false);
    expect(reviewSettingsErrors({ ...form, templateName: "Visit feedback" }).templateName).toBe(
      "reviewSettings.feedback.templateInvalid",
    );
    expect(reviewSettingsErrors({ ...form, reviewUrl: "g.page/r/x" }).reviewUrl).toBe("reviewSettings.link.invalid");
    expect(isWebLink("https://search.google.com/local/writereview?placeid=abc")).toBe(true);
    expect(isWebLink("javascript:alert(1)")).toBe(false);
    expect(isWebLink("https://localhost/review")).toBe(false);
    expect(isWebLink("https://g.page/r/x review")).toBe(false);
  });

  it("offers the usual delays and keeps an unusual stored one", () => {
    expect(delayOptions(120)).toEqual([30, 60, 120, 180, 360, 720, 1440, 2880]);
    expect(delayOptions(45)).toEqual([30, 45, 60, 120, 180, 360, 720, 1440, 2880]);
    expect(delayText(30)).toEqual({ key: "reviewSettings.feedback.delayMinutes", count: 30 });
    expect(delayText(180)).toEqual({ key: "reviewSettings.feedback.delayHours", count: 3 });
    expect(delayText(2880)).toEqual({ key: "reviewSettings.feedback.delayDays", count: 2 });
  });
});

describe("whom a request reaches", () => {
  const on = { ...reviewSettingsForm(VIEW), isFeedbackEnabled: true };

  it("is nobody while feedback is off", () => {
    expect(feedbackReadiness(reviewSettingsForm(VIEW), VIEW)).toBe("off");
  });

  it("is everyone with a connected WhatsApp number and a template", () => {
    const connected = { ...VIEW, is_whatsapp_connected: true };

    expect(feedbackReadiness({ ...on, templateName: "visit_feedback" }, connected)).toBe("everywhere");
    expect(feedbackReadiness(on, connected)).toBe("window");
    expect(feedbackReadiness({ ...on, templateName: "visit_feedback" }, VIEW)).toBe("window");
  });
});

describe("the numbers", () => {
  it("give the answered share and the spread of ratings, best first", () => {
    expect(answeredShare(STATS)).toBe(50);
    expect(answeredShare({ ...STATS, asked_count: 0, answered_count: 0 })).toBeNull();
    expect(scoreBars(STATS)).toEqual([
      { score: 5, count: 3, share: 75 },
      { score: 4, count: 0, share: 0 },
      { score: 3, count: 1, share: 25 },
      { score: 2, count: 0, share: 0 },
      { score: 1, count: 0, share: 0 },
    ]);
    expect(scoreBars({ ...STATS, answered_count: 0, score_counts: [] }).every((bar) => bar.share === 0)).toBe(true);
  });
});

describe("the labels", () => {
  it("exist in every language", () => {
    const keys = [
      ...Object.values(READINESS_TEXTS),
      ...Object.values(REQUEST_STATUS_LABELS),
      ...Object.values(SKIP_REASON_LABELS),
    ];
    for (const [locale, messages] of [
      ["en", en],
      ["ru", ru],
      ["ka", ka],
    ] as const) {
      const { t, tp } = createTranslator(locale, messages);
      for (const key of keys) {
        expect(t(key), `${locale} ${key}`).not.toBe(key);
      }
      for (const minutes of [30, 60, 120, 1440, 2880]) {
        const text = delayText(minutes);
        expect(tp(text.key, text.count), `${locale} ${minutes}`).toContain(String(text.count));
      }
    }
  });
});
