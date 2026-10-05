import { describe, expect, it } from "vitest";

import { barHeight, hasWeekComparison, judgedDays, weakCriteria } from "./quality";

describe("barHeight", () => {
  it("maps 1..5 onto the plot with a visible floor", () => {
    expect(barHeight(5)).toBe(100);
    expect(barHeight(3)).toBe(50);
    expect(barHeight(1)).toBe(6);
    expect(barHeight(1.1)).toBe(6);
  });

  it("draws nothing for a day without scores and clamps strays", () => {
    expect(barHeight(null)).toBeNull();
    expect(barHeight(undefined)).toBeNull();
    expect(barHeight(7)).toBe(100);
  });
});

describe("weakCriteria", () => {
  it("lists the criteria under the pass mark, lowest first", () => {
    const sample = {
      scores: [
        { criterion: "facts_and_prices", score: 3 },
        { criterion: "booking_data", score: 5 },
        { criterion: "handoff", score: 2 },
        { criterion: "language", score: 4 },
      ],
    } as const;
    expect(weakCriteria({ scores: [...sample.scores] })).toEqual(["handoff", "facts_and_prices"]);
  });
});

describe("week comparison and judged days", () => {
  it("needs both weeks to compare", () => {
    expect(hasWeekComparison({ last_week_average: 4.2, previous_week_average: 4.6 })).toBe(true);
    expect(hasWeekComparison({ last_week_average: 4.2, previous_week_average: null })).toBe(false);
    expect(hasWeekComparison({})).toBe(false);
  });

  it("keeps the judged days, newest first", () => {
    const days = [
      { day_start: 1, sample_count: 2, average_score: 4.5 },
      { day_start: 2, sample_count: 0, average_score: null },
      { day_start: 3, sample_count: 1, average_score: 3.8 },
    ];
    expect(judgedDays(days).map((day) => day.day_start)).toEqual([3, 1]);
  });
});
