import { describe, expect, it } from "vitest";

import type { NicheSummaryView } from "@/api/types";

import { liveIntegrations } from "./paths";
import type { PlanQuote, QuotedMoney } from "./prices";
import { roiNiches, roiPlans, suggestedPlan } from "./roiOptions";

const money = (amount: number, currency: string, estimated = false): QuotedMoney => ({
  money: { amount_minor: amount, currency_code: currency },
  text: "",
  is_estimated: estimated,
});

function quote(key: PlanQuote["plan_key"], overrides: Partial<PlanQuote> = {}): PlanQuote {
  return {
    plan_key: key,
    name: key,
    description: "",
    included_voice_minutes: 0,
    included_dialogs: 1000,
    channels: [],
    is_voice_included: false,
    trial_days: 14,
    grace_period_days: 7,
    annual_discount_percent: 10,
    monthly_price: money(9900, "EUR"),
    annual_price: money(106920, "EUR"),
    setup_fee: money(15000, "EUR"),
    overage_price_per_minute: money(15, "EUR"),
    ...overrides,
  };
}

function niche(key: NicheSummaryView["key"], check: NicheSummaryView["typical_check"]): NicheSummaryView {
  return {
    key,
    name: key,
    description: "",
    booking_unit: "time_slot",
    recommended_plans: [],
    requires_legal_review: false,
    resource_kind: "table",
    resource_noun: "table",
    takes_bookings: true,
    typical_check: check,
    wave: "a",
  };
}

describe("value calculator options", () => {
  it("compares with the billed price: the price book's lari, never a conversion", () => {
    const plans = roiPlans([
      quote("chat", { local_monthly_price: money(29300, "GEL") }),
      quote("plus", { local_monthly_price: money(11235, "USD", true) }),
    ]);

    expect(plans[0]).toEqual({ key: "chat", name: "chat", monthly: 293, monthlyEuro: 99, currency: "GEL" });
    expect(plans[1]).toMatchObject({ monthly: 99, monthlyEuro: 99, currency: "EUR" });
  });

  it("takes a niche's typical check in euros only", () => {
    const niches = roiNiches([
      niche("restaurant", { amount_minor: 3500, currency_code: "EUR" }),
      niche("hotel", { amount_minor: 30000, currency_code: "GEL" }),
      niche("clinic", null),
    ]);

    expect(niches.map((entry) => entry.typicalCheckEuro)).toEqual([35, null, null]);
  });

  it("starts with the kind of business's recommended plan on offer, else the first", () => {
    const plans = roiPlans([quote("chat"), quote("voice_and_chat"), quote("plus")]);

    expect(suggestedPlan(plans, ["plus", "chat"])?.key).toBe("plus");
    expect(suggestedPlan(plans, ["unknown"])?.key).toBe("chat");
    expect(suggestedPlan([], ["chat"])).toBeNull();
  });

  it("names only the integrations the platform connects today", () => {
    expect(liveIntegrations(["Google Calendar", "Cloudbeds", "Poster"])).toEqual(["Google Calendar"]);
    expect(liveIntegrations(undefined)).toEqual([]);
  });
});
