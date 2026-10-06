/**
 * Pure helpers of the Billing page: status badges, the notices above the
 * page, which plan actions are possible and plan prices per billing period.
 *
 * Fields of the API this page relies on (GET /billing, GET /v1/catalog/plans):
 * subscription.{plan_key, plan_name, billing_period, status, price,
 * trial_ends_at, period_start, period_end, grace_until, has_auto_debit},
 * usage.{used/included voice minutes and dialogs, *_usage_percent,
 * overage_voice_minutes, overage_cost, overage_price_per_minute},
 * invoices[].{id, kind, description, status, amount, period_*, issued_at},
 * is_trial_available, service_mode; plan quotes with monthly/annual (and
 * local_*) prices, annual_discount_percent, trial_days, setup fee, package.
 */

import type { Schema } from "@/api/types";
import type { BadgeTone } from "@/components/ui";
import { usageLevel } from "@/lib/usage";

export type BillingOverview = Schema<"BillingOverview">;
export type SubscriptionView = Schema<"SubscriptionView">;
export type InvoiceView = Schema<"InvoiceView">;
export type PlanQuote = Schema<"PlanQuote">;
export type QuotedMoney = Schema<"QuotedMoney">;
export type BillingPeriod = Schema<"BillingPeriod">;
export type SubscriptionStatus = Schema<"SubscriptionStatus">;
export type InvoiceStatus = Schema<"InvoiceStatus">;
export type CheckoutSession = Schema<"CheckoutSessionView">;

const MICROSECONDS_PER_DAY = 86_400_000_000;

export const SUBSCRIPTION_STATUS_TONES: Record<SubscriptionStatus, BadgeTone> = {
  incomplete: "warning",
  trialing: "info",
  active: "success",
  past_due: "danger",
  cancelled: "neutral",
  paused: "info",
};

export const INVOICE_STATUS_TONES: Record<InvoiceStatus, BadgeTone> = {
  issued: "warning",
  paid: "success",
  failed: "danger",
  void: "neutral",
};

/** Invoices that still wait for money. */
export function isInvoiceOpen(invoice: Pick<InvoiceView, "status">): boolean {
  return invoice.status === "issued" || invoice.status === "failed";
}

/** Newest first. */
export function sortInvoices(invoices: readonly InvoiceView[] | undefined): InvoiceView[] {
  return [...(invoices ?? [])].sort((left, right) => right.issued_at - left.issued_at);
}

/** Whole days from now to a moment (0 once it has passed). */
export function daysUntil(targetUs: number, nowUs: number): number {
  return Math.max(0, Math.ceil((targetUs - nowUs) / MICROSECONDS_PER_DAY));
}

/**
 * Whether the owner can open the payment page: there is a subscription and
 * something to pay (checkout answers 409 when automatic payment is on and
 * nothing is due).
 */
export function canPay(overview: BillingOverview): boolean {
  const subscription = overview.subscription;
  if (!subscription) {
    return false;
  }
  const hasOpenInvoices = (overview.invoices ?? []).some(isInvoiceOpen);
  // A pause covers what comes next: only its own bill is paid.
  if (subscription.pause_until) {
    return hasOpenInvoices;
  }
  return hasOpenInvoices || !(subscription.status === "active" && subscription.has_auto_debit);
}

/** A subscription that is not cancelled yet and was ever started (a trial or a payment). */
export function canCancel(overview: BillingOverview): boolean {
  const status = overview.subscription?.status;
  return status !== undefined && status !== "cancelled" && status !== "incomplete";
}

/**
 * Whether choosing a plan means paying for it now (POST …/billing/subscribe):
 * no subscription, one waiting for its first payment, an overdue one or a
 * cancelled one. A trial or an active subscription switches plans instead.
 */
/**
 * What an owner without a subscription is told: the free trial starts by
 * itself at the first go-live, can be started now, or was already used.
 */
export function noSubscriptionText(
  overview: Pick<BillingOverview, "does_trial_start_at_go_live" | "is_trial_available">,
): "billing.noSubscriptionTrialAtGoLive" | "billing.noSubscriptionDescription" | "billing.noSubscriptionNoTrial" {
  if (overview.does_trial_start_at_go_live) return "billing.noSubscriptionTrialAtGoLive";
  return overview.is_trial_available ? "billing.noSubscriptionDescription" : "billing.noSubscriptionNoTrial";
}

export function needsSubscription(overview: BillingOverview): boolean {
  const status = overview.subscription?.status;
  return status === undefined || status === "incomplete" || status === "past_due" || status === "cancelled";
}

/** Something the owner should know, most urgent first. */
export type BillingNotice =
  | { kind: "leadsOnly" }
  | { kind: "incomplete" }
  | { kind: "pastDue"; graceUntil: number | null }
  | { kind: "cancelled"; until: number }
  | { kind: "unpaid"; count: number }
  | { kind: "trial"; endsAt: number; daysLeft: number }
  | { kind: "usage"; unit: "voice" | "dialogs"; percent: number; isExceeded: boolean };

