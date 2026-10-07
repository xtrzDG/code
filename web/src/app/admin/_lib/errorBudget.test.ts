import { describe, expect, it } from "vitest";

import {
  budgetLeftShare,
  budgetTone,
  burnMultiple,
  burnTone,
  hasMeasurements,
  isLatencyOverTarget,
  orderedObjectives,
  overallTone,
  type ErrorBudget,
  type ObjectiveBudget,
} from "./errorBudget";

function objective(series: ObjectiveBudget["series"], permille: number, burn = 0): ObjectiveBudget {
  return {
    series,
    objective: series === "inbound_answered" ? 0.995 : 0.999,
    events: 1000,
    good_events: 999,
    budget_left_permille: permille,
    burn_rate_last_hour_percent: burn,
  };
}

function view(objectives: ObjectiveBudget[], p95: number | null = 4000): ErrorBudget {
  return {
    objectives,
    latency: { target_ms: 15_000, last_hour_p95_ms: p95, hours_over_target: 2, measured_hours: 600 },
    measured_since: 1_790_000_000_000_000,
    measured_until: 1_792_000_000_000_000,
  };
}

describe("error budget", () => {
  it("reads the budget left as a share the meter can show", () => {
    expect(budgetLeftShare(1000)).toBe(1);
    expect(budgetLeftShare(250)).toBe(0.25);
    expect(budgetLeftShare(-400)).toBe(0);
  });

  it("follows the budget policy: calm, under half, spent", () => {
    expect(budgetTone(800)).toBe("success");
    expect(budgetTone(499)).toBe("warning");
    expect(budgetTone(0)).toBe("danger");
    expect(budgetTone(-10)).toBe("danger");
  });

  it("shows the burn rate as a multiple and flags it from the slow alert's pace", () => {
    expect(burnMultiple(1440)).toBe(14.4);
    expect(burnTone(80)).toBe("neutral");
    expect(burnTone(250)).toBe("warning");
    expect(burnTone(601)).toBe("danger");
  });

  it("orders the objectives and takes the worst for the card", () => {
    const budget = view([objective("api_availability", 300), objective("inbound_answered", 900)]);

    expect(orderedObjectives(budget).map((item) => item.series)).toEqual(["inbound_answered", "api_availability"]);
    expect(overallTone(budget)).toBe("warning");
    expect(overallTone(view([objective("inbound_answered", -5), objective("api_availability", 900)]))).toBe("danger");
    expect(overallTone(view([objective("inbound_answered", 990)]))).toBe("success");
  });

  it("knows a platform without hourly rows and a slow last hour", () => {
    expect(hasMeasurements(view([]))).toBe(true);
    expect(hasMeasurements({ ...view([]), measured_since: null, measured_until: null })).toBe(false);
    expect(isLatencyOverTarget(view([], 16_000))).toBe(true);
    expect(isLatencyOverTarget(view([], 15_000))).toBe(false);
    expect(isLatencyOverTarget(view([], null))).toBe(false);
  });
});
