/**
 * Pure helpers of a client's production quality on the admin client page
 * (GET /v1/admin/clients/{business_id}/quality): the nightly judge's
 * scores of real conversations, 1 to 5.
 */

import type { Schema } from "@/api/types";
import { PASSING_SCORE } from "@/lib/assistant/autotests";

export type ClientQuality = Schema<"ClientQualityView">;
export type QualityDay = Schema<"QualityDayView">;
export type QualitySample = Schema<"QualitySampleView">;
export type JudgeCriterion = Schema<"JudgeCriterion">;

const LOWEST_SCORE = 1;
const HIGHEST_SCORE = 5;
/** A judged day never draws a bar lower than this (percent), so it shows. */
const MIN_BAR_PERCENT = 6;

/** A day's bar height in percent of the plot: 1 → the floor, 5 → full; null without scores. */
export function barHeight(average: number | null | undefined): number | null {
  if (average === null || average === undefined) {
    return null;
  }
  const share = (Math.min(HIGHEST_SCORE, Math.max(LOWEST_SCORE, average)) - LOWEST_SCORE) / (HIGHEST_SCORE - LOWEST_SCORE);
  return Math.max(MIN_BAR_PERCENT, Math.round(share * 100));
}

/** The criteria the judge scored below the pass mark, lowest first. */
export function weakCriteria(sample: Pick<QualitySample, "scores">): JudgeCriterion[] {
  return [...sample.scores]
    .filter((score) => score.score < PASSING_SCORE)
    .sort((first, second) => first.score - second.score)
    .map((score) => score.criterion);
}

/** Whether the last week can be compared with the week before. */
export function hasWeekComparison(quality: Pick<ClientQuality, "last_week_average" | "previous_week_average">): boolean {
  return (
    quality.last_week_average !== null &&
    quality.last_week_average !== undefined &&
    quality.previous_week_average !== null &&
    quality.previous_week_average !== undefined
  );
}

/** Days with scores, newest first, for the table view of the trend. */
export function judgedDays(days: readonly QualityDay[]): QualityDay[] {
  return days.filter((day) => day.sample_count > 0).reverse();
}
