import { describe, expect, it } from "vitest";

import {
  addDays,
  daysBetween,
  formatLocalDate,
  formatLocalTime,
  formatRelative,
  isLocalDate,
  isLocalTime,
  localDateOf,
  todayIn,
} from "./dates";

describe("local dates", () => {
  it("validates calendar dates and clock times", () => {
    expect(isLocalDate("2026-10-02")).toBe(true);
    expect(isLocalDate("2026-02-30")).toBe(false);
    expect(isLocalDate("2026-1-2")).toBe(false);
    expect(isLocalTime("20:00")).toBe(true);
    expect(isLocalTime("24:00")).toBe(false);
    expect(isLocalTime("7:30")).toBe(false);
  });

  it("adds days across months, years and leap days", () => {
    expect(addDays("2026-02-28", 1)).toBe("2026-03-01");
    expect(addDays("2028-02-28", 1)).toBe("2028-02-29");
    expect(addDays("2026-12-31", 1)).toBe("2027-01-01");
    expect(addDays("2026-10-01", -30)).toBe("2026-09-01");
    expect(daysBetween("2026-09-02", "2026-10-01")).toBe(29);
  });

  it("finds the date of an instant in the business time zone", () => {
    // 2026-10-01 21:30 UTC is already Oct 2 in Tbilisi (UTC+4) and still Oct 1 in New York.
    const instant = Date.UTC(2026, 9, 1, 21, 30) * 1000;
    expect(localDateOf(instant, "Asia/Tbilisi")).toBe("2026-10-02");
    expect(localDateOf(instant, "America/New_York")).toBe("2026-10-01");
    expect(todayIn("Asia/Tokyo", new Date(Date.UTC(2026, 9, 1, 16)))).toBe("2026-10-02");
  });

  it("formats local values without shifting them to the browser's zone", () => {
    expect(formatLocalDate("2026-10-02", "en", { weekday: "short", day: "numeric", month: "short" })).toBe(
      "Fri, Oct 2",
    );
    expect(formatLocalDate("2026-10-02", "ru", { day: "numeric", month: "long" })).toBe("2 октября");
    expect(formatLocalDate("not a date", "en")).toBe("not a date");
    expect(formatLocalTime("20:00", "en")).toBe("8:00 PM");
    expect(formatLocalTime("20:05", "ru")).toBe("20:05");
  });
});

describe("relative time", () => {
  const now = new Date(Date.UTC(2026, 9, 1, 12, 0));

  it("describes recent instants", () => {
    expect(formatRelative(now.getTime() * 1000 - 5 * 60 * 1_000_000, "en", { now })).toBe("5 minutes ago");
    expect(formatRelative(now.getTime() * 1000 - 3 * 3600 * 1_000_000, "en", { now })).toBe("3 hours ago");
    expect(formatRelative(now.getTime() * 1000 - 26 * 3600 * 1_000_000, "en", { now })).toBe("yesterday");
    expect(formatRelative(now.getTime() * 1000, "en", { now })).toBe("now");
  });

  it("gives up on old instants", () => {
    expect(formatRelative(now.getTime() * 1000 - 9 * 86_400 * 1_000_000, "en", { now })).toBeNull();
  });
});
