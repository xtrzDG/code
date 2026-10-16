import { describe, expect, it } from "vitest";

import { ROI_DEFAULTS, clampInput, computeRoi, roundNicely, startingCheck } from "./roi";

describe("value calculator", () => {
  it("counts only the after-hours share of missed requests that books", () => {
    const result = computeRoi({ ...ROI_DEFAULTS, averageCheck: 40 }, 99);

    expect(result.answeredRequests).toBe(48);
    expect(result.bookings).toBeCloseTo(14.4);
    expect(result.monthlyValue).toBeCloseTo(576);
    expect(result.multiple).toBeCloseTo(5.818, 2);
    expect(result.breakEvenBookings).toBe(3);
  });

  it("has no multiple without value or price and no break-even without a check", () => {
    expect(computeRoi({ ...ROI_DEFAULTS, averageCheck: 0 }, 99)).toMatchObject({
      monthlyValue: 0,
      multiple: null,
      breakEvenBookings: null,
    });
    expect(computeRoi({ ...ROI_DEFAULTS, averageCheck: 40 }, 0)).toMatchObject({ multiple: null, breakEvenBookings: null });
  });

  it("keeps typed numbers inside their ranges", () => {
    expect(clampInput("afterHoursPercent", 140)).toBe(100);
    expect(clampInput("conversionPercent", -5)).toBe(0);
    expect(clampInput("missedPerMonth", Number.NaN)).toBe(0);
    expect(computeRoi({ missedPerMonth: 10, afterHoursPercent: 250, conversionPercent: 50, averageCheck: 10 }, 10).bookings).toBe(5);
  });

  it("starts from the niche's typical check at the plans' price level", () => {
    expect(startingCheck(40, 99, 99)).toBe(40);
    expect(startingCheck(40, 99, 293)).toBe(120);
    expect(startingCheck(40, 0, 293)).toBe(40);
    expect(startingCheck(null, 99, 99)).toBeNull();
    expect(startingCheck(0, 99, 99)).toBeNull();
  });

  it("rounds starting values to two significant digits", () => {
    expect(roundNicely(0.4)).toBe(1);
    expect(roundNicely(7.4)).toBe(7);
    expect(roundNicely(37.2)).toBe(37);
    expect(roundNicely(142)).toBe(140);
    expect(roundNicely(1234)).toBe(1200);
  });
});
