import { describe, expect, it } from "vitest";

import { calendarWindow, isoWeekdayOf, shiftAnchor, weekStartOf, windowDates } from "./calendarDates";
import { isCalendarView } from "./calendarTypes";
import { clampStart, daySpan, layoutLanes, minuteOfTime, placeLoad, snapMinutes, timeAxis, timeOfMinute } from "./dayLayout";

const booking = (date: string, time: string | null, endDate: string, endTime: string | null) => ({
  date,
  time,
  end_date: endDate,
  end_time: endTime,
});

describe("the calendar's windows", () => {
  it("knows its views", () => {
    expect(isCalendarView("week")).toBe(true);
    expect(isCalendarView("all")).toBe(false);
    expect(isCalendarView(null)).toBe(false);
  });

  it("starts a week on the locale's first day", () => {
    // 2026-10-07 is a Wednesday.
    expect(isoWeekdayOf("2026-10-07")).toBe(3);
    expect(isoWeekdayOf("2026-10-11")).toBe(7);
    expect(weekStartOf("2026-10-07", 1)).toBe("2026-10-05");
    expect(weekStartOf("2026-10-07", 7)).toBe("2026-10-04");
    expect(weekStartOf("2026-10-04", 7)).toBe("2026-10-04");
    expect(weekStartOf("2026-10-09", 6)).toBe("2026-10-03");
  });

  it("reads one day, a week or two weeks of nights, and the arrows step by a day or a week", () => {
    expect(calendarWindow("day", "2026-10-07", 1)).toEqual({ from: "2026-10-07", days: 1 });
    expect(calendarWindow("week", "2026-10-07", 1)).toEqual({ from: "2026-10-05", days: 7 });
    expect(calendarWindow("nights", "2026-10-07", 1)).toEqual({ from: "2026-10-07", days: 14 });
    expect(shiftAnchor("day", "2026-10-31", 1)).toBe("2026-11-01");
    expect(shiftAnchor("week", "2026-10-07", -1)).toBe("2026-09-30");
    expect(shiftAnchor("nights", "2026-10-07", 1)).toBe("2026-10-14");
    expect(windowDates("2026-10-30", 3)).toEqual(["2026-10-30", "2026-10-31", "2026-11-01"]);
  });
});

describe("a booking on one day", () => {
  it("reads times, midnight at the end of a day included", () => {
    expect(minuteOfTime("19:30")).toBe(1170);
    expect(minuteOfTime("24:00")).toBe(1440);
    expect(minuteOfTime(null)).toBeNull();
  });

  it("is cut to the day when it runs over midnight", () => {
    const late = booking("2026-10-06", "23:00", "2026-10-07", "01:30");
    expect(daySpan(late, "2026-10-06")).toEqual({ start: 1380, end: 1440 });
    expect(daySpan(late, "2026-10-07")).toEqual({ start: 0, end: 90 });
    expect(daySpan(late, "2026-10-08")).toBeNull();
    expect(daySpan(late, "2026-10-05")).toBeNull();
    // Ends when the day begins: nothing of it is on the day.
    expect(daySpan(booking("2026-10-06", "22:00", "2026-10-07", "00:00"), "2026-10-07")).toBeNull();
    // A stay has no time.
    expect(daySpan(booking("2026-10-06", null, "2026-10-08", null), "2026-10-06")).toBeNull();
    // An unknown end counts as an hour.
    expect(daySpan(booking("2026-10-06", "10:00", "2026-10-06", null), "2026-10-06")).toEqual({ start: 600, end: 660 });
  });

  it("shows the hours of every opening and booking, to whole hours", () => {
    expect(timeAxis([{ opens_at: 12 * 60 + 30, closes_at: 23 * 60 }], [{ start: 11 * 60 + 15, end: 12 * 60 }])).toEqual({
      start: 11 * 60,
      end: 23 * 60,
    });
    expect(timeAxis([], [])).toEqual({ start: 540, end: 1080 });
    expect(timeAxis([{ opens_at: 18 * 60, closes_at: 1440 }], [])).toEqual({ start: 1080, end: 1440 });
    expect(timeAxis([], [{ start: 600, end: 600 }])).toEqual({ start: 600, end: 660 });
  });

  it("snaps and keeps a start inside the grid", () => {
    expect(snapMinutes(607)).toBe(600);
    expect(snapMinutes(608)).toBe(615);
    expect(clampStart(500, 120, { start: 540, end: 1080 })).toBe(540);
    expect(clampStart(1050, 120, { start: 540, end: 1080 })).toBe(960);
    expect(clampStart(600, 900, { start: 540, end: 1080 })).toBe(540);
    expect(timeOfMinute(1170)).toBe("19:30");
    expect(timeOfMinute(1440)).toBe("23:45");
    expect(timeOfMinute(-5)).toBe("00:00");
  });
});

describe("lanes", () => {
  it("puts overlapping bookings side by side and gives a group one lane count", () => {
    const laned = layoutLanes([
      { item: "a", span: { start: 600, end: 720 } },
      { item: "b", span: { start: 630, end: 690 } },
      { item: "c", span: { start: 700, end: 760 } },
      { item: "d", span: { start: 800, end: 860 } },
    ]);
    const by = Object.fromEntries(laned.map((entry) => [entry.item, [entry.lane, entry.lanes]]));
    expect(by).toEqual({ a: [0, 2], b: [1, 2], c: [1, 2], d: [0, 1] });
  });

  it("lets a booking that starts when another ends take its lane", () => {
    const laned = layoutLanes([
      { item: "a", span: { start: 600, end: 660 } },
      { item: "b", span: { start: 660, end: 720 } },
    ]);
    expect(laned.map((entry) => [entry.lane, entry.lanes])).toEqual([
      [0, 1],
      [0, 1],
    ]);
  });
});

describe("a place's load", () => {
  const terrace = {
    resource_id: "res_1",
    is_open: true,
    open_ranges: [{ opens_at: 720, closes_at: 1380 }],
    booking_count: 2,
    open_unit_minutes: 1980,
    booked_unit_minutes: 150,
  };

  it("counts the minutes booked within the opening hours", () => {
    expect(placeLoad(terrace, [{ start: 780, end: 840 }, { start: 690, end: 750 }])).toEqual({ share: 90 / 1980, count: 2 });
  });

  it("is null on a closed day", () => {
    expect(placeLoad({ ...terrace, is_open: false, open_unit_minutes: 0 }, [])).toEqual({ share: null, count: 0 });
  });
});
