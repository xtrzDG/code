import { describe, expect, it } from "vitest";

import { budgetTone, isSpendSpike, microUsdToCents, spendingProviders, type PlatformSpend } from "./spend";

const SPEND: PlatformSpend = {
  day: "2026-10-05",
  total_micro_usd: 13_000_000,
  week_daily_mean_micro_usd: 4_000_000,
  providers: [
    { provider: "voice", spend_micro_usd: 3_000_000 },
    { provider: "language_model", spend_micro_usd: 10_000_000 },
    { provider: "telephony", spend_micro_usd: 0 },
  ],
  braked_businesses: [],
};

describe("the spend tile", () => {
  it("shows micro-USD as cents, rounded", () => {
    expect(microUsdToCents(13_000_000)).toBe(1300);
    expect(microUsdToCents(4_999)).toBe(0);
    expect(microUsdToCents(5_000)).toBe(1);
  });

  it("flags a spike as the alert does: over 3 times the mean, from $5", () => {
    expect(isSpendSpike(SPEND)).toBe(true);
    expect(isSpendSpike({ total_micro_usd: 12_000_000, week_daily_mean_micro_usd: 4_000_000 })).toBe(false);
    expect(isSpendSpike({ total_micro_usd: 4_000_000, week_daily_mean_micro_usd: 0 })).toBe(false);
    expect(isSpendSpike({ total_micro_usd: 5_000_000, week_daily_mean_micro_usd: 0 })).toBe(true);
  });

  it("colours the budget by use", () => {
    expect(budgetTone(40)).toBe("info");
    expect(budgetTone(80)).toBe("warning");
    expect(budgetTone(130)).toBe("danger");
  });

  it("lists the providers with spend, largest first", () => {
    expect(spendingProviders(SPEND).map((provider) => provider.provider)).toEqual(["language_model", "voice"]);
  });
});
