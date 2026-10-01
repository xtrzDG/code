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
import { usageLevel } from "@/components/workspace/helpers";

export type BillingOverview = Schema<"BillingOverview">;
export type SubscriptionView = Schema<"SubscriptionView">;
export type InvoiceView = Schema<"InvoiceView">;
export type PlanQuote = Schema<"PlanQuote">;
export type QuotedMoney = Schema<"QuotedMoney">;
export type BillingPeriod = Schema<"BillingPeriod">;
export type SubscriptionStatus = Schema<"SubscriptionStatus">;
export type InvoiceStatus = Schema<"InvoiceStatus">;

const MICROSECONDS_PER_DAY = 86_400_000_000;

export const SUBSCRIPTION_STATUS_TONES: Record<SubscriptionStatus, BadgeTone> = {
  trialing: "info",
  active: "success",
  past_due: "danger",
  cancelled: "neutral",
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
  return hasOpenInvoices || !(subscription.status === "active" && subscription.has_auto_debit);
}

export function canCancel(overview: BillingOverview): boolean {
  return overview.subscription !== null && overview.subscription !== undefined && overview.subscription.status !== "cancelled";
}

/** Something the owner should know, most urgent first. */
export type BillingNotice =
  | { kind: "leadsOnly" }
  | { kind: "pastDue"; graceUntil: number | null }
  | { kind: "cancelled"; until: number }
  | { kind: "unpaid"; count: number }
  | { kind: "trial"; endsAt: number; daysLeft: number }
  | { kind: "usage"; unit: "voice" | "dialogs"; percent: number; isExceeded: boolean };

export function billingNotices(overview: BillingOverview, nowUs: number): BillingNotice[] {
  const notices: BillingNotice[] = [];
  const subscription = overview.subscription;
  if (overview.service_mode === "leads_only") {
    notices.push({ kind: "leadsOnly" });
  }
  if (subscription?.status === "past_due") {
    notices.push({ kind: "pastDue", graceUntil: subscription.grace_until ?? null });
  }
  if (subscription?.status === "cancelled") {
    notices.push({ kind: "cancelled", until: subscription.period_end });
  }
  const unpaid = (overview.invoices ?? []).filter(isInvoiceOpen).length;
  if (unpaid > 0 && subscription?.status !== "past_due") {
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

export type PlanAction = "current" | "switch" | "trial" | "unavailable";

/** What the owner can do with a plan card in the chosen billing period. */
export function planAction(quote: PlanQuote, period: BillingPeriod, overview: BillingOverview): PlanAction {
  const subscription = overview.subscription;
  if (subscription) {
    return subscription.plan_key === quote.plan_key && subscription.billing_period === period ? "current" : "switch";
  }
  return overview.is_trial_available && quote.trial_days > 0 ? "trial" : "unavailable";
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
