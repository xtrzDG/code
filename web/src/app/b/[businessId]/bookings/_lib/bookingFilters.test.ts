import { describe, expect, it } from "vitest";

import {
  bookingApiQuery,
  bookingFiltersQuery,
  DEFAULT_BOOKING_FILTERS,
  isRangeValid,
  parseBookingFilters,
  rangeDates,
  sheetFilterCount,
  withoutSheetFilters,
} from "./bookingFilters";

describe("booking ranges", () => {
  const today = "2026-10-01";

  it("turn presets into local dates", () => {
    expect(rangeDates({ range: "upcoming", from: null, to: null }, today)).toEqual({ from: today, to: null });
    expect(rangeDates({ range: "today", from: null, to: null }, today)).toEqual({ from: today, to: today });
    expect(rangeDates({ range: "tomorrow", from: null, to: null }, today)).toEqual({ from: "2026-10-02", to: "2026-10-02" });
    expect(rangeDates({ range: "week", from: null, to: null }, today)).toEqual({ from: today, to: "2026-10-07" });
    expect(rangeDates({ range: "past", from: null, to: null }, today)).toEqual({ from: "2026-09-01", to: "2026-09-30" });
    expect(rangeDates({ range: "custom", from: "2026-11-01", to: null }, today)).toEqual({ from: "2026-11-01", to: null });
  });

  it("reject a start after the end", () => {
    expect(isRangeValid({ from: "2026-10-02", to: "2026-10-01" })).toBe(false);
    expect(isRangeValid({ from: "2026-10-01", to: null })).toBe(true);
  });
});

describe("booking filters in the URL", () => {
  it("round-trip and drop invalid values", () => {
    const filters = {
      ...DEFAULT_BOOKING_FILTERS,
      phoneView: "all" as const,
      range: "custom" as const,
      from: "2026-10-01",
      to: "2026-10-07",
      status: "pending" as const,
    };
    const query = bookingFiltersQuery(filters);
    expect(query).toBe("range=custom&from=2026-10-01&to=2026-10-07&status=pending");
    expect(parseBookingFilters(Object.fromEntries(new URLSearchParams(query)))).toEqual(filters);
    expect(parseBookingFilters({ range: "decade", from: "2026-13-01", status: "lost", test: ["1", "1"] })).toEqual(
      DEFAULT_BOOKING_FILTERS,
    );
    expect(bookingFiltersQuery(DEFAULT_BOOKING_FILTERS)).toBe("");
  });

  it("open a phone on today's agenda unless the address asks for the list", () => {
    expect(parseBookingFilters({}).phoneView).toBe("today");
    expect(parseBookingFilters({ status: "pending" }).phoneView).toBe("all");
    expect(parseBookingFilters({ range: "week" }).phoneView).toBe("all");
    expect(parseBookingFilters({ view: "all" }).phoneView).toBe("all");
    expect(parseBookingFilters({ view: "today", test: "1" }).phoneView).toBe("today");
    expect(parseBookingFilters({ view: "calendar" }).phoneView).toBe("today");

    const list = { ...DEFAULT_BOOKING_FILTERS, phoneView: "all" as const };
    expect(bookingFiltersQuery(list)).toBe("view=all");
    expect(parseBookingFilters(Object.fromEntries(new URLSearchParams("view=all")))).toEqual(list);
    const agendaWithTest = { ...DEFAULT_BOOKING_FILTERS, includeTest: true };
    expect(bookingFiltersQuery(agendaWithTest)).toBe("test=1&view=today");
    expect(parseBookingFilters(Object.fromEntries(new URLSearchParams("test=1&view=today")))).toEqual(agendaWithTest);
  });
});

describe("the phone's filter sheet", () => {
  it("counts and clears status, place and test bookings, not the dates", () => {
    expect(sheetFilterCount(DEFAULT_BOOKING_FILTERS)).toBe(0);
    const chosen = { ...DEFAULT_BOOKING_FILTERS, range: "week" as const, status: "pending" as const, resourceId: "resource_1", includeTest: true };
    expect(sheetFilterCount(chosen)).toBe(3);
    expect(withoutSheetFilters(chosen)).toEqual({ ...DEFAULT_BOOKING_FILTERS, range: "week" });
  });
});

describe("list query", () => {
  it("sends every filter to the API and reads past ranges latest first", () => {
    expect(bookingApiQuery(DEFAULT_BOOKING_FILTERS, { from: "2026-10-01", to: null })).toEqual({
      from: "2026-10-01",
      order: "earliest_first",
    });
    expect(
      bookingApiQuery(
        { ...DEFAULT_BOOKING_FILTERS, range: "past", status: "no_show", resourceId: "resource_9", includeTest: true },
        { from: "2026-09-01", to: "2026-09-30" },
      ),
    ).toEqual({
      from: "2026-09-01",
      to: "2026-09-30",
      status: "no_show",
      resource_id: "resource_9",
      include_sandbox: "true",
      order: "latest_first",
    });
  });
});
