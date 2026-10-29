import { describe, expect, it } from "vitest";

import type { OpeningInterval } from "@/api/types";

import { businessClock, openState, weekRows } from "./openingHours";

const HOUR = 60;

function every(days: number[], opens: number, closes: number): OpeningInterval[] {
  return days.map((weekday) => ({ weekday: weekday as OpeningInterval["weekday"], opens_at: opens, closes_at: closes }));
}

const WEEKDAYS_10_TO_23 = every([1, 2, 3, 4, 5], 10 * HOUR, 23 * HOUR);

describe("businessClock", () => {
  it("reads the business's wall clock, not the visitor's", () => {
    // Monday 2026-10-05 21:30 UTC is Tuesday 01:30 in Tbilisi (UTC+4).
    const now = new Date(Date.UTC(2026, 9, 5, 21, 30));

    expect(businessClock(now, "Asia/Tbilisi")).toEqual({ weekday: 2, minute: 90 });
    expect(businessClock(now, "America/New_York")).toEqual({ weekday: 1, minute: 17 * HOUR + 30 });
  });

  it("reads an unknown zone as UTC", () => {
    const now = new Date(Date.UTC(2026, 9, 4, 8, 5));

    expect(businessClock(now, "Mars/Olympus")).toEqual({ weekday: 7, minute: 8 * HOUR + 5 });
  });
});

describe("openState", () => {
  it("is open until the closing time", () => {
    expect(openState(WEEKDAYS_10_TO_23, { weekday: 3, minute: 12 * HOUR })).toEqual({
      kind: "open",
      closesAt: "23:00",
    });
  });

  it("opens later today, tomorrow or on a later day", () => {
    expect(openState(WEEKDAYS_10_TO_23, { weekday: 3, minute: 8 * HOUR })).toEqual({
      kind: "closed",
      opensAt: "10:00",
      inDays: 0,
      weekday: 3,
    });
    expect(openState(WEEKDAYS_10_TO_23, { weekday: 3, minute: 23 * HOUR + 30 })).toMatchObject({
      inDays: 1,
      weekday: 4,
    });
    // Friday night: closed over the weekend until Monday.
    expect(openState(WEEKDAYS_10_TO_23, { weekday: 5, minute: 23 * HOUR + 30 })).toEqual({
      kind: "closed",
      opensAt: "10:00",
      inDays: 3,
      weekday: 1,
    });
  });

  it("follows an evening past midnight into the next day", () => {
    // Saturday 18:00–24:00 and Sunday 00:00–02:00, as the API splits it.
    const lateBar = [
      { weekday: 6, opens_at: 18 * HOUR, closes_at: 24 * HOUR },
      { weekday: 7, opens_at: 0, closes_at: 2 * HOUR },
    ] as OpeningInterval[];

    expect(openState(lateBar, { weekday: 6, minute: 23 * HOUR })).toEqual({ kind: "open", closesAt: "02:00" });
    expect(openState(lateBar, { weekday: 7, minute: HOUR })).toEqual({ kind: "open", closesAt: "02:00" });
  });

  it("is always open around the clock, unknown without hours", () => {
    expect(openState(every([1, 2, 3, 4, 5, 6, 7], 0, 24 * HOUR), { weekday: 4, minute: 3 * HOUR })).toEqual({
      kind: "always",
    });
    expect(openState([], { weekday: 4, minute: 0 })).toEqual({ kind: "unknown" });
  });
});

describe("weekRows", () => {
  it("lists Monday to Sunday with closed days and today marked", () => {
    const rows = weekRows(
      [...WEEKDAYS_10_TO_23, ...every([6], 12 * HOUR, 15 * HOUR), ...every([6], 18 * HOUR, 22 * HOUR)],
      6,
    );

    expect(rows.map((row) => row.weekday)).toEqual([1, 2, 3, 4, 5, 6, 7]);
    expect(rows[0]).toEqual({ weekday: 1, ranges: ["10:00–23:00"], isAllDay: false, isToday: false });
    expect(rows[5]).toEqual({ weekday: 6, ranges: ["12:00–15:00", "18:00–22:00"], isAllDay: false, isToday: true });
    expect(rows[6]).toEqual({ weekday: 7, ranges: [], isAllDay: false, isToday: false });
  });

  it("marks a day open around the clock", () => {
    const [monday] = weekRows(every([1], 0, 24 * HOUR), 1);

    expect(monday).toMatchObject({ isAllDay: true, ranges: [] });
  });
});
