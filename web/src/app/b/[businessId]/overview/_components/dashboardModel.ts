/** Pure rules of the dashboard: periods, the next step for the owner, package levels, bars. */

import type { BusinessStatus, BusinessView } from "@/api/types";
import { addDays, type LocalDateText } from "@/components/insights/dates";
import { sharePercent } from "@/components/insights/numbers";
import type { MessageKey } from "@/i18n/translate";
import type { BusinessSection } from "@/lib/navigation";

export const DASHBOARD_PERIODS = ["today", "7d", "30d", "90d"] as const;
export type DashboardPeriod = (typeof DASHBOARD_PERIODS)[number];
export const DEFAULT_DASHBOARD_PERIOD: DashboardPeriod = "30d";

const PERIOD_DAYS: Record<DashboardPeriod, number> = { today: 1, "7d": 7, "30d": 30, "90d": 90 };

export function isDashboardPeriod(value: unknown): value is DashboardPeriod {
  return typeof value === "string" && (DASHBOARD_PERIODS as readonly string[]).includes(value);
}

/** Inclusive local dates of a period ending today (the API's `from` and `to`). */
export function periodRange(period: DashboardPeriod, today: LocalDateText): { from: LocalDateText; to: LocalDateText } {
  return { from: addDays(today, 1 - PERIOD_DAYS[period]), to: today };
}

export interface NextStep {
  tone: "info" | "success" | "warning" | "danger";
  title: MessageKey;
  description: MessageKey;
  action: MessageKey;
  section: BusinessSection;
}

const NEXT_STEPS: Record<BusinessStatus, NextStep> = {
  onboarding: {
    tone: "warning",
    title: "dashboard.status.onboarding.title",
    description: "dashboard.status.onboarding.description",
    action: "dashboard.status.onboarding.action",
    section: "onboarding",
  },
  testing: {
    tone: "info",
    title: "dashboard.status.testing.title",
    description: "dashboard.status.testing.description",
    action: "dashboard.status.testing.action",
    section: "assistant",
  },
  live: {
    tone: "success",
    title: "dashboard.status.live.title",
    description: "dashboard.status.live.description",
    action: "dashboard.status.live.action",
    section: "channels",
  },
  paused: {
    tone: "warning",
    title: "dashboard.status.paused.title",
    description: "dashboard.status.paused.description",
    action: "dashboard.status.paused.action",
    section: "settings",
  },
};

const LEADS_ONLY_STEP: NextStep = {
  tone: "danger",
  title: "dashboard.status.leadsOnly.title",
  description: "dashboard.status.leadsOnly.description",
  action: "dashboard.status.leadsOnly.action",
  section: "billing",
};

/** What the owner should do next, from the business status (an unpaid plan wins). */
export function nextStep(business: Pick<BusinessView, "status" | "service_mode">): NextStep {
  if (business.service_mode === "leads_only" && business.status !== "onboarding") {
    return LEADS_ONLY_STEP;
  }
  return NEXT_STEPS[business.status];
}

/** Sections whose API answers owners only (billing overview, settings changes). */
const OWNER_ONLY_SECTIONS: ReadonlySet<BusinessSection> = new Set(["billing", "settings"]);

/** Whether the next step's button makes sense for the viewer (staff cannot act on billing or settings). */
export function canTakeStep(step: Pick<NextStep, "section">, isOwner: boolean): boolean {
  return isOwner || !OWNER_ONLY_SECTIONS.has(step.section);
}

export type UsageLevel = "ok" | "warning" | "over";

/** 80% of a package triggers the warning (concept: "на 80 % пакета"); 100% is overage. */
export const USAGE_WARNING_PERCENT = 80;

export function usageLevel(percent: number | null | undefined): UsageLevel {
  if (percent === null || percent === undefined) {
    return "ok";
  }
  if (percent >= 100) {
    return "over";
  }
  return percent >= USAGE_WARNING_PERCENT ? "warning" : "ok";
}

export interface Bar<Key> {
  key: Key;
  count: number;
  percent: number;
}

/** Counts as bars sized by their share of the total, largest first. */
export function toBars<Key>(items: readonly { key: Key; count: number }[]): Bar<Key>[] {
  const total = items.reduce((sum, item) => sum + item.count, 0);
  return [...items]
    .sort((left, right) => right.count - left.count)
    .map((item) => ({ key: item.key, count: item.count, percent: sharePercent(item.count, total) }));
}

/** The daily series of the trend chart, in the fixed color order. */
export const TREND_SERIES = ["conversation_count", "booking_count", "handoff_count"] as const;
export type TrendSeries = (typeof TREND_SERIES)[number];

const TICK_COUNT = 4;

/**
 * A clean y-axis for whole counts: four equal steps of 1, 2 or 5 × 10ⁿ
 * reaching at least the largest value (0 to 4 for an empty period).
 */
export function trendAxis(maxValue: number): { max: number; ticks: number[] } {
  let step = 1;
  for (let magnitude = 1; step * TICK_COUNT < maxValue; magnitude *= 10) {
    step = [1, 2, 5, 10].map((factor) => factor * magnitude).find((candidate) => candidate * TICK_COUNT >= maxValue) ?? 10 * magnitude;
  }
  return { max: step * TICK_COUNT, ticks: Array.from({ length: TICK_COUNT + 1 }, (_, index) => index * step) };
}

/** An SVG path through the values, spread over the width, 0 at the bottom. */
export function trendPath(values: readonly number[], max: number, width: number, height: number): string {
  if (values.length === 0 || max <= 0) {
    return "";
  }
  const stepX = values.length > 1 ? width / (values.length - 1) : 0;
  return values
    .map((value, index) => {
      const x = Math.round(index * stepX * 100) / 100;
      const y = Math.round((height - (value / max) * height) * 100) / 100;
      return `${index === 0 ? "M" : "L"}${x} ${y}`;
    })
    .join(" ");
}

/** The day nearest to a pointer at `fraction` (0–1) of the plot width. */
export function nearestDayIndex(fraction: number, count: number): number {
  if (count <= 1) {
    return 0;
  }
  return Math.min(count - 1, Math.max(0, Math.round(fraction * (count - 1))));
}
