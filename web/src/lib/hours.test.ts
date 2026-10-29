import { describe, expect, it } from "vitest";

import type { OpeningInterval } from "@/api/types";

import { intervalsToWeek, overlappingWeekdays, weekToIntervals, type DayHours } from "./hours";

function week(entries: Partial<Record<1 | 2 | 3 | 4 | 5 | 6 | 7, DayHours["intervals"]>>): DayHours[] {
  return ([1, 2, 3, 4, 5, 6, 7] as const).map((weekday) => ({ weekday, intervals: entries[weekday] ?? [] }));
}

describe("opening hours", () => {
  it("splits hours past midnight into two days for the API", () => {
    expect(weekToIntervals(week({ 5: [{ opens: 18 * 60, closes: 2 * 60 }] }))).toEqual([
      { weekday: 5, opens_at: 1080, closes_at: 1440 },
      { weekday: 6, opens_at: 0, closes_at: 120 },
    ]);
  });

  it("wraps Sunday night into Monday", () => {
    expect(weekToIntervals(week({ 7: [{ opens: 20 * 60, closes: 60 }] }))).toEqual([
      { weekday: 1, opens_at: 0, closes_at: 60 },
      { weekday: 7, opens_at: 1200, closes_at: 1440 },
    ]);
  });

  it("treats 00:00 as midnight and 00:00–00:00 as the whole day", () => {
    expect(weekToIntervals(week({ 1: [{ opens: 600, closes: 0 }], 2: [{ opens: 0, closes: 0 }] }))).toEqual([
      { weekday: 1, opens_at: 600, closes_at: 1440 },
      { weekday: 2, opens_at: 0, closes_at: 1440 },
    ]);
  });

  it("joins the API's overnight pieces back into one editor row", () => {
    const intervals: OpeningInterval[] = [
      { weekday: 5, opens_at: 1080, closes_at: 1440 },
      { weekday: 6, opens_at: 0, closes_at: 120 },
      { weekday: 6, opens_at: 1080, closes_at: 1440 },
      { weekday: 7, opens_at: 0, closes_at: 120 },
    ];
    const result = intervalsToWeek(intervals);
    expect(result.find((day) => day.weekday === 5)?.intervals).toEqual([{ opens: 1080, closes: 120 }]);
    expect(result.find((day) => day.weekday === 6)?.intervals).toEqual([{ opens: 1080, closes: 120 }]);
    expect(result.find((day) => day.weekday === 7)?.intervals).toEqual([]);
  });

  it("keeps whole days and early openings that do not continue a night", () => {
    const intervals: OpeningInterval[] = [
      { weekday: 1, opens_at: 0, closes_at: 1440 },
      { weekday: 2, opens_at: 0, closes_at: 300 },
      { weekday: 3, opens_at: 540, closes_at: 780 },
      { weekday: 3, opens_at: 840, closes_at: 1440 },
    ];
    const result = intervalsToWeek(intervals);
    expect(result[0]?.intervals).toEqual([{ opens: 0, closes: 0 }]);
    expect(result[1]?.intervals).toEqual([{ opens: 0, closes: 300 }]);
    expect(result[2]?.intervals).toEqual([
      { opens: 540, closes: 780 },
      { opens: 840, closes: 0 },
    ]);
  });

  it("round-trips through the editor", () => {
    const intervals: OpeningInterval[] = [
      { weekday: 1, opens_at: 540, closes_at: 1320 },
      { weekday: 4, opens_at: 1080, closes_at: 1440 },
      { weekday: 5, opens_at: 0, closes_at: 180 },
      { weekday: 5, opens_at: 1080, closes_at: 1440 },
      { weekday: 6, opens_at: 0, closes_at: 180 },
    ];
    expect(weekToIntervals(intervalsToWeek(intervals))).toEqual(intervals);
  });

  it("finds overlapping intervals the API would refuse", () => {
    expect(
      overlappingWeekdays([
        { weekday: 2, opens_at: 600, closes_at: 900 },
        { weekday: 2, opens_at: 840, closes_at: 1000 },
        { weekday: 3, opens_at: 600, closes_at: 900 },
      ]),
    ).toEqual([2]);
  });
});
