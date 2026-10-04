import { describe, expect, it } from "vitest";

import {
  changeLabel,
  changeOf,
  hadNoActivity,
  earningCount,
  formatMonth,
  formatWholeMoney,
  isReportKind,
  moneyFormula,
  monthSoFar,
  nextMonthStart,
  periodDays,
  savedTime,
  sentimentOf,
  type ValueTotals,
} from "./valueModel";

const TOTALS: ValueTotals = {
  conversation_count: 134,
  after_hours_conversation_count: 18,
  customer_message_count: 400,
  assistant_reply_count: 380,
  call_count: 12,
  booking_count: 30,
  assistant_booking_count: 22,
  request_count: 9,
  handoff_count: 4,
  staff_minutes_saved: 540,
  estimated_revenue_minor: 264_000,
  valued_booking_count: 0,
};

const plain = (value: number) => String(value);
const percent = (value: number) => `${value}%`;

describe("a change against the period before", () => {
  it("is a whole percent with its direction", () => {
    expect(changeOf(116, 100)).toEqual({ direction: "up", percent: 16, difference: 16 });
    expect(changeOf(92, 100)).toEqual({ direction: "down", percent: 8, difference: -8 });
    expect(changeOf(5, 5)).toEqual({ direction: "same", percent: 0, difference: 0 });
  });

  it("has no percent when the period before had none, and nothing when both are empty", () => {
    expect(changeOf(5, 0)).toEqual({ direction: "up", percent: null, difference: 5 });
    expect(changeOf(0, 0)).toBeNull();
  });

  it("reads as an arrow and an amount", () => {
    expect(changeLabel(changeOf(116, 100)!, plain, percent)).toBe("▲ 16%");
    expect(changeLabel(changeOf(92, 100)!, plain, percent)).toBe("▼ 8%");
    expect(changeLabel(changeOf(5, 0)!, plain, percent)).toBe("▲ +5");
    expect(changeLabel(changeOf(1001, 1000)!, plain, percent)).toBe("▲ <1%");
    expect(changeLabel(changeOf(3, 3)!, plain, percent)).toBe("= 0%");
  });

  it("is good news only for numbers where more is better", () => {
    expect(sentimentOf(changeOf(2, 1)!, "more-is-better")).toBe("positive");
    expect(sentimentOf(changeOf(1, 2)!, "more-is-better")).toBe("negative");
    expect(sentimentOf(changeOf(2, 1)!, "neutral")).toBe("neutral");
    expect(sentimentOf(changeOf(1, 1)!, "more-is-better")).toBe("neutral");
  });
});

describe("the value numbers", () => {
  it("count the assistant's bookings, or its requests for niches that take orders", () => {
    expect(earningCount("bookings", TOTALS)).toBe(22);
    expect(earningCount("requests", TOTALS)).toBe(9);
  });

  it("show staff time in hours from an hour on", () => {
    expect(savedTime(540)).toEqual({ unit: "hours", count: 9 });
    expect(savedTime(95)).toEqual({ unit: "hours", count: 2 });
    expect(savedTime(45)).toEqual({ unit: "minutes", count: 45 });
  });

  it("show money in whole units of the currency", () => {
    expect(formatWholeMoney(264_000, "GEL", "en")).toBe("GEL\u00a02,640");
    expect(formatWholeMoney(1_250_050, "JPY", "en")).toBe("¥1,250,050");
    expect(formatWholeMoney(4_050, "EUR", "en")).toBe("€41");
  });
});

describe("the periods", () => {
  it("count days inclusively", () => {
    expect(periodDays("2026-09-04", "2026-10-03")).toBe(30);
    expect(periodDays("2026-10-03", "2026-10-03")).toBe(1);
  });

  it("name a month and find the next report day", () => {
    expect(formatMonth("2026-09", "en")).toBe("September 2026");
    expect(formatMonth("2026-W39", "en")).toBe("2026-W39");
    expect(nextMonthStart("2026-10-03")).toBe("2026-11-01");
    expect(nextMonthStart("2026-12-31")).toBe("2027-01-01");
    expect(monthSoFar("2026-10-03")).toEqual({ from: "2026-10-01", to: "2026-10-03" });
  });

  it("know the kinds of reports", () => {
    expect(isReportKind("weekly")).toBe(true);
    expect(isReportKind("yearly")).toBe(false);
    expect(isReportKind(undefined)).toBe(false);
  });
});

describe("hadNoActivity", () => {
  const quiet = {
    conversation_count: 0,
    customer_message_count: 0,
    booking_count: 0,
    request_count: 0,
    handoff_count: 0,
    call_count: 0,
  };

  it("is true only when nothing at all happened in the period", () => {
    expect(hadNoActivity(quiet)).toBe(true);
    expect(hadNoActivity({ ...quiet, call_count: 1 })).toBe(false);
    expect(hadNoActivity({ ...quiet, customer_message_count: 3 })).toBe(false);
  });
});

describe("the line under the money", () => {
  it("names the average check when the money rests on it alone", () => {
    expect(moneyFormula("bookings", { ...TOTALS, revenue_source: "average_check" }, 12_000)).toEqual({
      kind: "check",
      count: 22,
      checkMinor: 12_000,
    });
    // Reports stored before bookings had values carry no source.
    expect(moneyFormula("requests", TOTALS, 12_000)).toEqual({ kind: "check", count: 9, checkMinor: 12_000 });
  });

  it("says the bookings count at their own prices when every one has a price", () => {
    const booked = { ...TOTALS, revenue_source: "booked_values" as const, valued_booking_count: 22, booked_value_minor: 264_000 };
    expect(moneyFormula("bookings", booked, 12_000)).toEqual({ kind: "booked", valued: 22 });
    // Without an average check the priced bookings still make the money.
    expect(moneyFormula("bookings", booked, null)).toEqual({ kind: "booked", valued: 22 });
  });

  it("splits mixed money into the priced bookings and the rest at the check", () => {
    const mixed = { ...TOTALS, revenue_source: "mixed" as const, valued_booking_count: 20, booked_value_minor: 240_000 };
    expect(moneyFormula("bookings", mixed, 12_000)).toEqual({
      kind: "mixed",
      bookedMinor: 240_000,
      unvalued: 2,
      checkMinor: 12_000,
    });
  });

  it("has nothing to explain without money", () => {
    expect(moneyFormula("bookings", { ...TOTALS, estimated_revenue_minor: null }, 12_000)).toEqual({ kind: "none" });
    expect(moneyFormula("bookings", TOTALS, null)).toEqual({ kind: "none" });
  });
});
