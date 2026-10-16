import { describe, expect, it } from "vitest";

import { EMPTY_SEGMENT_FORM, formOf, rulesKey, rulesOf, segmentBody, summaryParts, type Segment } from "./segmentRules";

const segment: Segment = {
  id: "segment_a",
  name: "Not back in 60 days",
  rules: { tag: "regular", last_visit_days_ago: 60, min_bookings: 2, max_bookings: null, vip_only: false },
  created_at: 1,
  updated_at: 2,
};

describe("the segment editor", () => {
  it("fills the form from a saved segment", () => {
    expect(formOf(segment)).toEqual({
      name: "Not back in 60 days",
      tag: "regular",
      lastVisitDays: "60",
      minBookings: "2",
      maxBookings: "",
      vipOnly: false,
    });
  });

  it("turns the form into rules, empty fields left out", () => {
    expect(rulesOf({ ...EMPTY_SEGMENT_FORM, tag: "  big  table ", minBookings: " 3 ", vipOnly: true }).rules).toEqual({
      tag: "big table",
      last_visit_days_ago: null,
      min_bookings: 3,
      max_bookings: null,
      vip_only: true,
    });
  });

  it("refuses numbers out of range or not whole", () => {
    expect(rulesOf({ ...EMPTY_SEGMENT_FORM, lastVisitDays: "0" }).errors).toEqual({ lastVisitDays: "segments.errors.days" });
    expect(rulesOf({ ...EMPTY_SEGMENT_FORM, lastVisitDays: "3651" }).errors.lastVisitDays).toBe("segments.errors.days");
    expect(rulesOf({ ...EMPTY_SEGMENT_FORM, minBookings: "1.5" }).errors).toEqual({ minBookings: "segments.errors.bookings" });
    expect(rulesOf({ ...EMPTY_SEGMENT_FORM, maxBookings: "-1" }).errors).toEqual({ maxBookings: "segments.errors.bookings" });
    expect(rulesOf({ ...EMPTY_SEGMENT_FORM, minBookings: "5", maxBookings: "2" }).errors).toEqual({
      maxBookings: "segments.errors.minMax",
    });
    expect(rulesOf({ ...EMPTY_SEGMENT_FORM, minBookings: "5", maxBookings: "2" }).rules).toBeNull();
  });

  it("needs a name of 1 to 60 characters to save", () => {
    expect(segmentBody({ ...EMPTY_SEGMENT_FORM, name: "  " }).errors).toEqual({ name: "segments.errors.name" });
    expect(segmentBody({ ...EMPTY_SEGMENT_FORM, name: "x".repeat(61) }).body).toBeNull();
    expect(segmentBody({ ...formOf(segment), name: "  Lapsed\tregulars " }).body).toEqual({
      name: "Lapsed regulars",
      rules: segment.rules,
    });
  });

  it("keys rules by what they mean", () => {
    expect(rulesKey({ tag: "Regular", vip_only: false })).toBe(rulesKey({ tag: "regular", vip_only: false, min_bookings: null }));
    expect(rulesKey({ vip_only: true })).not.toBe(rulesKey({ vip_only: false }));
  });

  it("says the rules as a sentence", () => {
    expect(summaryParts(segment.rules)).toEqual([
      { key: "segments.summary.tag", values: { tag: "regular" } },
      { plural: "segments.summary.lastVisit", count: 60 },
      { plural: "segments.summary.minBookings", count: 2 },
    ]);
    expect(summaryParts({ max_bookings: 0, vip_only: true })).toEqual([
      { plural: "segments.summary.maxBookings", count: 0 },
      { key: "segments.summary.vipOnly" },
    ]);
    expect(summaryParts({ vip_only: false })).toEqual([{ key: "segments.summary.everyone" }]);
  });
});
