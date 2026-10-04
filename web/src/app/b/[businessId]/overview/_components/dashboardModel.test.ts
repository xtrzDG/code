import { describe, expect, it } from "vitest";

import {
  canTakeStep,
  isDashboardPeriod,
  isLaunched,
  nearestDayIndex,
  needsStatusCard,
  nextStep,
  periodRange,
  toBars,
  trendAxis,
  trendPath,
  usageLevel,
} from "./dashboardModel";

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
    expect(nextStep({ status: "onboarding", service_mode: "full" }).page).toBe("assistant/profile");
    expect(nextStep({ status: "testing", service_mode: "full" }).page).toBe("assistant");
    expect(nextStep({ status: "live", service_mode: "full" }).page).toBe("assistant/channels");
    expect(nextStep({ status: "paused", service_mode: "full" }).page).toBe("settings");
  });

  it("sends an unpaid live business to billing", () => {
    const step = nextStep({ status: "live", service_mode: "leads_only" });
    expect(step.page).toBe("settings/billing");
    expect(step.tone).toBe("danger");
  });
});

describe("the status card", () => {
  it("gives way to the setup guide for owners of a business being set up or live", () => {
    expect(needsStatusCard({ status: "onboarding", service_mode: "full" }, true)).toBe(false);
    expect(needsStatusCard({ status: "testing", service_mode: "full" }, true)).toBe(false);
    expect(needsStatusCard({ status: "live", service_mode: "full" }, true)).toBe(false);
  });

  it("stays for owners when the plan is unpaid or the assistant is paused", () => {
    expect(needsStatusCard({ status: "live", service_mode: "leads_only" }, true)).toBe(true);
    expect(needsStatusCard({ status: "paused", service_mode: "full" }, true)).toBe(true);
    expect(needsStatusCard({ status: "onboarding", service_mode: "leads_only" }, true)).toBe(false);
  });

  it("always shows staff the status", () => {
    expect(needsStatusCard({ status: "live", service_mode: "full" }, false)).toBe(true);
  });
});

describe("who can take the next step", () => {
  it("keeps billing and settings for owners", () => {
    expect(canTakeStep({ page: "settings/billing" }, false)).toBe(false);
    expect(canTakeStep({ page: "settings" }, false)).toBe(false);
    expect(canTakeStep({ page: "assistant/channels" }, false)).toBe(false);
    expect(canTakeStep({ page: "settings/billing" }, true)).toBe(true);
    expect(canTakeStep({ page: "assistant" }, false)).toBe(true);
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

describe("trend chart", () => {
  it("picks a clean axis of four steps for whole counts", () => {
    expect(trendAxis(0)).toEqual({ max: 4, ticks: [0, 1, 2, 3, 4] });
    expect(trendAxis(4)).toEqual({ max: 4, ticks: [0, 1, 2, 3, 4] });
    expect(trendAxis(5)).toEqual({ max: 8, ticks: [0, 2, 4, 6, 8] });
    expect(trendAxis(30).max).toBe(40);
    expect(trendAxis(300)).toEqual({ max: 400, ticks: [0, 100, 200, 300, 400] });
    expect(trendAxis(1234).max).toBe(2000);
  });

  it("draws a path across the plot with zero at the bottom", () => {
    expect(trendPath([0, 2, 4], 4, 100, 50)).toBe("M0 50 L50 25 L100 0");
    expect(trendPath([], 4, 100, 50)).toBe("");
  });

  it("snaps the pointer to the nearest day", () => {
    expect(nearestDayIndex(0, 30)).toBe(0);
    expect(nearestDayIndex(0.5, 3)).toBe(1);
    expect(nearestDayIndex(0.74, 3)).toBe(1);
    expect(nearestDayIndex(1.2, 3)).toBe(2);
    expect(nearestDayIndex(0.5, 1)).toBe(0);
  });
});

describe("launch", () => {
  it("counts a live or paused business as launched, not one still in setup", () => {
    expect(isLaunched("live")).toBe(true);
    expect(isLaunched("paused")).toBe(true);
    expect(isLaunched("onboarding")).toBe(false);
    expect(isLaunched("testing")).toBe(false);
  });
});
