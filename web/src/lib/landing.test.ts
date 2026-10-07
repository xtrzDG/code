import { describe, expect, it } from "vitest";

import { acceptLanguageTags, pickLandingCountry, sharedTrialDays, type PlanQuote } from "./landing";

const money = (amount: number, currency: string) => ({
  money: { amount_minor: amount, currency_code: currency },
  text: "",
  is_estimated: false,
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
    monthly_price: money(9900, "EUR"),
    annual_price: money(100980, "EUR"),
    setup_fee: money(15000, "EUR"),
    overage_price_per_minute: money(15, "EUR"),
    ...overrides,
  };
}

describe("landing country", () => {
  const available = ["GE", "DE", "TR", "US", "RU"];
  const priced = ["GE", "DE"];

  it("always shows the country the visitor picked", () => {
    expect(pickLandingCountry({ requested: "us", available, priced })).toBe("US");
    expect(pickLandingCountry({ requested: "XX", geoCountry: "DE", available, priced })).toBe("DE");
  });

  it("guesses only countries with a price book", () => {
    expect(pickLandingCountry({ geoCountry: "US", acceptLanguage: "en-US", available, priced })).toBe("GE");
    expect(pickLandingCountry({ acceptLanguage: "ru-RU,ru;q=0.9", available, priced })).toBe("GE");
    expect(pickLandingCountry({ acceptLanguage: "de-DE", available, priced })).toBe("DE");
    expect(pickLandingCountry({ acceptLanguage: "ka", available, priced })).toBe("GE");
  });

  it("treats every country as priced when the catalog does not say", () => {
    expect(pickLandingCountry({ acceptLanguage: "en-US,en;q=0.9", available })).toBe("US");
    expect(pickLandingCountry({ geoCountry: "TR", available })).toBe("TR");
  });

  it("falls back to Georgia, then the first country", () => {
    expect(pickLandingCountry({ acceptLanguage: "fr-FR", available, priced })).toBe("GE");
    expect(pickLandingCountry({ available: ["DE"], priced: [] })).toBe("DE");
    expect(pickLandingCountry({ available: [] })).toBeNull();
  });

  it("reads Accept-Language best first", () => {
    expect(acceptLanguageTags("de;q=0.5, ru-RU, ka;q=0.8, *")).toEqual(["ru-RU", "ka", "de"]);
    expect(acceptLanguageTags("en;q=abc")).toEqual([]);
    expect(acceptLanguageTags(null)).toEqual([]);
  });
});

describe("shared trial", () => {
  it("names the trial only when every plan has the same one", () => {
    expect(sharedTrialDays([quote(), quote({ plan_key: "plus" })])).toBe(14);
    expect(sharedTrialDays([quote(), quote({ trial_days: 7 })])).toBeNull();
    expect(sharedTrialDays([quote({ trial_days: 0 })])).toBeNull();
    expect(sharedTrialDays([])).toBeNull();
  });
});
