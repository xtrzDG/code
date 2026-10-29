import { describe, expect, it } from "vitest";

import type { PlanQuote, QuotedMoney, SubscriptionView } from "./billing";
import { setupOptionFee, setupState } from "./setupOptions";

const money = (amount_minor: number, currency_code = "GEL", is_estimated = false): QuotedMoney => ({
  money: { amount_minor, currency_code },
  text: "",
  is_estimated,
});

const quote = (overrides: Partial<PlanQuote> = {}): PlanQuote =>
  ({
    plan_key: "chat",
    setup_fee: money(15_000, "EUR"),
    local_setup_fee: money(44_300, "GEL", true),
    setup_options: [
      { option: "self_serve", fee: money(0, "EUR"), local_fee: null },
      { option: "done_for_you", fee: money(15_000, "EUR"), local_fee: money(44_300, "GEL", true) },
    ],
    ...overrides,
  }) as PlanQuote;

describe("setup option fees", () => {
  it("charges nothing to set the assistant up yourself", () => {
    expect(setupOptionFee(quote(), "self_serve", "monthly")).toBeNull();
  });

  it("charges the team's setup once with a monthly plan, in the local currency when known", () => {
    expect(setupOptionFee(quote(), "done_for_you", "monthly")).toEqual(money(44_300, "GEL", true));
    const noLocal = quote({
      setup_options: [{ option: "done_for_you", fee: money(15_000, "EUR"), local_fee: null }],
    });
    expect(setupOptionFee(noLocal, "done_for_you", "monthly")?.money.currency_code).toBe("EUR");
  });

  it("includes the team's setup in a yearly payment", () => {
    expect(setupOptionFee(quote(), "done_for_you", "annual")).toBeNull();
  });

  it("falls back to the plan's setup fee for a quote without options", () => {
    expect(setupOptionFee(quote({ setup_options: [] }), "done_for_you", "monthly")).toEqual(money(44_300, "GEL", true));
    expect(setupOptionFee(quote({ setup_options: [] }), "self_serve", "monthly")).toBeNull();
  });
});

describe("setup state", () => {
  const subscription = (overrides: Partial<SubscriptionView>) => ({ setup_option: null, ...overrides }) as SubscriptionView;

  it("tells the team's setup with the request date", () => {
    expect(setupState(subscription({ setup_option: "done_for_you", onboarding_requested_at: 5 }))).toEqual({
      kind: "done_for_you",
      requestedAt: 5,
    });
  });

  it("tells a self-serve setup (a trial or an older subscription pays no fee either), and nothing before a subscription", () => {
    expect(setupState(subscription({ setup_option: "self_serve" }))).toEqual({ kind: "self_serve" });
    expect(setupState(subscription({}))).toEqual({ kind: "self_serve" });
    expect(setupState(null)).toBeNull();
  });
});
