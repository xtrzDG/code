/**
 * The founder's Metrics page (GET /v1/admin/metrics) as data: its filters
 * in the address (`?from=&to=&country=&niche=&source=&include_admins=`, so
 * a view can be shared and survives a reload), the period presets, and the small pieces
 * of arithmetic the charts need. Pure functions; the screen lives in
 * _components/metrics/.
 */

import type { Schema } from "@/api/types";

export type AdminMetricsView = Schema<"AdminMetricsView">;
export type FunnelStepView = Schema<"FunnelStepView">;
export type TunnelStepView = Schema<"TunnelStepView">;
export type MrrView = Schema<"MrrView">;
type MrrMovementView = Schema<"MrrMovementView">;
export type MarginView = Schema<"MarginView">;
export type CohortRowView = Schema<"CohortRowView">;
export type SourceRowView = Schema<"SourceRowView">;
export type WebVitalView = Schema<"WebVitalView">;
export type BusinessGrowthView = Schema<"BusinessGrowthView">;
export type MrrMovementKind = MrrMovementView["kind"];

/**
 * Unset filters are empty strings; the API's default period is the last 90
 * days. `include_admins` is "true" when platform admins' own sign-ups and
 * businesses are counted (left out by default).
 */
export interface MetricsFilters {
  from: string;
  to: string;
  country: string;
  niche: string;
  source: string;
  include_admins: string;
}

export const EMPTY_METRICS_FILTERS: MetricsFilters = { from: "", to: "", country: "", niche: "", source: "", include_admins: "" };

export const PERIOD_PRESETS = ["last30", "last90", "last180", "last365"] as const;
export type PeriodPreset = (typeof PERIOD_PRESETS)[number] | "custom";

const PRESET_DAYS: Record<(typeof PERIOD_PRESETS)[number], number> = { last30: 30, last90: 90, last180: 180, last365: 365 };
const DEFAULT_PRESET = "last90";
const DAY_MS = 24 * 60 * 60 * 1000;

const RULES: Record<keyof MetricsFilters, RegExp> = {
  from: /^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$/,
  to: /^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$/,
  country: /^[A-Z]{2}$/,
  niche: /^[a-z][a-z_]*$/,
  source: /^[a-z0-9][a-z0-9._:-]{0,119}$/,
  include_admins: /^true$/,
};
const FILTER_KEYS = Object.keys(RULES) as (keyof MetricsFilters)[];

/** The filters of an address; a value the API would refuse is dropped. */
export function parseMetricsFilters(params: URLSearchParams): MetricsFilters {
  const filters = { ...EMPTY_METRICS_FILTERS };
  for (const key of FILTER_KEYS) {
    const value = params.get(key)?.trim() ?? "";
    filters[key] = RULES[key].test(value) ? value : "";
  }
  return filters;
}

/** The set filters as an address query (and as the API's query parameters). */
export function metricsQuery(filters: MetricsFilters): Record<string, string> {
  return Object.fromEntries(FILTER_KEYS.filter((key) => filters[key] !== "").map((key) => [key, filters[key]]));
}

export function metricsSearch(filters: MetricsFilters): string {
  return new URLSearchParams(metricsQuery(filters)).toString();
}

/** Whether the filters narrow the numbers (counting platform admins in is not a narrowing). */
export function hasMetricsFilters(filters: MetricsFilters): boolean {
  return FILTER_KEYS.some((key) => key !== "include_admins" && filters[key] !== "");
}

/** The same filters with platform admins counted in or left out. */
export function withPlatformAdmins(filters: MetricsFilters, isIncluded: boolean): MetricsFilters {
  return { ...filters, include_admins: isIncluded ? "true" : "" };
}

/** A UTC calendar day as YYYY-MM-DD. */
export function isoDay(moment: Date): string {
  return moment.toISOString().slice(0, 10);
}

export function shiftDay(day: string, days: number): string {
  return isoDay(new Date(Date.parse(`${day}T00:00:00Z`) + days * DAY_MS));
}

/** The days of a preset ending today (both included); the default is no filter at all. */
export function presetRange(preset: (typeof PERIOD_PRESETS)[number], today: string): Pick<MetricsFilters, "from" | "to"> {
  if (preset === DEFAULT_PRESET) {
    return { from: "", to: "" };
  }
  return { from: shiftDay(today, -(PRESET_DAYS[preset] - 1)), to: today };
}

/** Which preset the filters' days are, or "custom". */
export function presetOf(filters: Pick<MetricsFilters, "from" | "to">, today: string): PeriodPreset {
  if (filters.from === "" && filters.to === "") {
    return DEFAULT_PRESET;
  }
  for (const preset of PERIOD_PRESETS) {
    const range = presetRange(preset, today);
    if (range.from === filters.from && range.to === filters.to) {
      return preset;
    }
  }
  return "custom";
}

/** A bar's width in percent of the widest; a non-zero value stays visible. */
export function barPercent(value: number, max: number): number {
  if (max <= 0 || value <= 0) {
    return 0;
  }
  return Math.max(1, Math.round((value / max) * 1000) / 10);
}

/** Cohort cells: five steps of the accent behind the printed share. */
const COHORT_SHADES = ["bg-surface-muted", "bg-accent-solid/10", "bg-accent-solid/20", "bg-accent-solid/30", "bg-accent-solid/40"] as const;

export function cohortShade(percent: number): (typeof COHORT_SHADES)[number] {
  if (percent <= 0) {
    return COHORT_SHADES[0];
  }
  if (percent < 10) {
    return COHORT_SHADES[1];
  }
  if (percent < 25) {
    return COHORT_SHADES[2];
  }
  return percent < 50 ? COHORT_SHADES[3] : COHORT_SHADES[4];
}

/** The widest cohort row (months since sign-up) of the table. */
export function cohortColumns(rows: readonly CohortRowView[]): number {
  return rows.reduce((widest, row) => Math.max(widest, row.paying?.length ?? 0), 0);
}

export type DurationUnit = "minutes" | "hours" | "days";

/** A duration in its most readable whole unit: minutes, hours up to two days, then days. */
export function durationParts(seconds: number): { unit: DurationUnit; count: number } {
  if (seconds < 60 * 60) {
    return { unit: "minutes", count: Math.max(0, Math.round(seconds / 60)) };
  }
  if (seconds < 48 * 60 * 60) {
    return { unit: "hours", count: Math.round(seconds / (60 * 60)) };
  }
  return { unit: "days", count: Math.round(seconds / (24 * 60 * 60)) };
}

/** Movements that add to MRR are shown with +, the others with −. */
export function movementSign(kind: MrrMovementKind): 1 | -1 {
  return kind === "contraction" || kind === "churn" ? -1 : 1;
}

/** Owners of a source who pay, in percent of its sign-ups. */
export function payingShare(row: SourceRowView): number | null {
  return row.sign_ups > 0 ? Math.round((row.paying / row.sign_ups) * 1000) / 10 : null;
}