export function billingNotices(overview: BillingOverview, nowUs: number): BillingNotice[] {
  const notices: BillingNotice[] = [];
  const subscription = overview.subscription;
  // A seasonal pause takes requests only by choice; its card says so.
  if (overview.service_mode === "leads_only" && subscription?.status !== "paused") {
    notices.push({ kind: "leadsOnly" });
  }
  if (subscription?.status === "past_due") {
    notices.push({ kind: "pastDue", graceUntil: subscription.grace_until ?? null });
  }
  if (subscription?.status === "cancelled") {
    notices.push({ kind: "cancelled", until: subscription.period_end });
  }
  if (subscription?.status === "incomplete") {
    notices.push({ kind: "incomplete" });
  }
  const unpaid = (overview.invoices ?? []).filter(isInvoiceOpen).length;
  if (unpaid > 0 && subscription?.status !== "past_due" && subscription?.status !== "incomplete") {
    notices.push({ kind: "unpaid", count: unpaid });
  }
  if (subscription?.status === "trialing") {
    const endsAt = subscription.trial_ends_at ?? subscription.period_end;
    notices.push({ kind: "trial", endsAt, daysLeft: daysUntil(endsAt, nowUs) });
  }
  const usage = overview.usage;
  if (usage) {
    const units: [unit: "voice" | "dialogs", percent: number | null | undefined][] = [
      ["voice", usage.voice_usage_percent],
      ["dialogs", usage.dialog_usage_percent],
    ];
    for (const [unit, percent] of units) {
      const level = usageLevel(percent);
      if ((level === "warning" || level === "exceeded") && percent !== null && percent !== undefined) {
        notices.push({ kind: "usage", unit, percent, isExceeded: level === "exceeded" });
      }
    }
  }
  return notices;
}

/** The price to show for a plan: local currency when known, else the plan currency (EUR). */
export function planPrice(quote: PlanQuote, period: BillingPeriod): QuotedMoney {
  return period === "annual"
    ? (quote.local_annual_price ?? quote.annual_price)
    : (quote.local_monthly_price ?? quote.monthly_price);
}

export function planSetupFee(quote: PlanQuote): QuotedMoney {
  return quote.local_setup_fee ?? quote.setup_fee;
}

export function planOveragePrice(quote: PlanQuote): QuotedMoney {
  return quote.local_overage_price_per_minute ?? quote.overage_price_per_minute;
}

/** A yearly price per month, in minor units of its currency. */
export function monthlyEquivalentMinor(annual: QuotedMoney): number {
  return Math.round(annual.money.amount_minor / 12);
}

/** Whether any shown plan price is a conversion by exchange rate. */
export function hasEstimatedPrices(quotes: readonly PlanQuote[], period: BillingPeriod): boolean {
  return quotes.some((quote) =>
    [planPrice(quote, period), planSetupFee(quote), planOveragePrice(quote)].some((price) => price.is_estimated),
  );
}

export type PlanAction = "switch" | "trial" | "subscribe";

export interface PlanCardActions {
  /** The subscription is on this plan and billing period. */
  isCurrent: boolean;
  /** Buttons of the card, the main one first (empty: nothing to do). */
  actions: PlanAction[];
}

/**
 * What the owner can do with a plan card in the chosen billing period.
 *
 * A running trial or an active subscription switches plans. Otherwise (no
 * subscription, one waiting for its first payment, overdue or cancelled) the
 * owner subscribes and pays now; the free trial comes first while it is
 * still available and the plan has one.
 */
export function planActions(quote: PlanQuote, period: BillingPeriod, overview: BillingOverview): PlanCardActions {
  const subscription = overview.subscription;
  const isCurrent = subscription?.plan_key === quote.plan_key && subscription?.billing_period === period;
  if (subscription?.status === "paused") {
    // A paused subscription keeps its plan until it is resumed.
    return { isCurrent, actions: [] };
  }
  if (subscription && !needsSubscription(overview)) {
    return { isCurrent, actions: isCurrent ? [] : ["switch"] };
  }
  const canTrial = overview.is_trial_available && quote.trial_days > 0;
  return { isCurrent, actions: canTrial ? ["trial", "subscribe"] : ["subscribe"] };
}

/** The largest yearly discount of the plans (for "Yearly −15 %"). */
export function maxAnnualDiscount(quotes: readonly PlanQuote[]): number {
  return quotes.reduce((max, quote) => Math.max(max, quote.annual_discount_percent), 0);
}

/** Where the payment page sends the payer back: this billing page. */
export function checkoutReturnUrl(origin: string, billingPath: string): string {
  return `${origin.replace(/\/$/, "")}${billingPath}?checkout=return`;
}

/** Money as text with "≈" for converted amounts. */
export function quotedMoneyText(price: QuotedMoney, formatMoney: (minor: number, currency: string) => string): string {
  const text = formatMoney(price.money.amount_minor, price.money.currency_code);
  return price.is_estimated ? `≈ ${text}` : text;
}
