import { describe, expect, it } from "vitest";

import { growthLines } from "./growthLines";

const NONE = { waitlist_booking_count: 0, campaign_booking_count: 0, waitlist_value_minor: null, campaign_value_minor: null };

describe("the growth lines", () => {
  it("show nothing for a business without waitlist or return-visit bookings", () => {
    expect(growthLines(NONE, NONE)).toEqual([]);
  });

  it("show each origin with its worth and the period before", () => {
    const current = { ...NONE, waitlist_booking_count: 2, waitlist_value_minor: 12_000 };
    const previous = { ...NONE, campaign_booking_count: 1 };
    expect(growthLines(current, previous)).toEqual([
      { origin: "waitlist", count: 2, previousCount: 0, valueMinor: 12_000 },
      { origin: "campaign", count: 0, previousCount: 1, valueMinor: null },
    ]);
  });

  it("read reports stored before the lines existed as none", () => {
    expect(growthLines({}, {})).toEqual([]);
  });
});
