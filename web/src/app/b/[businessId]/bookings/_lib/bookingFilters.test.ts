import { describe, expect, it } from "vitest";

import {
  bookingApiQuery,
  bookingFiltersQuery,
  DEFAULT_BOOKING_FILTERS,
  isRangeValid,
  parseBookingFilters,
  rangeDates,
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
    const filters = { ...DEFAULT_BOOKING_FILTERS, range: "custom" as const, from: "2026-10-01", to: "2026-10-07", status: "pending" as const };
    const query = bookingFiltersQuery(filters);
    expect(query).toBe("range=custom&from=2026-10-01&to=2026-10-07&status=pending");
    expect(parseBookingFilters(Object.fromEntries(new URLSearchParams(query)))).toEqual(filters);
    expect(parseBookingFilters({ range: "decade", from: "2026-13-01", status: "lost", test: ["1", "1"] })).toEqual(
      DEFAULT_BOOKING_FILTERS,
    );
    expect(bookingFiltersQuery(DEFAULT_BOOKING_FILTERS)).toBe("");
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
