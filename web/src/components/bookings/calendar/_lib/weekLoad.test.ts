import { describe, expect, it } from "vitest";

import { filledGrid } from "./calendarTypes";
import { layoutStays, stayNights } from "./nightsLayout";
import { dayLoad, loadLevel, placeDayShare } from "./weekLoad";

const slot = (open: number, booked: number, count = 1) => ({
  resource_id: "res_slot",
  is_open: open > 0,
  booking_count: count,
  open_unit_minutes: open,
  booked_unit_minutes: booked,
});
const rooms = (open: number, booked: number) => ({
  resource_id: "res_room",
  is_open: open > 0,
  booking_count: booked,
  open_units: open,
  booked_units: booked,
});

describe("the week's heatmap", () => {
  it("shares minutes for time slots and rooms for nights; closed is no share", () => {
    expect(placeDayShare(slot(600, 150))).toBe(0.25);
    expect(placeDayShare(slot(0, 0))).toBeNull();
    expect(placeDayShare(rooms(2, 1))).toBe(0.5);
    expect(placeDayShare(rooms(0, 0))).toBeNull();
    expect(placeDayShare(rooms(1, 3))).toBe(1);
  });

  it("colours in five steps", () => {
    expect([null, 0, 0.1, 0.3, 0.5, 0.9].map(loadLevel)).toEqual([0, 0, 1, 2, 3, 4]);
  });

  it("adds up a day: time slots by minutes, else rooms", () => {
    expect(dayLoad({ places: [slot(600, 300, 3), slot(600, 0, 0), rooms(2, 2)] })).toEqual({
      share: 0.25,
      count: 5,
    });
    expect(dayLoad({ places: [rooms(2, 1), rooms(1, 1)] })).toEqual({ share: 2 / 3, count: 2 });
    expect(dayLoad({ places: [rooms(0, 0)] })).toEqual({ share: null, count: 0 });
  });
});

describe("the nights grid", () => {
  const stay = (date: string, endDate: string) => ({ date, end_date: endDate, time: null });

  it("takes the nights from check-in to the night before check-out, cut to the window", () => {
    expect(stayNights(stay("2026-10-06", "2026-10-08"), "2026-10-06", 14)).toEqual({
      first: 0,
      count: 2,
      startsBefore: false,
      endsAfter: false,
    });
    expect(stayNights(stay("2026-10-01", "2026-10-07"), "2026-10-06", 14)).toEqual({
      first: 0,
      count: 1,
      startsBefore: true,
      endsAfter: false,
    });
    expect(stayNights(stay("2026-10-18", "2026-10-25"), "2026-10-06", 14)).toEqual({
      first: 12,
      count: 2,
      startsBefore: false,
      endsAfter: true,
    });
    expect(stayNights(stay("2026-10-01", "2026-10-06"), "2026-10-06", 14)).toBeNull();
    // A stay keeps its check-in time; its nights count all the same.
    expect(stayNights({ date: "2026-10-06", end_date: "2026-10-07" }, "2026-10-06", 14)?.count).toBe(1);
  });

  it("stacks the stays of a room type in at least as many lanes as it has rooms", () => {
    const entries = [
      { item: "a", nights: { first: 0, count: 2, startsBefore: false, endsAfter: false } },
      { item: "b", nights: { first: 1, count: 2, startsBefore: false, endsAfter: false } },
    ];
    const { stays, lanes } = layoutStays(entries, 1);
    expect(lanes).toBe(2);
    expect(stays.map((entry) => entry.lane)).toEqual([0, 1]);
    expect(layoutStays([], 3).lanes).toBe(3);
  });
});

describe("a window from the API", () => {
  it("gets every list it left out", () => {
    const grid = filledGrid({
      date_from: "2026-10-06",
      date_to: "2026-10-06",
      timezone: "Asia/Tbilisi",
      is_truncated: false,
      days: [{ date: "2026-10-06" }],
    });
    expect([grid.places, grid.bookings, grid.days[0]?.places, grid.days[0]?.business_ranges]).toEqual([[], [], [], []]);
    expect(filledGrid({ date_from: "2026-10-06", date_to: "2026-10-06", timezone: "UTC", is_truncated: false }).days).toEqual([]);
  });
});
