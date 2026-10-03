import { describe, expect, it } from "vitest";

import { acceptLanguageTags, landingPrices, moneyText, pickLandingCountry, sharedTrialDays, type PlanQuote } from "./landing";

const money = (amount: number, currency: string, text: string, estimated = false) => ({
  money: { amount_minor: amount, currency_code: currency },
  text,
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
    annual_discount_percent: 15,
    monthly_price: money(9900, "EUR", "€99.00"),
    annual_price: money(100980, "EUR", "€1,009.80"),
    setup_fee: money(15000, "EUR", "€150.00"),
    overage_price_per_minute: money(15, "EUR", "€0.15"),
    ...overrides,
  };
}

describe("landing country", () => {
  const available = ["GE", "DE", "TR", "US"];

  it("prefers the picked country, then the proxy's, then the browser languages", () => {
    expect(pickLandingCountry({ requested: "de", available })).toBe("DE");
    expect(pickLandingCountry({ requested: "XX", geoCountry: "TR", available })).toBe("TR");
    expect(pickLandingCountry({ acceptLanguage: "en-US,en;q=0.9", available })).toBe("US");
    expect(pickLandingCountry({ acceptLanguage: "ka", available })).toBe("GE");
  });

  it("falls back to Georgia, then the first available country", () => {
    expect(pickLandingCountry({ acceptLanguage: "fr-FR", available })).toBe("GE");
    expect(pickLandingCountry({ available: ["DE"] })).toBe("DE");
    expect(pickLandingCountry({ available: [] })).toBeNull();
  });

  it("reads Accept-Language best first", () => {
    expect(acceptLanguageTags("de;q=0.5, ru-RU, ka;q=0.8, *")).toEqual(["ru-RU", "ka", "de"]);
    expect(acceptLanguageTags(null)).toEqual([]);
  });
});

describe("landing prices", () => {
  it("shows the local price with the plan's euro price beside it", () => {
    const prices = landingPrices(quote({ local_monthly_price: money(29300, "GEL", "293,00 ₾") }));
    expect(prices.monthly.text).toBe("293,00 ₾");
    expect(prices.plan?.text).toBe("€99.00");
  });

  it("shows only the plan price when the country pays in it", () => {
    const prices = landingPrices(quote());
    expect(prices.monthly.text).toBe("€99.00");
    expect(prices.plan).toBeNull();
  });

  it("marks converted prices", () => {
    expect(moneyText(money(100, "TRY", "₺1.00", true))).toBe("≈ ₺1.00");
  });

  it("names the trial only when every plan has the same one", () => {
    expect(sharedTrialDays([quote(), quote({ plan_key: "plus" })])).toBe(14);
    expect(sharedTrialDays([quote(), quote({ trial_days: 7 })])).toBeNull();
    expect(sharedTrialDays([quote({ trial_days: 0 })])).toBeNull();
    expect(sharedTrialDays([])).toBeNull();
  });
});
