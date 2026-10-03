/**
 * Pure helpers of the Assistant section's autotests: run progress, results,
 * scores and the scenarios a run may cover.
 */

import type { Schema } from "@/api/types";
import { numberFormat } from "@/lib/intl/formatters";

import type { AssistantToolName, AssistantVersionStatus, StatusTone } from "./versions";

export type AutotestRunView = Schema<"AutotestRunView">;
export type AutotestScenarioResult = Schema<"AutotestScenarioResultView">;
export type AutotestScenarioKind = Schema<"AutotestScenarioKind">;
export type AutotestOutcome = Schema<"AutotestOutcome">;
export type JudgeCriterion = Schema<"JudgeCriterion">;

export const JUDGE_CRITERIA: readonly JudgeCriterion[] = [
  "facts_and_prices",
  "booking_data",
  "ai_disclosure",
  "handoff",
  "language",
];

export const AUTOTEST_KINDS: readonly AutotestScenarioKind[] = [
  "booking",
  "booking_out_of_hours",
  "cancellation",
  "price_question",
  "unknown_question",
  "discount_request",
  "rude_customer",
  "human_request",
  "prompt_injection",
  "emergency",
];

/** The judge's pass mark: a run passes with an average of at least 4 of 5. */
export const PASSING_SCORE = 4;

/** "4.25" -> "4.3" in the UI language (scores are 1..5). */
export function formatScore(score: number, locale: string): string {
  return numberFormat(locale, { minimumFractionDigits: 1, maximumFractionDigits: 1 }).format(score);
}

/**
 * Keep polling while the version is under test (the worker plays the run in
 * the background) or the run says it is still running.
 */
export function isRunInProgress(
  versionStatus: AssistantVersionStatus | undefined,
  run: Pick<AutotestRunView, "status"> | null | undefined,
): boolean {
  return versionStatus === "testing" || run?.status === "running";
}

export interface RunSummary {
  total: number;
  done: number;
  passed: number;
  failed: number;
  errored: number;
  /** 0..1 share of finished scenarios; 1 when nothing is planned. */
  progress: number;
}

export function summarizeRun(run: Pick<AutotestRunView, "scenario_count" | "results">): RunSummary {
  const results = run.results ?? [];
  const count = (outcome: AutotestOutcome) => results.filter((result) => result.outcome === outcome).length;
  const total = Math.max(run.scenario_count, results.length);
  return {
    total,
    done: results.length,
    passed: count("passed"),
    failed: count("failed"),
    errored: count("errored"),
    progress: total === 0 ? 1 : results.length / total,
  };
}

export type ResultFilter = "all" | "problems";

export function filterResults(
  results: readonly AutotestScenarioResult[],
  filter: { outcome: ResultFilter; language: string | "all" },
): AutotestScenarioResult[] {
  return results.filter(
    (result) =>
      (filter.outcome === "all" || result.outcome !== "passed") &&
      (filter.language === "all" || result.language === filter.language),
  );
}

/** Problems first (errored, failed), then passed; stable inside each outcome. */
export function sortResults(results: readonly AutotestScenarioResult[]): AutotestScenarioResult[] {
  const rank: Record<AutotestOutcome, number> = { errored: 0, failed: 1, passed: 2 };
  return results
    .map((result, index) => ({ result, index }))
    .sort((left, right) => rank[left.result.outcome] - rank[right.result.outcome] || left.index - right.index)
    .map((entry) => entry.result);
}

/** "price_question__en__2" -> 2: scenarios repeated for several items are numbered. */
export function scenarioNumber(scenarioKey: string): number | null {
  const match = /__(\d+)$/.exec(scenarioKey);
  return match ? Number(match[1]) : null;
}

export function resultLanguages(results: readonly Pick<AutotestScenarioResult, "language">[]): string[] {
  return [...new Set(results.map((result) => result.language))];
}

export function criterionScore(result: Pick<AutotestScenarioResult, "scores">, criterion: JudgeCriterion): number | null {
  return result.scores.find((score) => score.criterion === criterion)?.score ?? null;
}

/** Average judge score of one scenario, or null when it was not judged. */
export function scenarioAverage(result: Pick<AutotestScenarioResult, "scores">): number | null {
  if (result.scores.length === 0) {
    return null;
  }
  return result.scores.reduce((sum, score) => sum + score.score, 0) / result.scores.length;
}

export function scoreTone(score: number): StatusTone {
  if (score >= PASSING_SCORE) {
    return "success";
  }
  return score >= 3 ? "warning" : "danger";
}

const BOOKING_SCENARIO_KINDS: ReadonlySet<AutotestScenarioKind> = new Set(["booking", "booking_out_of_hours", "cancellation"]);

/**
 * Scenario kinds that apply to a version, as the API plans them: the
 * niche's kinds without repeats, booking ones only when the version books.
 */
export function applicableAutotestKinds(
  nicheKinds: readonly AutotestScenarioKind[],
  tools: readonly AssistantToolName[],
): AutotestScenarioKind[] {
  const canBook = tools.includes("create_booking");
  return nicheKinds.filter(
    (kind, index) => nicheKinds.indexOf(kind) === index && (canBook || !BOOKING_SCENARIO_KINDS.has(kind)),
  );
}

/**
 * The scenarios to send when the owner narrows a run: null means "all"
 * (only a run over every language and kind can make a version ready).
 */
export function narrowedSelection<T extends string>(chosen: readonly T[], available: readonly T[]): T[] | null {
  const unique = available.filter((value) => chosen.includes(value));
  return unique.length === available.length ? null : unique;
}
