import { describe, expect, it } from "vitest";

import {
  FIRST_DAY_MS,
  periodHeading,
  showsReturnMultiple,
  trialTerms,
  usesOnlyOwnPrices,
  valueStage,
  type ValueModel,
  type ValueTotals,
} from "./valueModel";

const QUIET: ValueTotals = {
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
  estimated_revenue_minor: 0,
  valued_booking_count: 0,
};
const BUSY: ValueTotals = { ...QUIET, conversation_count: 16, assistant_booking_count: 16, estimated_revenue_minor: 192_000 };

/** 2026-10-05 10:40 in Tbilisi, as the API's microseconds. */
const LAUNCHED_US = Date.UTC(2026, 9, 5, 6, 40) * 1000;
const LAUNCHED_MS = LAUNCHED_US / 1000;

function model(overrides: Partial<ValueModel> = {}): ValueModel {
  return {
    business_id: "biz_1",
    currency_code: "GEL",
    timezone: "Asia/Tbilisi",
    date_from: "2026-09-06",
    date_to: "2026-10-05",
    previous_date_from: "2026-08-07",
    previous_date_to: "2026-09-05",
    value_basis: "bookings",
    average_check_minor: 12_000,
    average_check_source: "niche_default",
    typical_check_minor: 12_000,
    seconds_per_reply: 60,
    seconds_per_call: 180,
    current: BUSY,
    previous: BUSY,
    plan_cost_minor: 51_000,
    return_multiple: 3.8,
    is_trial: false,
    trial_ends_at: null,
    plan_cost_after_trial_minor: null,
    is_since_launch: false,
    went_live_at: null,
    ...overrides,
  };
}

describe("the day-0 readiness of the owner's hero", () => {
  it("is ready during the first day after the launch, even with a few conversations", () => {
    const fresh = model({ went_live_at: LAUNCHED_US, is_since_launch: true, date_from: "2026-10-05" });

    expect(valueStage(fresh, LAUNCHED_MS + 60_000)).toBe("ready");
    expect(valueStage(fresh, LAUNCHED_MS + FIRST_DAY_MS - 1)).toBe("ready");
    expect(valueStage(fresh, LAUNCHED_MS + FIRST_DAY_MS)).toBe("working");
  });

  it("stays ready while no conversation came since the launch", () => {
    const quiet = model({ went_live_at: LAUNCHED_US, is_since_launch: true, current: QUIET });
    const later = LAUNCHED_MS + 3 * FIRST_DAY_MS;

    expect(valueStage(quiet, later)).toBe("ready");
    expect(valueStage({ ...quiet, current: BUSY }, later)).toBe("working");
  });

  it("never greets a business live for long, however quiet its period", () => {
    const quietMonth = model({ went_live_at: LAUNCHED_US - 90 * FIRST_DAY_MS * 1000, current: QUIET });

    expect(valueStage(quietMonth, LAUNCHED_MS)).toBe("working");
    // Live before milestones were kept: no launch moment, the period was not cut.
    expect(valueStage(model({ current: QUIET }), LAUNCHED_MS)).toBe("working");
  });

  it("reads a period cut at the launch as 'since' its first day", () => {
    expect(periodHeading({ date_from: "2026-10-05", date_to: "2026-10-05", is_since_launch: true })).toEqual({
      kind: "since",
      from: "2026-10-05",
    });
    expect(periodHeading(model())).toEqual({ kind: "range", from: "2026-09-06", to: "2026-10-05" });
  });
});

describe("the return against the plan's price", () => {
  it("shows for money above zero against a priced plan", () => {
    expect(showsReturnMultiple(model())).toBe(true);
  });

  it("never shows during the free trial, for no money, or a multiple of nothing", () => {
    expect(showsReturnMultiple(model({ is_trial: true }))).toBe(false);
    expect(showsReturnMultiple(model({ current: { ...BUSY, estimated_revenue_minor: 0 } }))).toBe(false);
    expect(showsReturnMultiple(model({ return_multiple: 0 }))).toBe(false);
    expect(showsReturnMultiple(model({ return_multiple: null, plan_cost_minor: null }))).toBe(false);
  });

  it("says what the plan costs after the trial instead", () => {
    const trial = model({
      is_trial: true,
      trial_ends_at: LAUNCHED_US + 14 * FIRST_DAY_MS * 1000,
      plan_cost_after_trial_minor: 51_000,
      plan_cost_minor: null,
      return_multiple: null,
    });

    expect(trialTerms(trial)).toEqual({ endsAt: LAUNCHED_US + 14 * FIRST_DAY_MS * 1000, priceMinor: 51_000 });
    expect(trialTerms(model({ is_trial: true }))).toEqual({ endsAt: null, priceMinor: null });
    expect(trialTerms(model())).toBeNull();
  });
});

describe("the average check line", () => {
  it("hides when every counted booking had its own price", () => {
    expect(usesOnlyOwnPrices({ revenue_source: "booked_values" })).toBe(true);
    expect(usesOnlyOwnPrices({ revenue_source: "mixed" })).toBe(false);
    expect(usesOnlyOwnPrices({ revenue_source: null })).toBe(false);
  });
});
