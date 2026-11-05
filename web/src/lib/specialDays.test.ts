import { describe, expect, it } from "vitest";

import {
  formatLocalDate,
  intervalsLabel,
  isLocalDate,
  specialHoursIntervals,
  splitExceptions,
  todayInTimeZone,
  weekdayOfDate,
} from "./specialDays";

describe("local dates", () => {
  it("accepts real dates only", () => {
    expect(isLocalDate("2026-12-31")).toBe(true);
    expect(isLocalDate("2028-02-29")).toBe(true);
    expect(isLocalDate("2026-02-29")).toBe(false);
    expect(isLocalDate("2026-13-01")).toBe(false);
    expect(isLocalDate("31.12.2026")).toBe(false);
  });

  it("finds today in the business time zone", () => {
    const instant = new Date("2026-10-01T22:30:00Z");
    expect(todayInTimeZone(instant, "Asia/Tbilisi")).toBe("2026-10-02");
    expect(todayInTimeZone(instant, "America/New_York")).toBe("2026-10-01");
  });

  it("knows the ISO weekday of a date and formats it in the UI language", () => {
    expect(weekdayOfDate("2026-12-31")).toBe(4);
    expect(weekdayOfDate("2027-01-03")).toBe(7);
    expect(formatLocalDate("2026-12-31", "en")).toBe("Thu, Dec 31, 2026");
  });

  it("splits upcoming and past days", () => {
    const { upcoming, past } = splitExceptions(
      [{ date: "2026-12-31" }, { date: "2026-01-01" }, { date: "2026-10-01" }, { date: "2025-12-31" }],
      "2026-10-01",
    );
    expect(upcoming.map((item) => item.date)).toEqual(["2026-10-01", "2026-12-31"]);
    expect(past.map((item) => item.date)).toEqual(["2026-01-01", "2025-12-31"]);
  });
});

describe("special hours", () => {
  it("builds intervals on the weekday of the date, 00:00 closing as midnight", () => {
    expect(
      specialHoursIntervals("2026-12-31", [
        { key: "b", opens: "18:00", closes: "00:00" },
        { key: "a", opens: "10:00", closes: "16:00" },
      ]),
    ).toEqual({
      ok: true,
      intervals: [
        { weekday: 4, opens_at: 600, closes_at: 960 },
        { weekday: 4, opens_at: 1080, closes_at: 1440 },
      ],
    });
  });

  it("refuses empty, reversed, malformed and overlapping hours", () => {
    expect(specialHoursIntervals("2026-12-31", [])).toEqual({ ok: false, error: "knowledge.exceptions.errors.hoursRequired" });
    expect(specialHoursIntervals("2026-12-31", [{ key: "a", opens: "16:00", closes: "10:00" }])).toEqual({
      ok: false,
      error: "knowledge.exceptions.errors.closesBeforeOpens",
    });
    expect(specialHoursIntervals("2026-12-31", [{ key: "a", opens: "", closes: "10:00" }])).toEqual({ ok: false, error: "validation.time" });
    expect(
      specialHoursIntervals("2026-12-31", [
        { key: "a", opens: "10:00", closes: "16:00" },
        { key: "b", opens: "15:00", closes: "18:00" },
      ]),
    ).toEqual({ ok: false, error: "validation.hoursOverlap" });
  });

  it("labels intervals as times of day", () => {
    expect(intervalsLabel([{ opens_at: 1080, closes_at: 1440 }, { opens_at: 600, closes_at: 960 }])).toBe("10:00–16:00, 18:00–24:00");
  });
});
