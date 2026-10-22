/**
 * Pure helpers of the card on file on the Billing page: how the saved card
 * reads, whether it still works, where the retries of a declined charge
 * stand and the trial's "Save card" prompt.
 *
 * Fields of the API this relies on: GET …/billing/payment-method
 * (`PaymentMethodView`: provider, card.{brand, last_digits, expiry_month,
 * expiry_year, saved_at}, has_auto_debit, can_save_card, trial_ends_at,
 * is_trial_card_prompt_due, retry.{last_attempt, last_outcome,
 * next_retry_at, grace_until}) and POST …/billing/payment-method
 * (`CardSetupSessionView`: provider, url, payment_order_id).
 */

import type { Schema } from "@/api/types";
import type { MessageKey } from "@/i18n/translate";

import type { BillingNotice } from "./billing";

export type PaymentMethodView = Schema<"PaymentMethodView">;
export type PaymentCardView = Schema<"PaymentCardView">;
export type PaymentRetryView = Schema<"PaymentRetryView">;
export type PaymentProvider = Schema<"PaymentProvider">;
type PaymentRetryOutcome = Schema<"PaymentRetryOutcome">;
export type CardSetupSession = Schema<"CardSetupSessionView">;

/** Retries of a declined automatic charge: on days 1, 3 and 6 of the grace period. */
export const PAYMENT_RETRY_ATTEMPTS = 3;

/** A card saved this long before the owner came back still counts as the one just saved. */
const CARD_RETURN_WINDOW_US = 30 * 60 * 1_000_000;

/** Payment services by their own names (never translated). */
export const PROVIDER_NAMES: Record<PaymentProvider, string> = {
  flitt: "Flitt",
  stripe: "Stripe",
};

/** Card networks as they write their names; others are shown as the provider reports them. */
const BRAND_NAMES: Record<string, string> = {
  VISA: "Visa",
  MASTERCARD: "Mastercard",
  MASTER: "Mastercard",
  MAESTRO: "Maestro",
  AMEX: "American Express",
  AMERICAN_EXPRESS: "American Express",
  DISCOVER: "Discover",
  DINERS: "Diners Club",
  JCB: "JCB",
  UNIONPAY: "UnionPay",
  MIR: "Mir",
};

const RETRY_OUTCOME_TEXTS: Record<PaymentRetryOutcome, MessageKey> = {
  claimed: "billingCard.retry.outcomes.claimed",
  approved: "billingCard.retry.outcomes.approved",
  declined: "billingCard.retry.outcomes.declined",
  processing: "billingCard.retry.outcomes.processing",
  failed: "billingCard.retry.outcomes.failed",
  not_possible: "billingCard.retry.outcomes.not_possible",
  skipped: "billingCard.retry.outcomes.skipped",
};

/** "VISA" -> "Visa"; null when the provider did not say. */
export function cardBrandName(brand: string | null | undefined): string | null {
  const trimmed = brand?.trim() ?? "";
  if (trimmed === "") {
    return null;
  }
  return BRAND_NAMES[trimmed.toUpperCase().replace(/[\s-]+/g, "_")] ?? trimmed;
}

/** "•••• 4242", or null without the last digits. */
export function maskedCardNumber(card: Pick<PaymentCardView, "last_digits">): string | null {
  return card.last_digits ? `•••• ${card.last_digits}` : null;
}

/** The expiry as printed on cards ("04/31"); null when unknown. */
export function cardExpiryText(card: Pick<PaymentCardView, "expiry_month" | "expiry_year">): string | null {
  if (!card.expiry_month || !card.expiry_year) {
    return null;
  }
  return `${String(card.expiry_month).padStart(2, "0")}/${String(card.expiry_year % 100).padStart(2, "0")}`;
}

export type CardExpiryState = "valid" | "expiring" | "expired" | "unknown";

/**
 * Whether the card still works: a card is valid through the last day of its
 * expiry month; "expiring" is this month or the next, so the owner has time
 * to replace it before a charge is declined.
 */
export function cardExpiryState(card: Pick<PaymentCardView, "expiry_month" | "expiry_year">, now: Date): CardExpiryState {
  if (!card.expiry_month || !card.expiry_year) {
    return "unknown";
  }
  const monthsLeft = card.expiry_year * 12 + (card.expiry_month - 1) - (now.getFullYear() * 12 + now.getMonth());
  if (monthsLeft < 0) {
    return "expired";
  }
  return monthsLeft <= 1 ? "expiring" : "valid";
}

/** "Update card" when a card is saved, "Save card" before. */
export function cardActionText(view: Pick<PaymentMethodView, "card">): MessageKey {
  return view.card ? "billingCard.update" : "billingCard.save";
}

/** What the retry block says first: the last retry and how it went, or that the charge was declined. */
export function retryStatusText(retry: PaymentRetryView): MessageKey {
  return retry.last_outcome && retry.last_attempt ? RETRY_OUTCOME_TEXTS[retry.last_outcome] : "billingCard.retry.declined";
}

/**
 * The trial's own notice gives way to the "Save card" prompt (from day 10
 * of a trial without a card), so the page asks once.
 */
export function withoutTrialNotice(notices: readonly BillingNotice[], view: PaymentMethodView | undefined): BillingNotice[] {
  return isCardPromptShown(view) ? notices.filter((notice) => notice.kind !== "trial") : [...notices];
}

export function isCardPromptShown(view: PaymentMethodView | undefined): boolean {
  return Boolean(view?.is_trial_card_prompt_due && view.can_save_card);
}

/**
 * Back from the provider's page: the card shows once the provider confirms
 * it. A card saved shortly before the owner came back is the new one.
 */
export function isCardConfirmed(view: Pick<PaymentMethodView, "card"> | undefined, returnedAtUs: number): boolean {
  const savedAt = view?.card?.saved_at;
  return savedAt !== undefined && savedAt >= returnedAtUs - CARD_RETURN_WINDOW_US;
}

/** Where the provider's page sends the owner back: this billing page. */
export function cardReturnUrl(origin: string, billingPath: string): string {
  return `${origin.replace(/\/$/, "")}${billingPath}?card=return`;
}
