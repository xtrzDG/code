import { describe, expect, it } from "vitest";

import type { ValueTotals } from "@/components/value/valueModel";

import { REPORT_ROWS, reportsPath, reportTitle, splitMinutes, visibleRows } from "./reportsModel";

const EMPTY: ValueTotals = {
  conversation_count: 0,
  after_hours_conversation_count: 0,
  customer_message_count: 0,
  assistant_reply_count: 0,
  call_count: 0,
  booking_count: 0,
  assistant_booking_count: 0,
  request_count: 0,
  handoff_count: 0,
  staff_minutes_saved: 0,
  estimated_revenue_minor: null,
  valued_booking_count: 0,
  waitlist_booking_count: 0,
  campaign_booking_count: 0,
};

describe("a stored report", () => {
  it("is named by its period", () => {
    const base = { period_key: "2026-09", date_from: "2026-09-01", date_to: "2026-09-30" };
    expect(reportTitle({ ...base, kind: "monthly" }, "en")).toBe("September 2026");
    expect(reportTitle({ kind: "weekly", period_key: "2026-W39", date_from: "2026-09-21", date_to: "2026-09-27" }, "en")).toMatch(
      /Sep 21\s*–\s*27, 2026/,
    );
    expect(reportTitle({ kind: "daily", period_key: "2026-10-02", date_from: "2026-10-02", date_to: "2026-10-02" }, "en")).toBe(
      "Friday, October 2, 2026",
    );
  });

  it("shows the money row only with an estimate", () => {
    expect(visibleRows(EMPTY, EMPTY).some((row) => row.kind === "money")).toBe(false);
    expect(visibleRows({ ...EMPTY, estimated_revenue_minor: 12_000 }, EMPTY)).toHaveLength(REPORT_ROWS.length - 4);
  });

  it("shows the waitlist's and return visits' rows only when either period had such bookings", () => {
    const fields = (current: typeof EMPTY, previous: typeof EMPTY) => visibleRows(current, previous).map((row) => row.field);
    expect(fields(EMPTY, EMPTY)).not.toContain("waitlist_booking_count");
    const withWaitlist = { ...EMPTY, waitlist_booking_count: 2, waitlist_value_minor: 9_000 };
    expect(fields(withWaitlist, EMPTY)).toEqual(expect.arrayContaining(["waitlist_booking_count", "waitlist_value_minor"]));
    expect(fields(withWaitlist, EMPTY)).not.toContain("campaign_booking_count");
    const backAfterMessage = { ...EMPTY, campaign_booking_count: 1 };
    // A booking without its own price: the count, no worth.
    expect(fields(EMPTY, backAfterMessage)).toContain("campaign_booking_count");
    expect(fields(EMPTY, backAfterMessage)).not.toContain("campaign_value_minor");
  });

  it("splits staff minutes into hours and minutes", () => {
    expect(splitMinutes(555)).toEqual({ hours: 9, minutes: 15 });
    expect(splitMinutes(45)).toEqual({ hours: 0, minutes: 45 });
  });

  it("opens the Reports page on one report", () => {
    expect(reportsPath("business_1")).toBe("/b/business_1/overview/reports");
    expect(reportsPath("business_1", "value_report_9")).toBe("/b/business_1/overview/reports?report=value_report_9");
  });
});
