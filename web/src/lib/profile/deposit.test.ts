import { describe, expect, it } from "vitest";

import { depositText, withDeposit } from "./deposit";

const rules = { max_party_size: 4, slot_minutes: 60, min_notice_minutes: 0, deposit_minor: 5000, deposit_currency_code: "GEL" };

describe("booking deposit", () => {
  it("shows the stored deposit as a price", () => {
    expect(depositText(rules, "GEL")).toBe("50");
    expect(depositText({ deposit_minor: 1250 }, "EUR")).toBe("12.5");
    expect(depositText({ deposit_minor: null }, "GEL")).toBe("");
    expect(depositText(null, "GEL")).toBe("");
  });

  it("stores what is typed in minor units, and nothing for an empty field or zero", () => {
    expect(withDeposit(rules, "12,50", "GEL")).toEqual({ ok: true, rules: { ...rules, deposit_minor: 1250, deposit_currency_code: "GEL" } });
    expect(withDeposit(rules, " ", "GEL")).toEqual({ ok: true, rules: { ...rules, deposit_minor: null, deposit_currency_code: null } });
    expect(withDeposit(rules, "0", "GEL")).toEqual({ ok: true, rules: { ...rules, deposit_minor: null, deposit_currency_code: null } });
  });

  it("refuses what is not a price of the currency", () => {
    expect(withDeposit(rules, "ten", "GEL")).toEqual({ ok: false, problem: "validation.number" });
    expect(withDeposit(rules, "1.234", "GEL")).toEqual({ ok: false, problem: "knowledge.form.priceAmbiguous" });
    expect(withDeposit(rules, "10.5", "JPY")).toEqual({ ok: false, problem: "knowledge.form.priceTooPrecise" });
  });
});
