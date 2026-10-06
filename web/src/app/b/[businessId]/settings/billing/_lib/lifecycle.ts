/**
 * Pure helpers of the subscription lifecycle on the Billing page: the
 * cancel dialog's reasons and the offer each one gets, and what the pause
 * card shows.
 *
 * Fields of the API this relies on (GET …/billing/lifecycle): offers[].
 * {reason, offer.{kind, pause_months, pause_price, plan_key, plan_name,
 * plan_price, credit}}, pause.{is_enabled, is_available, unavailable_reason,
 * price_percent, monthly_price, starts_at, ends_at, max_months,
 * paused_months, cap_months, window_months}; and subscription.{status,
 * pause_starts_at, pause_until} of GET …/billing.
 */

import type { Schema } from "@/api/types";

import type { BillingOverview } from "./billing";

export type SubscriptionLifecycle = Schema<"SubscriptionLifecycleView">;
export type CancellationReason = Schema<"CancellationReason">;
export type RetentionOffer = Schema<"RetentionOfferView">;
export type RetentionOfferKind = Schema<"RetentionOfferKind">;
export type PauseOptions = Schema<"PauseOptionsView">;
export type PauseUnavailableReason = Schema<"PauseUnavailableReason">;

/** The reasons in the order the dialog lists them. */
export const CANCELLATION_REASONS: readonly CancellationReason[] = [
  "seasonal_break",
  "not_enough_use",
  "too_expensive",
  "answer_quality",
  "missing_feature",
  "switched_provider",
  "closing_business",
  "other",
];

/** The longest owner's note the API takes. */
export const CANCELLATION_DETAILS_MAX = 1000;

/** The offer the dialog makes for a reason, or null. */
export function offerFor(
  lifecycle: SubscriptionLifecycle | undefined,
  reason: CancellationReason | null,
): RetentionOffer | null {
  if (!lifecycle || reason === null) {
    return null;
  }
  return lifecycle.offers?.find((choice) => choice.reason === reason)?.offer ?? null;
}

/** The owner's own words, trimmed; null when empty. */
export function cancellationDetails(text: string): string | null {
  const trimmed = text.trim();
  return trimmed === "" ? null : trimmed.slice(0, CANCELLATION_DETAILS_MAX);
}

/** What the pause card shows. */
export type PauseCardState =
  | { kind: "hidden" }
  | { kind: "paused"; until: number }
  | { kind: "scheduled"; startsAt: number; until: number }
  | { kind: "available"; options: PauseOptions }
  | { kind: "unavailable"; reason: Exclude<PauseUnavailableReason, "feature_off" | "already_paused"> };

export function pauseCardState(
  overview: BillingOverview | undefined,
  lifecycle: SubscriptionLifecycle | undefined,
): PauseCardState {
  const subscription = overview?.subscription;
  if (!subscription || !lifecycle) {
    return { kind: "hidden" };
  }
  if (subscription.status === "paused" && subscription.pause_until) {
    return { kind: "paused", until: subscription.pause_until };
  }
  if (subscription.pause_starts_at && subscription.pause_until) {
    return { kind: "scheduled", startsAt: subscription.pause_starts_at, until: subscription.pause_until };
  }
  const pause = lifecycle.pause;
  // Before the platform turns pausing on, the card is not shown at all.
  if (!pause.is_enabled) {
    return { kind: "hidden" };
  }
  if (pause.is_available && pause.starts_at) {
    return { kind: "available", options: pause };
  }
  const reason = pause.unavailable_reason;
  if (reason === "not_active" || reason === "not_monthly" || reason === "allowance_used") {
    return { kind: "unavailable", reason };
  }
  return { kind: "hidden" };
}

/** 1 … max: the months a pause may last now. */
export function pauseMonthChoices(maxMonths: number): number[] {
  return Array.from({ length: Math.max(0, maxMonths) }, (_, index) => index + 1);
}

/** When a pause of `months` would end (the API's dates, in the business's calendar); null if unknown. */
export function pauseEndFor(options: PauseOptions | undefined, months: number): number | null {
  return options?.ends_at?.[months - 1] ?? null;
}

/** A chosen length that is still allowed, else one month. */
export function allowedPauseMonths(months: number, maxMonths: number): number {
  return months >= 1 && months <= maxMonths ? months : 1;
}
