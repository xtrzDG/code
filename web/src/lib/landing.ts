/**
 * Helpers of the public landing page: which country's prices to show and
 * the trial every plan shares. Prices themselves: ./publicSite/prices.ts.
 */

import type { Schema } from "@/api/types";

import { guessCountryCode } from "./countries";

export type PlanQuote = Schema<"PlanQuote">;

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
 * The country whose prices the page shows. A country the visitor picked
 * (?country=) is always shown. Otherwise the page guesses only among the
 * countries with a price book (`priced`: the plans are billed in their own
 * currency), so nobody lands on prices that are mere conversions: the
 * country a hosting proxy reports for the visitor, else one guessed from
 * the browser languages, else Georgia (the first market) or the first
 * priced country.
 */
export function pickLandingCountry(options: {
  requested?: string | null;
  available: readonly string[];
  priced?: readonly string[];
  geoCountry?: string | null;
  acceptLanguage?: string | null;
}): string | null {
  const available = new Set(options.available.map((code) => code.toUpperCase()));
  const requested = options.requested?.trim().toUpperCase();
  if (requested && available.has(requested)) {
    return requested;
  }
  const priced = (options.priced ?? options.available).filter((code) => available.has(code.toUpperCase()));
  const geo = options.geoCountry?.trim().toUpperCase();
  if (geo && priced.some((code) => code.toUpperCase() === geo)) {
    return geo;
  }
  return guessCountryCode(acceptLanguageTags(options.acceptLanguage), priced) ?? options.available[0]?.toUpperCase() ?? null;
}

/** The free trial every plan shares ("14 days free on every plan"), or null when they differ or have none. */
export function sharedTrialDays(quotes: readonly PlanQuote[]): number | null {
  const days = new Set(quotes.map((quote) => quote.trial_days));
  const [only] = [...days];
  return days.size === 1 && only !== undefined && only > 0 ? only : null;
}
