/**
 * Helpers of the public landing page: which country's prices to show and
 * how to present a plan quote of GET /v1/catalog/plans.
 */

import type { Schema } from "@/api/types";

import { guessCountryCode } from "./countries";

export type PlanQuote = Schema<"PlanQuote">;
export type QuotedMoney = Schema<"QuotedMoney">;

/** The language tags of an Accept-Language header, best first ("ru-RU,ka;q=0.8" -> ["ru-RU", "ka"]). */
export function acceptLanguageTags(header: string | null | undefined): string[] {
  if (!header) {
    return [];
  }
  return header
    .split(",")
    .map((part, index) => {
      const [tag = "", ...parameters] = part.trim().split(";");
      const q = parameters.map((parameter) => parameter.trim()).find((parameter) => parameter.startsWith("q="));
      const quality = q ? Number(q.slice(2)) : 1;
      return { tag: tag.trim(), quality: Number.isFinite(quality) ? quality : 0, index };
    })
    .filter((entry) => entry.tag !== "" && entry.tag !== "*" && entry.quality > 0)
    .sort((left, right) => right.quality - left.quality || left.index - right.index)
    .map((entry) => entry.tag);
}

/**
 * The country whose prices the page shows: the one picked (?country=), else
 * the country a hosting proxy reports for the visitor, else a guess from the
 * browser languages, else Georgia (the first market) or the first available.
 */
export function pickLandingCountry(options: {
  requested?: string | null;
  available: readonly string[];
  geoCountry?: string | null;
  acceptLanguage?: string | null;
}): string | null {
  const allowed = new Set(options.available.map((code) => code.toUpperCase()));
  for (const candidate of [options.requested, options.geoCountry]) {
    const code = candidate?.trim().toUpperCase();
    if (code && allowed.has(code)) {
      return code;
    }
  }
  return guessCountryCode(acceptLanguageTags(options.acceptLanguage), options.available);
}

/** The free trial every plan shares ("14 days free on every plan"), or null when they differ or have none. */
export function sharedTrialDays(quotes: readonly PlanQuote[]): number | null {
  const days = new Set(quotes.map((quote) => quote.trial_days));
  const [only] = [...days];
  return days.size === 1 && only !== undefined && only > 0 ? only : null;
}

/** A price as text, "≈ " in front when it was converted by an exchange rate. */
export function moneyText(price: QuotedMoney): string {
  return price.is_estimated ? `≈ ${price.text}` : price.text;
}

/**
 * The monthly price in the country's currency when the price book or an
 * official rate knows it, and the plan's own price (euros) beside it when
 * the two differ.
 */
export function landingPrices(quote: PlanQuote): { monthly: QuotedMoney; annual: QuotedMoney; setupFee: QuotedMoney; overage: QuotedMoney; plan: QuotedMoney | null } {
  const local = quote.local_monthly_price ?? null;
  return {
    monthly: local ?? quote.monthly_price,
    annual: quote.local_annual_price ?? quote.annual_price,
    setupFee: quote.local_setup_fee ?? quote.setup_fee,
    overage: quote.local_overage_price_per_minute ?? quote.overage_price_per_minute,
    plan: local && local.money.currency_code !== quote.monthly_price.money.currency_code ? quote.monthly_price : null,
  };
}

/** Whether any price the card shows is a conversion by exchange rate. */
export function hasEstimatedPrice(quote: PlanQuote): boolean {
  const prices = landingPrices(quote);
  return [prices.monthly, prices.annual, prices.setupFee, prices.overage].some((price) => price.is_estimated);
}
