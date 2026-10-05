/**
 * Pure helpers of a run compared with the live version's run: what got
 * worse, what got better and by how much (GET …/autotest-run, `comparison`).
 */

import type { Schema } from "@/api/types";

import { formatScore } from "./autotests";
import type { StatusTone } from "./versions";

export type AutotestRunComparison = Schema<"AutotestRunComparisonView">;
export type AutotestOutcomeChange = Schema<"AutotestOutcomeChangeView">;
export type AutotestScoreChange = Schema<"AutotestScoreChangeView">;
export type AutotestCriterionChange = Schema<"AutotestCriterionChangeView">;

/** Under this a change rounds to "0.0" and has no direction. */
const VISIBLE_CHANGE = 0.05;

/** "+0.6", "−0.8" or "0.0" in the UI language: a sign whenever it moved. */
export function formatScoreChange(change: number, locale: string): string {
  const sign = change >= VISIBLE_CHANGE ? "+" : change <= -VISIBLE_CHANGE ? "\u2212" : "";
  return `${sign}${formatScore(Math.abs(change), locale)}`;
}

/** Up is good, down is bad; a change under a tenth of a point is neutral. */
export function changeTone(change: number): StatusTone {
  if (change >= VISIBLE_CHANGE) {
    return "success";
  }
  return change <= -VISIBLE_CHANGE ? "danger" : "neutral";
}

/**
 * Whether anything moved: a new failure, a fix, a scenario's score (the API
 * lists only half a point or more) or a criterion's average (the API lists
 * all five; a move under a tenth of a point does not count).
 */
export function hasComparisonChanges(comparison: AutotestRunComparison): boolean {
  return (
    comparison.new_failures.length > 0 ||
    comparison.fixed.length > 0 ||
    comparison.score_changes.length > 0 ||
    comparison.criterion_changes.some((change) => Math.abs(change.change) >= VISIBLE_CHANGE)
  );
}

/** Score drops first (the API sends them worst first), then the rises. */
export function scoreDrops(comparison: AutotestRunComparison): AutotestScoreChange[] {
  return comparison.score_changes.filter((change) => change.change < 0);
}

export function scoreRises(comparison: AutotestRunComparison): AutotestScoreChange[] {
  return comparison.score_changes.filter((change) => change.change > 0);
}
