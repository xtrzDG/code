/**
 * How full a package is (voice minutes, dialogues), the one rule every
 * screen shows: the owner is warned from 80 % of a package (concept,
 * section 9: "на 80 % пакета"), and 100 % or more is overage.
 */

export const USAGE_WARNING_PERCENT = 80;

const FULL_PERCENT = 100;

/** "none": the package has none of this unit (no percent). */
export type UsageLevel = "none" | "ok" | "warning" | "exceeded";

export function usageLevel(percent: number | null | undefined): UsageLevel {
  if (percent === null || percent === undefined || !Number.isFinite(percent)) {
    return "none";
  }
  if (percent >= FULL_PERCENT) {
    return "exceeded";
  }
  return percent >= USAGE_WARNING_PERCENT ? "warning" : "ok";
}

/** A level the owner should act on: the price of more, or the overage. */
export function isUsageWarned(level: UsageLevel): boolean {
  return level === "warning" || level === "exceeded";
}
