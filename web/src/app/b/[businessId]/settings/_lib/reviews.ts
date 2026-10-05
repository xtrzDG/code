/**
 * Settings → Reviews: the owner's form (feedback after visits, when to
 * ask, the WhatsApp template, the Google review link), what customers get
 * with it, the numbers of the last 30 days and the labels of the latest
 * requests.
 */

import type { RequestBody, Schema } from "@/api/types";
import type { BadgeTone } from "@/components/ui";
import type { MessageKey, PluralKey } from "@/i18n/translate";

export type ReviewSettingsView = Schema<"ReviewSettingsView">;
export type ReviewSettingsBody = RequestBody<"/v1/businesses/{business_id}/review-settings", "put">;
export type ReviewStatsView = Schema<"ReviewStatsView">;
export type FeedbackRequestView = Schema<"FeedbackRequestView">;
export type FeedbackRequestPage = Schema<"FeedbackRequestPage">;
export type FeedbackRequestStatus = Schema<"FeedbackRequestStatus">;
export type FeedbackSkipReason = Schema<"FeedbackSkipReason">;

/** Settings → Reviews lists the latest requests only (the API pages further). */
export const FEEDBACK_REQUEST_LIST_SIZE = 20;
const SCORES = [5, 4, 3, 2, 1] as const;

/** What Meta accepts as a template name (the API checks the same). */
const TEMPLATE_NAME_PATTERN = /^[a-z0-9_]{1,512}$/;
const MAX_LINK_LENGTH = 2048;

/** The delays an owner picks from, in minutes after the visit ends (the API allows 15 to 4320). */
const DELAY_CHOICES = [30, 60, 120, 180, 360, 720, 1440, 2880] as const;

export interface ReviewSettingsForm {
  isFeedbackEnabled: boolean;
  delayMinutes: number;
  /** As typed; an empty name means "no WhatsApp template". */
  templateName: string;
  /** As typed; an empty link means "no review link". */
  reviewUrl: string;
}

export function reviewSettingsForm(view: ReviewSettingsView): ReviewSettingsForm {
  return {
    isFeedbackEnabled: view.is_feedback_enabled,
    delayMinutes: view.delay_minutes,
    templateName: view.feedback_template_name ?? "",
    reviewUrl: view.google_review_url ?? "",
  };
}

export function reviewSettingsBody(form: ReviewSettingsForm): ReviewSettingsBody {
  const templateName = form.templateName.trim();
  const reviewUrl = form.reviewUrl.trim();
  return {
    is_feedback_enabled: form.isFeedbackEnabled,
    delay_minutes: form.delayMinutes,
    feedback_template_name: templateName === "" ? null : templateName,
    google_review_url: reviewUrl === "" ? null : reviewUrl,
  };
}

export interface ReviewSettingsErrors {
  templateName: MessageKey | null;
  reviewUrl: MessageKey | null;
}

/** The errors under the fields; all null when the form can be saved. */
export function reviewSettingsErrors(form: ReviewSettingsForm): ReviewSettingsErrors {
  const templateName = form.templateName.trim();
  const reviewUrl = form.reviewUrl.trim();
  return {
    templateName:
      templateName === "" || TEMPLATE_NAME_PATTERN.test(templateName) ? null : "reviewSettings.feedback.templateInvalid",
    reviewUrl: reviewUrl === "" || isWebLink(reviewUrl) ? null : "reviewSettings.link.invalid",
  };
}

export function hasErrors(errors: ReviewSettingsErrors): boolean {
  return errors.templateName !== null || errors.reviewUrl !== null;
}

/** A full http(s) address with a host, as the API accepts it. */
export function isWebLink(text: string): boolean {
  if (text.length > MAX_LINK_LENGTH || /\s/.test(text)) {
    return false;
  }
  try {
    const url = new URL(text);
    return (url.protocol === "https:" || url.protocol === "http:") && url.hostname.includes(".");
  } catch {
    return false;
  }
}

