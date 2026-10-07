import { describe, expect, it } from "vitest";

import type { Schema } from "@/api/types";

import {
  bookingWhen,
  fillPlaceholders,
  formatLocalDate,
  formatLocalTime,
  moveTarget,
  todayIn,
  wallClock,
} from "./format";

type View = Schema<"ManagedBookingView">;

function booking(fields: Partial<View>): View {
  return {
    token: "t".repeat(60),
    business_name: "Salobie Bia",
    status: "confirmed",
    booking_unit: "time_slot",
    date: "2026-10-06",
    time: "19:00",
    end_date: "2026-10-06",
    end_time: "21:00",
    timezone: "Asia/Tbilisi",
    party_size: 2,
    language: "en",
    can_cancel: true,
    can_reschedule: true,
    is_over: false,
    ...fields,
  };
}

describe("wallClock", () => {
  it("reads a local date and time as the same clock in UTC", () => {
    expect(wallClock("2026-10-06", "19:00")?.toISOString()).toBe("2026-10-06T19:00:00.000Z");
    expect(wallClock("2026-10-06")?.toISOString()).toBe("2026-10-06T00:00:00.000Z");
  });

  it("refuses malformed text", () => {
    expect(wallClock("06.10.2026")).toBeNull();
    expect(wallClock("2026-10-06", "7pm")).toBeNull();
  });
});

describe("formatLocalDate and formatLocalTime", () => {
  it("write the day and the time in the guest's language, whatever the zone", () => {
    expect(formatLocalDate("2026-10-06", "en")).toBe("Tuesday, October 6, 2026");
    expect(formatLocalDate("2026-10-06", "ru")).toMatch(/^Вторник, 6 октября 2026/);
    expect(formatLocalDate("2026-10-06", "ka")).toContain("ოქტომბერი");
    expect(formatLocalTime("19:00", "en")).toMatch(/^7:00\s?PM$/);
    expect(formatLocalTime("19:00", "ru")).toBe("19:00");
    expect(formatLocalTime("19:00", "he")).toBe("19:00");
  });

  it("leave malformed text as it is", () => {
    expect(formatLocalDate("soon", "en")).toBe("soon");
    expect(formatLocalTime("later", "en")).toBe("later");
  });
});

describe("bookingWhen", () => {
  it("writes a visit's day and times", () => {
    expect(bookingWhen(booking({}), "ru")).toEqual({
      date: expect.stringMatching(/^Вторник/),
      times: "19:00 – 21:00",
      departure: null,
    });
  });

  it("names the end day of a visit past midnight", () => {
    const late = bookingWhen(booking({ time: "23:00", end_date: "2026-10-07", end_time: "01:00" }), "ru");

    expect(late.times).toMatch(/^23:00 – Среда, 7 октября 2026.* 01:00$/);
  });

  it("writes a stay's arrival and departure days", () => {
    const stay = bookingWhen(
      booking({ booking_unit: "night", time: "14:00", end_date: "2026-10-09", end_time: "12:00" }),
      "en",
    );

    expect(stay).toEqual({ date: "Tuesday, October 6, 2026", times: null, departure: "Friday, October 9, 2026" });
  });
});

describe("moveTarget", () => {
  it("names the new day, with the time when there is one", () => {
    expect(moveTarget("2026-10-07", "20:00", "ru")).toMatch(/^Среда, 7 октября 2026.*, 20:00$/);
    expect(moveTarget("2026-10-07", null, "en")).toBe("Wednesday, October 7, 2026");
  });
});

describe("todayIn", () => {
  it("is the business's date, not the visitor's", () => {
    const lateMonday = new Date(Date.UTC(2026, 9, 5, 22, 0));

    expect(todayIn("Asia/Tbilisi", lateMonday)).toBe("2026-10-06");
    expect(todayIn("America/Los_Angeles", lateMonday)).toBe("2026-10-05");
    expect(todayIn("Mars/Olympus", lateMonday)).toBe("2026-10-05");
  });
});

describe("fillPlaceholders", () => {
  it("fills known names and keeps the others", () => {
    expect(fillPlaceholders("Move to {when}", { when: "Friday" })).toBe("Move to Friday");
    expect(fillPlaceholders("{business} knows", {})).toBe("{business} knows");
  });
});
