/**
 * What the value calculator compares with: the plans at the price they are
 * billed at (lari in Georgia, euros elsewhere, never a conversion) and the
 * kinds of business with their typical check in euros.
 */

import type { NicheSummaryView } from "@/api/types";
import { minorToMajor } from "@/lib/format";

import { billed, type PlanQuote } from "./prices";

export interface RoiPlan {
  key: string;
  name: string;
  /** The monthly price in the billed currency, major units. */
  monthly: number;
  /** The same plan's monthly price in euros, major units (the scale of a niche's typical check). */
  monthlyEuro: number;
  currency: string;
}

export interface RoiNiche {
  key: string;
  name: string;
  /** A typical check in euros, major units; null where checks vary too much to suggest one. */
  typicalCheckEuro: number | null;
}

export function roiPlans(quotes: readonly PlanQuote[]): RoiPlan[] {
  return quotes.map((quote) => {
    const money = billed(quote.local_monthly_price, quote.monthly_price).money;
    const euros = quote.monthly_price.money;
    return {
      key: quote.plan_key,
      name: quote.name,
      monthly: minorToMajor(money.amount_minor, money.currency_code),
      monthlyEuro: minorToMajor(euros.amount_minor, euros.currency_code),
      currency: money.currency_code,
    };
  });
}

export function roiNiches(niches: readonly NicheSummaryView[]): RoiNiche[] {
  return niches.map((niche) => {
    const check = niche.typical_check ?? null;
    return {
      key: niche.key,
      name: niche.name,
      typicalCheckEuro: check && check.currency_code === "EUR" ? minorToMajor(check.amount_minor, check.currency_code) : null,
    };
  });
}

/** The plan a kind of business usually starts with (its first recommended plan on offer), else the first. */
export function suggestedPlan(plans: readonly RoiPlan[], recommended: readonly string[] = []): RoiPlan | null {
  for (const key of recommended) {
    const plan = plans.find((candidate) => candidate.key === key);
    if (plan) {
      return plan;
    }
  }
  return plans[0] ?? null;
}
