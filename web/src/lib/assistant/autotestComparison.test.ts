import { describe, expect, it } from "vitest";

import {
  changeTone,
  formatScoreChange,
  hasComparisonChanges,
  scoreDrops,
  scoreRises,
  type AutotestRunComparison,
} from "./autotestComparison";

function comparison(overrides: Partial<AutotestRunComparison> = {}): AutotestRunComparison {
  return {
    baseline_run_id: "autotest_run_1",
    baseline_version_id: "assistant_version_1",
    baseline_version_number: 3,
    baseline_average_score: 4.5,
    average_score_change: -0.3,
    shared_scenario_count: 12,
    new_failures: [],
    fixed: [],
    score_changes: [],
    criterion_changes: [],
    ...overrides,
  };
}

const drop = { scenario_key: "booking__en", kind: "booking", language: "en", average_score: 3.4, baseline_average_score: 4.6, change: -1.2 } as const;
const rise = { scenario_key: "price_question__en__1", kind: "price_question", language: "en", average_score: 4.8, baseline_average_score: 4.0, change: 0.8 } as const;

describe("formatScoreChange", () => {
  it("always signs a change that shows", () => {
    expect(formatScoreChange(0.6, "en")).toBe("+0.6");
    expect(formatScoreChange(-0.84, "en")).toBe("−0.8");
    expect(formatScoreChange(0.02, "en")).toBe("0.0");
  });

  it("uses the reader's decimal separator", () => {
    expect(formatScoreChange(-1.25, "ru")).toMatch(/^−1,[23]$/);
  });
});

describe("changeTone", () => {
  it("marks rises good, drops bad and tiny moves neutral", () => {
    expect(changeTone(0.5)).toBe("success");
    expect(changeTone(-0.5)).toBe("danger");
    expect(changeTone(0.01)).toBe("neutral");
  });
});

describe("comparison lists", () => {
  it("sees no change in an identical run", () => {
    expect(hasComparisonChanges(comparison())).toBe(false);
  });

  it("splits score changes into drops and rises", () => {
    const changed = comparison({ score_changes: [drop, rise] });
    expect(hasComparisonChanges(changed)).toBe(true);
    expect(scoreDrops(changed)).toEqual([drop]);
    expect(scoreRises(changed)).toEqual([rise]);
  });

  it("counts a new failure or a fix as a change", () => {
    const failure = { scenario_key: "tool_abuse__en", kind: "tool_abuse", language: "en", outcome: "failed", baseline_outcome: "passed" } as const;
    expect(hasComparisonChanges(comparison({ new_failures: [failure] }))).toBe(true);
    expect(hasComparisonChanges(comparison({ fixed: [{ ...failure, outcome: "passed", baseline_outcome: "failed" }] }))).toBe(true);
  });
});
