import { describe, expect, it } from "vitest";

import { filterCounts, holdOptions, isRemovable, isWaitlistFilter, minutesLeft, wishedWindow } from "./waitlistModel";

describe("the waitlist page", () => {
  it("knows its three lists", () => {
    expect(isWaitlistFilter("booked")).toBe(true);
    expect(isWaitlistFilter("offered")).toBe(false);
    expect(isWaitlistFilter(undefined)).toBe(false);
  });

  it("counts waiting and held entries as one list", () => {
    expect(
      filterCounts([
        { status: "waiting", count: 3 },
        { status: "offered", count: 1 },
        { status: "booked", count: 2 },
      ]),
    ).toEqual({ active: 4, booked: 2, ended: 0 });
  });

  it("reads the hours a customer would take", () => {
    expect(wishedWindow({ time_from: "19:00", time_to: "21:00" })).toEqual({ kind: "between", from: "19:00", to: "21:00" });
    expect(wishedWindow({ time_from: "19:00", time_to: null })).toEqual({ kind: "from", from: "19:00" });
    expect(wishedWindow({ time_from: null, time_to: "12:00" })).toEqual({ kind: "until", to: "12:00" });
    expect(wishedWindow({ time_from: null, time_to: null })).toEqual({ kind: "any" });
  });

  it("lets staff take off only entries still open", () => {
    expect(isRemovable({ status: "waiting" })).toBe(true);
    expect(isRemovable({ status: "offered" })).toBe(true);
    expect(isRemovable({ status: "booked" })).toBe(false);
    expect(isRemovable({ status: "expired" })).toBe(false);
  });

  it("rounds the minutes left up and stops at zero", () => {
    const now = Date.UTC(2026, 9, 7, 18, 0);
    const inMicros = (ms: number) => ms * 1000;
    expect(minutesLeft(inMicros(now + 12 * 60_000 + 1), now)).toBe(13);
    expect(minutesLeft(inMicros(now + 60_000), now)).toBe(1);
    expect(minutesLeft(inMicros(now - 1), now)).toBe(0);
    expect(minutesLeft(null, now)).toBeNull();
  });

  it("offers the usual holds, the stored one among them", () => {
    expect(holdOptions(30)).toEqual([15, 20, 30, 45, 60, 90, 120]);
    expect(holdOptions(25)).toEqual([15, 20, 25, 30, 45, 60, 90, 120]);
  });
});
