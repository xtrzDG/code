/**
 * The admin overview's spend tile (GET /v1/admin/spend): amounts come in
 * micro-USD; the tile shows them as dollars and cents, flags a day far
 * above the week before as the `spend_spike` alert does (3 times the
 * daily mean, from $5), and colours the budget bar by how much is used.
 */

import type { BadgeTone } from "@/components/ui";
import type { Schema } from "@/api/types";

export type PlatformSpend = Schema<"PlatformSpendView">;
export type SpendProvider = Schema<"SpendProvider">;
export type BrakedBusiness = Schema<"BusinessSpendMark">;

const MICRO_USD_PER_CENT = 10_000;
/** The `spend_spike` rule of ops/alerts/spend_spike.yaml. */
export const SPIKE_RATIO = 3;
export const SPIKE_FLOOR_MICRO_USD = 5_000_000;
/** The `spend_budget` rule fires at 80% of the daily budget. */
export const BUDGET_ALERT_PERCENT = 80;

/** Micro-USD → US cents, for `formatMoney(cents, "USD", locale)`. */
export function microUsdToCents(microUsd: number): number {
  return Math.round(microUsd / MICRO_USD_PER_CENT);
}

/** Whether today is far above the week before, as the spend alert sees it. */
export function isSpendSpike(spend: Pick<PlatformSpend, "total_micro_usd" | "week_daily_mean_micro_usd">): boolean {
  return (
    spend.total_micro_usd >= SPIKE_FLOOR_MICRO_USD &&
    spend.total_micro_usd > SPIKE_RATIO * spend.week_daily_mean_micro_usd
  );
}

/** The budget bar's tone: calm, then warning from the alert's 80%, danger past the budget. */
export function budgetTone(percent: number): Extract<BadgeTone, "info" | "warning" | "danger"> {
  if (percent >= 100) {
    return "danger";
  }
  return percent >= BUDGET_ALERT_PERCENT ? "warning" : "info";
}

/** Providers with spend, largest first (a quiet provider is left out). */
export function spendingProviders(spend: PlatformSpend): PlatformSpend["providers"] {
  return spend.providers.filter((provider) => provider.spend_micro_usd > 0).sort((a, b) => b.spend_micro_usd - a.spend_micro_usd);
}
