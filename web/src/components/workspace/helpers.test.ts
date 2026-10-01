import { describe, expect, it } from "vitest";

import {
  formatMicroUsd,
  isConfirmationTyped,
  isoDay,
  safeFileName,
  shortId,
  usageBarWidth,
  usageLevel,
  usagePercent,
  zonedDayStartUs,
} from "./helpers";

describe("isConfirmationTyped", () => {
  it("ignores case and surrounding spaces", () => {
    expect(isConfirmationTyped(" delete ", "DELETE")).toBe(true);
    expect(isConfirmationTyped("Нино", "нино")).toBe(true);
    expect(isConfirmationTyped("delet", "DELETE")).toBe(false);
  });

  it("never unlocks an empty expectation", () => {
    expect(isConfirmationTyped("", "  ")).toBe(false);
  });
});

describe("usage", () => {
  it("warns from 80 % and flags 100 %", () => {
    expect(usageLevel(null)).toBe("none");
    expect(usageLevel(undefined)).toBe("none");
    expect(usageLevel(0)).toBe("ok");
    expect(usageLevel(79)).toBe("ok");
    expect(usageLevel(80)).toBe("warning");
    expect(usageLevel(99)).toBe("warning");
    expect(usageLevel(100)).toBe("exceeded");
    expect(usageLevel(250)).toBe("exceeded");
  });

  it("computes whole percents and empty packages", () => {
    expect(usagePercent(320, 400)).toBe(80);
    expect(usagePercent(1, 3)).toBe(33);
    expect(usagePercent(5, 0)).toBeNull();
    expect(usagePercent(-1, 10)).toBe(0);
  });

  it("caps the bar width", () => {
    expect(usageBarWidth(140)).toBe(100);
    expect(usageBarWidth(null)).toBe(0);
    expect(usageBarWidth(42)).toBe(42);
  });
});

describe("formatMicroUsd", () => {
  it("shows small costs with four decimals", () => {
    expect(formatMicroUsd(1_234_567, "en")).toBe("$1.2346");
    expect(formatMicroUsd(0, "en")).toBe("$0.00");
    expect(formatMicroUsd(54_900_000, "en")).toBe("$54.90");
  });
});

describe("ids and files", () => {
  it("shortens prefixed ids", () => {
    expect(shortId("contact_639833a1-4f05-440f-bbab-540dca7ac3b8")).toBe("639833a1");
    expect(shortId("plain")).toBe("plain");
    expect(shortId("dpa_acceptance_92bc0277-7156")).toBe("92bc0277");
  });

  it("builds safe file names", () => {
    expect(safeFileName("contact data/ნინო 2026.json")).toBe("contact-data-2026.json");
    expect(safeFileName("///")).toBe("download");
    expect(isoDay(new Date(Date.UTC(2026, 9, 1, 23, 0)))).toBe("2026-10-01");
  });
});

describe("zonedDayStartUs", () => {
  it("finds local midnight in any time zone", () => {
    expect(zonedDayStartUs("2026-10-01", "Asia/Tbilisi")).toBe(Date.UTC(2026, 8, 30, 20) * 1000);
    expect(zonedDayStartUs("2026-10-01", "UTC")).toBe(Date.UTC(2026, 9, 1) * 1000);
    expect(zonedDayStartUs("2026-03-29", "Europe/Berlin")).toBe(Date.UTC(2026, 2, 28, 23) * 1000);
    expect(zonedDayStartUs("2026-07-01", "America/New_York")).toBe(Date.UTC(2026, 6, 1, 4) * 1000);
    expect(zonedDayStartUs("yesterday", "UTC")).toBeNull();
  });
});
