import { describe, expect, it } from "vitest";

import {
  EMPTY_METRICS_FILTERS,
  barPercent,
  cohortColumns,
  cohortShade,
  durationParts,
  hasMetricsFilters,
  metricsSearch,
  movementSign,
  parseMetricsFilters,
  payingShare,
  presetOf,
  presetRange,
  shiftDay,
} from "./metrics";

const TODAY = "2026-10-15";

describe("metrics filters", () => {
  it("are read from the address, dropping what the API would refuse", () => {
    const filters = parseMetricsFilters(
      new URLSearchParams("from=2026-09-01&to=2026-13-01&country=GE&niche=beauty_salon&source=Instagram&x=1"),
    );

    expect(filters).toEqual({ from: "2026-09-01", to: "", country: "GE", niche: "beauty_salon", source: "" });
    expect(hasMetricsFilters(filters)).toBe(true);
    expect(hasMetricsFilters(EMPTY_METRICS_FILTERS)).toBe(false);
  });

  it("go back into the address in a fixed order, the empty ones left out", () => {
    expect(metricsSearch({ ...EMPTY_METRICS_FILTERS, source: "google", from: "2026-09-01" })).toBe("from=2026-09-01&source=google");
    expect(metricsSearch(EMPTY_METRICS_FILTERS)).toBe("");
  });

  it("name presets by days ending today; the last 90 days are the API's default", () => {
    expect(shiftDay("2026-03-01", -1)).toBe("2026-02-28");
    expect(presetRange("last30", TODAY)).toEqual({ from: "2026-09-16", to: TODAY });
    expect(presetRange("last90", TODAY)).toEqual({ from: "", to: "" });
    expect(presetOf({ from: "", to: "" }, TODAY)).toBe("last90");
    expect(presetOf(presetRange("last365", TODAY), TODAY)).toBe("last365");
    expect(presetOf({ from: "2026-09-01", to: "2026-09-30" }, TODAY)).toBe("custom");
  });
});

describe("metrics arithmetic", () => {
  it("draws bars on a shared scale, keeping small values visible", () => {
    expect(barPercent(50, 200)).toBe(25);
    expect(barPercent(1, 1000)).toBe(1);
    expect(barPercent(0, 10)).toBe(0);
    expect(barPercent(3, 0)).toBe(0);
  });

  it("shades cohort cells in five steps and counts the widest row", () => {
    expect([0, 5, 12, 30, 80].map(cohortShade)).toEqual([
      "bg-surface-muted",
      "bg-accent-solid/10",
      "bg-accent-solid/20",
      "bg-accent-solid/30",
      "bg-accent-solid/40",
    ]);
    expect(cohortColumns([{ month: "2026-09", sign_ups: 3, went_live: 2, paying: [10, 20] }, { month: "2026-10", sign_ups: 1, went_live: 1 }])).toBe(2);
  });

  it("reads durations in their most natural unit", () => {
    expect(durationParts(600)).toEqual({ unit: "minutes", count: 10 });
    expect(durationParts(5 * 3600)).toEqual({ unit: "hours", count: 5 });
    expect(durationParts(10 * 86400)).toEqual({ unit: "days", count: 10 });
  });

  it("signs MRR movements and the paying share of a source", () => {
    expect(movementSign("expansion")).toBe(1);
    expect(movementSign("churn")).toBe(-1);
    expect(payingShare({ source: "google", sign_ups: 3, went_live: 2, paying: 1 })).toBe(33.3);
    expect(payingShare({ source: "x", sign_ups: 0, went_live: 0, paying: 0 })).toBeNull();
  });
});
