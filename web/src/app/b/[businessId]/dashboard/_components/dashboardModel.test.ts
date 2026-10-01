import { describe, expect, it } from "vitest";

import { isDashboardPeriod, nextStep, periodRange, toBars, usageLevel } from "./dashboardModel";

describe("dashboard periods", () => {
  it("end today and include it", () => {
    expect(periodRange("today", "2026-10-01")).toEqual({ from: "2026-10-01", to: "2026-10-01" });
    expect(periodRange("7d", "2026-10-01")).toEqual({ from: "2026-09-25", to: "2026-10-01" });
    expect(periodRange("30d", "2026-10-01")).toEqual({ from: "2026-09-02", to: "2026-10-01" });
    expect(periodRange("90d", "2026-03-01")).toEqual({ from: "2025-12-02", to: "2026-03-01" });
  });

  it("accept only known values from the URL", () => {
    expect(isDashboardPeriod("7d")).toBe(true);
    expect(isDashboardPeriod("365d")).toBe(false);
    expect(isDashboardPeriod(undefined)).toBe(false);
  });
});

describe("next step", () => {
  it("follows the business status", () => {
    expect(nextStep({ status: "onboarding", service_mode: "full" }).section).toBe("onboarding");
    expect(nextStep({ status: "testing", service_mode: "full" }).section).toBe("assistant");
    expect(nextStep({ status: "live", service_mode: "full" }).section).toBe("channels");
    expect(nextStep({ status: "paused", service_mode: "full" }).section).toBe("settings");
  });

  it("sends an unpaid live business to billing", () => {
    const step = nextStep({ status: "live", service_mode: "leads_only" });
    expect(step.section).toBe("billing");
    expect(step.tone).toBe("danger");
  });
});

describe("package usage", () => {
  it("warns at 80% and flags overage at 100%", () => {
    expect(usageLevel(null)).toBe("ok");
    expect(usageLevel(79)).toBe("ok");
    expect(usageLevel(80)).toBe("warning");
    expect(usageLevel(100)).toBe("over");
    expect(usageLevel(140)).toBe("over");
  });
});

describe("bars", () => {
  it("sorts by count and sizes by share", () => {
    expect(
      toBars([
        { key: "en", count: 1 },
        { key: "ka", count: 3 },
      ]),
    ).toEqual([
      { key: "ka", count: 3, percent: 75 },
      { key: "en", count: 1, percent: 25 },
    ]);
    expect(toBars([])).toEqual([]);
  });
});