export function isSameReviewSettings(form: ReviewSettingsForm, view: ReviewSettingsView): boolean {
  const body = reviewSettingsBody(form);
  return (
    body.is_feedback_enabled === view.is_feedback_enabled &&
    body.delay_minutes === view.delay_minutes &&
    (body.feedback_template_name ?? null) === (view.feedback_template_name ?? null) &&
    (body.google_review_url ?? null) === (view.google_review_url ?? null)
  );
}

/** The delays to offer: the choices, and the stored one when it is not among them. */
export function delayOptions(current: number): number[] {
  const choices: number[] = [...DELAY_CHOICES];
  return choices.includes(current) ? choices : [...choices, current].sort((left, right) => left - right);
}

export type DelayText = { key: PluralKey; count: number };

/** "2 hours after the visit", "30 minutes after the visit", "2 days after the visit" (`tp`). */
export function delayText(minutes: number): DelayText {
  if (minutes % 1440 === 0) {
    return { key: "reviewSettings.feedback.delayDays", count: minutes / 1440 };
  }
  if (minutes % 60 === 0) {
    return { key: "reviewSettings.feedback.delayHours", count: minutes / 60 };
  }
  return { key: "reviewSettings.feedback.delayMinutes", count: minutes };
}

export type FeedbackReadiness = "off" | "everywhere" | "window";

/**
 * Whom a request reaches with these choices: every messenger customer
 * (a connected WhatsApp number with a template covers those quiet for a
 * day), or only those who wrote within the last 24 hours on WhatsApp.
 */
export function feedbackReadiness(form: ReviewSettingsForm, view: ReviewSettingsView): FeedbackReadiness {
  if (!form.isFeedbackEnabled) {
    return "off";
  }
  if (view.is_whatsapp_connected && form.templateName.trim() !== "") {
    return "everywhere";
  }
  return "window";
}

export const READINESS_TEXTS: Record<FeedbackReadiness, MessageKey> = {
  off: "reviewSettings.feedback.readiness.off",
  everywhere: "reviewSettings.feedback.readiness.everywhere",
  window: "reviewSettings.feedback.readiness.window",
};

export const READINESS_TONES: Record<FeedbackReadiness, "info" | "success" | "warning"> = {
  off: "info",
  everywhere: "success",
  window: "warning",
};

/** Answered of asked as a whole percentage; null before anyone was asked. */
export function answeredShare(stats: ReviewStatsView): number | null {
  return stats.asked_count === 0 ? null : Math.round((stats.answered_count / stats.asked_count) * 100);
}

/** How many gave each score, best first, with each score's share of all ratings (0 to 100). */
export function scoreBars(stats: ReviewStatsView): { score: number; count: number; share: number }[] {
  const counts = new Map((stats.score_counts ?? []).map((item) => [item.score, item.count]));
  const total = stats.answered_count;
  return SCORES.map((score) => {
    const count = counts.get(score) ?? 0;
    return { score, count, share: total === 0 ? 0 : Math.round((count / total) * 100) };
  });
}

export const REQUEST_STATUS_LABELS: Record<FeedbackRequestStatus, MessageKey> = {
  sent: "reviewSettings.requests.statuses.sent",
  answered: "reviewSettings.requests.statuses.answered",
  skipped: "reviewSettings.requests.statuses.skipped",
  failed: "reviewSettings.requests.statuses.failed",
};

export const REQUEST_STATUS_TONES: Record<FeedbackRequestStatus, BadgeTone> = {
  sent: "info",
  answered: "success",
  skipped: "neutral",
  failed: "danger",
};

export const SKIP_REASON_LABELS: Record<FeedbackSkipReason, MessageKey> = {
  opted_out: "reviewSettings.requests.skipReasons.opted_out",
  no_contact: "reviewSettings.requests.skipReasons.no_contact",
  no_channel: "reviewSettings.requests.skipReasons.no_channel",
  window_closed: "reviewSettings.requests.skipReasons.window_closed",
  already_asked: "reviewSettings.requests.skipReasons.already_asked",
  daily_limit: "reviewSettings.requests.skipReasons.daily_limit",
};
