/**
 * Honest prices on the public site. The price a visitor reads first is
 * always one the platform bills: the price book's amount where the
 * country has one (lari in Georgia, the plans' own euros in the euro
 * area), else the plan's euros. A conversion into the visitor's currency
 * comes second, rounded to whole units and marked "≈" ("≈ $112"), never
 * a raw "$1,145.97".
 */

import type { Schema } from "@/api/types";
import { minorToMajor } from "@/lib/format";
import { numberFormat } from "@/lib/intl/formatters";

export type PlanQuote = Schema<"PlanQuote">;
export type QuotedMoney = Schema<"QuotedMoney">;
type Money = QuotedMoney["money"];
type ExchangeRateQuote = Schema<"ExchangeRateQuote">;

/** A money amount as text; whole amounts without decimals ("€99", "0,15 €"). */
export function moneyLabel(money: Money, locale: string): string {
  const major = minorToMajor(money.amount_minor, money.currency_code);
  const isWhole = Number.isInteger(major);
  return numberFormat(locale, {
    style: "currency",
    currency: money.currency_code,
    ...(isWhole ? { minimumFractionDigits: 0, maximumFractionDigits: 0 } : {}),
  }).format(major);
}

/** A conversion for orientation: "≈ $112" (whole units, always). */
export function approximateLabel(money: Money, locale: string): string {
  const major = Math.round(minorToMajor(money.amount_minor, money.currency_code));
  const text = numberFormat(locale, {
    style: "currency",
    currency: money.currency_code,
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(major);
  return `≈ ${text}`;
}

/** The billed price: the price book's local amount when it is not a conversion, else the plan's own. */
function billed(local: QuotedMoney | null | undefined, plan: QuotedMoney): QuotedMoney {
  return local && !local.is_estimated ? local : plan;
}

export interface PlanPriceLines {
  /** Monthly price the plan is billed at. */
  monthly: string;
  /** Twelve months with the annual discount, in the same currency. */
  annual: string;
  /** The done-for-you setup fee, in the same currency. */
  setupFee: string;
  /** An extra voice minute, in the same currency. */
  overage: string;
  /** The billed currency (EUR or the price book's). */
  currency: string;
  /**
   * Beside the monthly price: the conversion into the visitor's currency
   * ("≈ $112"), or the plan's euros beside a local price-book amount.
   */
  secondary: { kind: "converted" | "euros"; text: string } | null;
}

/** What one plan card shows, in this order. */
export function planPriceLines(quote: PlanQuote, locale: string): PlanPriceLines {
  const monthly = billed(quote.local_monthly_price, quote.monthly_price);
  const local = quote.local_monthly_price ?? null;
  let secondary: PlanPriceLines["secondary"] = null;
  if (local && local.is_estimated) {
    secondary = { kind: "converted", text: approximateLabel(local.money, locale) };
  } else if (local && local.money.currency_code !== quote.monthly_price.money.currency_code) {
    secondary = { kind: "euros", text: moneyLabel(quote.monthly_price.money, locale) };
  }
  return {
    monthly: moneyLabel(monthly.money, locale),
    annual: moneyLabel(billed(quote.local_annual_price, quote.annual_price).money, locale),
    setupFee: moneyLabel(billed(quote.local_setup_fee, quote.setup_fee).money, locale),
    overage: moneyLabel(billed(quote.local_overage_price_per_minute, quote.overage_price_per_minute).money, locale),
    currency: monthly.money.currency_code,
    secondary,
  };
}

/** Whether any plan shows a conversion (the page then names the rate behind it). */
export function hasConversion(quotes: readonly PlanQuote[]): boolean {
  return quotes.some((quote) => quote.local_monthly_price?.is_estimated === true);
}

export type RateSourceKind = "official" | "planning";

/**
 * Who set the rate behind a conversion: a central bank's published rate
 * (National Bank of Georgia, ECB) or the platform's own planning rate, the
 * fallback while no published rate is stored. A rate built from both is a
 * planning rate: it is only as good as its weakest part.
 */
export function rateSourceKind(rate: Pick<ExchangeRateQuote, "sources">): RateSourceKind {
  const sources = rate.sources ?? [];
  return sources.length === 0 || sources.includes("planning") ? "planning" : "official";
}
