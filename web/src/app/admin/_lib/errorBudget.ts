/**
 * The error budget card of /admin/system (GET /v1/admin/system/error-budget,
 * docs/operations/slo.md). The budget comes in permille (1000 untouched, 0
 * spent, below 0 overspent) and the burn rate in percent of the pace that
 * spends the budget in exactly 28 days; the card shows both as people read
 * them: a share of the budget left and "times as fast".
 */

import type { BadgeTone } from "@/components/ui";
import type { Schema } from "@/api/types";

export type ErrorBudget = Schema<"ErrorBudgetView">;
export type ObjectiveBudget = Schema<"ObjectiveBudgetView">;
type ServiceLevelSeries = ObjectiveBudget["series"];

const PERMILLE = 1000;
const PERCENT = 100;
/** Below half the budget left, deploys name their rollback (the budget policy). */
const POLICY_WARNING_PERMILLE = 500;
/** The slow burn-rate rules of ops/alerts fire above 6 times the sustainable pace. */
const SLOW_BURN_PERCENT = 600;

/** The objectives in the order the card shows them. */
const SERIES_ORDER: readonly ServiceLevelSeries[] = ["inbound_answered", "api_availability"];

/** The share of the budget left, 0..1 (an overspent budget is 0 on the meter). */
export function budgetLeftShare(permille: number): number {
  return Math.min(1, Math.max(0, permille / PERMILLE));
}

/** The budget policy's tone: calm, warning under half left, danger when spent. */
export function budgetTone(permille: number): Extract<BadgeTone, "success" | "warning" | "danger"> {
  if (permille <= 0) {
    return "danger";
  }
  return permille < POLICY_WARNING_PERMILLE ? "warning" : "success";
}

/** The burn rate as a multiple of the sustainable pace (1440% → 14.4). */
export function burnMultiple(percent: number): number {
  return percent / PERCENT;
}

/** How the last hour burned: within the pace, above it, or as fast as a burn alert fires. */
export function burnTone(percent: number): Extract<BadgeTone, "neutral" | "warning" | "danger"> {
  if (percent > SLOW_BURN_PERCENT) {
    return "danger";
  }
  return percent > PERCENT ? "warning" : "neutral";
}

/** The objectives of the view, in the card's order (an unknown series last). */
export function orderedObjectives(view: ErrorBudget): ObjectiveBudget[] {
  const rank = (series: ServiceLevelSeries) => {
    const index = SERIES_ORDER.indexOf(series);
    return index < 0 ? SERIES_ORDER.length : index;
  };
  return [...(view.objectives ?? [])].sort((a, b) => rank(a.series) - rank(b.series));
}

/** The card's overall state: the worst budget among the objectives. */
export function overallTone(view: ErrorBudget): Extract<BadgeTone, "success" | "warning" | "danger"> {
  const tones = orderedObjectives(view).map((objective) => budgetTone(objective.budget_left_permille));
  if (tones.includes("danger")) {
    return "danger";
  }
  return tones.includes("warning") ? "warning" : "success";
}

/** Whether `record_sli` wrote any hourly row yet. */
export function hasMeasurements(view: ErrorBudget): boolean {
  return view.measured_since != null && view.measured_until != null;
}

/** Whether the last measured hour's answer p95 missed its target. */
export function isLatencyOverTarget(view: ErrorBudget): boolean {
  const p95 = view.latency.last_hour_p95_ms;
  return p95 != null && p95 > view.latency.target_ms;
}
