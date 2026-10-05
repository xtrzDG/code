import { describe, expect, it } from "vitest";

import {
  approximateLabel,
  hasConversion,
  moneyLabel,
  planPriceLines,
  rateSourceKey,
  type PlanQuote,
  type QuotedMoney,
} from "./prices";

/** Intl puts a no-break space between "GEL" and the amount. */
const plain = (text: string) => text.replace(/\u00a0/g, " ");

const money = (amount: number, currency: string, estimated = false): QuotedMoney => ({
  money: { amount_minor: amount, currency_code: currency },
  text: "",
  is_estimated: estimated,
});

function quote(overrides: Partial<PlanQuote> = {}): PlanQuote {
  return {
    plan_key: "chat",
    name: "Chat",
    description: "",
    included_voice_minutes: 0,
    included_dialogs: 1000,
    channels: ["whatsapp"],
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

describe("money labels", () => {
  it("drops the decimals of whole amounts and keeps them otherwise", () => {
    expect(moneyLabel({ amount_minor: 9900, currency_code: "EUR" }, "en")).toBe("€99");
    expect(moneyLabel({ amount_minor: 15, currency_code: "EUR" }, "en")).toBe("€0.15");
    expect(plain(moneyLabel({ amount_minor: 29300, currency_code: "GEL" }, "en"))).toBe("GEL 293");
  });

  it("rounds conversions to whole units and marks them", () => {
    expect(approximateLabel({ amount_minor: 11235, currency_code: "USD" }, "en")).toBe("≈ $112");
    expect(approximateLabel({ amount_minor: 114597, currency_code: "USD" }, "en")).toBe("≈ $1,146");
    expect(approximateLabel({ amount_minor: 11250, currency_code: "USD" }, "en")).toBe("≈ $113");
  });
});

describe("plan price lines", () => {
  it("shows euros first and the conversion second where there is no price book", () => {
    const lines = planPriceLines(
      quote({
        local_monthly_price: money(11235, "USD", true),
        local_annual_price: money(114597, "USD", true),
        local_setup_fee: money(17022, "USD", true),
        local_overage_price_per_minute: money(17, "USD", true),
      }),
      "en",
    );

    expect(lines).toEqual({
      monthly: "€99",
      annual: "€1,069.20",
      setupFee: "€150",
      overage: "€0.15",
      currency: "EUR",
      secondary: { kind: "converted", text: "≈ $112" },
    });
    expect(Object.values(lines).join(" ")).not.toMatch(/\$1,145\.97|\$112\.35/);
  });

  it("shows the price book's own amount first and the euros beside it", () => {
    const lines = planPriceLines(
      quote({
        local_monthly_price: money(29300, "GEL"),
        local_annual_price: money(316440, "GEL"),
        local_setup_fee: money(44300, "GEL"),
        local_overage_price_per_minute: money(44, "GEL"),
      }),
      "en",
    );

    expect(plain(lines.monthly)).toBe("GEL 293");
    expect(lines.currency).toBe("GEL");
    expect(lines.secondary).toEqual({ kind: "euros", text: "€99" });
  });

  it("shows only euros in the euro area or without a known rate", () => {
    expect(planPriceLines(quote({ local_monthly_price: money(9900, "EUR") }), "en").secondary).toBeNull();
    expect(planPriceLines(quote(), "en")).toMatchObject({ monthly: "€99", secondary: null });
  });

  it("says when any plan shows a conversion", () => {
    expect(hasConversion([quote(), quote({ local_monthly_price: money(11235, "USD", true) })])).toBe(true);
    expect(hasConversion([quote({ local_monthly_price: money(29300, "GEL") })])).toBe(false);
  });
});

describe("rate source", () => {
  it("names a central bank's rate, several banks' rates or the planning rate", () => {
    expect(rateSourceKey({ sources: ["nbg"] })).toBe("nbg");
    expect(rateSourceKey({ sources: ["ecb"] })).toBe("ecb");
    expect(rateSourceKey({ sources: ["ecb", "nbg"] })).toBe("official");
    expect(rateSourceKey({ sources: ["planning"] })).toBe("planning");
    expect(rateSourceKey({ sources: ["ecb", "planning"] })).toBe("planning");
    expect(rateSourceKey({ sources: [] })).toBe("planning");
    expect(rateSourceKey({})).toBe("planning");
  });
});
