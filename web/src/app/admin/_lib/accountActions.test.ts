import { describe, expect, it } from "vitest";

import type { Schema } from "@/api/types";

import {
  ADMIN_REASON_MAX,
  availableActions,
  cleanReason,
  isDiscountDayValid,
  isReasonValid,
  isReferenceValid,
  lastDiscountDay,
  openInvoices,
  parseCreditMinor,
  parseDiscountPercent,
  parseTrialDays,
} from "./accountActions";

function invoice(id: string, status: Schema<"InvoiceStatus">, periodStart: number): Schema<"AdminInvoiceView"> {
  return {
    id,
    kind: "service_period",
    status,
    amount: { amount_minor: 15_000, currency_code: "GEL" },
    period_start: periodStart,
    period_end: periodStart + 1,
  };
}

describe("account action inputs", () => {
  it("asks for a reason of 8 to 300 characters, sent without blanks around it", () => {
    expect(isReasonValid("  short  ")).toBe(false);
    expect(isReasonValid("Slow onboarding: photos next week")).toBe(true);
    expect(isReasonValid("x".repeat(ADMIN_REASON_MAX + 1))).toBe(false);
    expect(cleanReason("  Agreed on the call \n")).toBe("Agreed on the call");
  });

  it("takes whole days from 1 to 60 and whole percents from 1 to 100", () => {
    expect(parseTrialDays("14")).toBe(14);
    expect(parseTrialDays(" 60 ")).toBe(60);
    expect(parseTrialDays("0")).toBeNull();
    expect(parseTrialDays("61")).toBeNull();
    expect(parseTrialDays("1.5")).toBeNull();
    expect(parseTrialDays("-3")).toBeNull();
    expect(parseDiscountPercent("100")).toBe(100);
    expect(parseDiscountPercent("101")).toBeNull();
    expect(parseDiscountPercent("")).toBeNull();
  });

  it("takes a discount's last day from today to three years ahead, real days only", () => {
    expect(isDiscountDayValid("2026-10-05", "2026-10-05")).toBe(true);
    expect(isDiscountDayValid("2026-10-04", "2026-10-05")).toBe(false);
    expect(isDiscountDayValid(lastDiscountDay("2026-10-05"), "2026-10-05")).toBe(true);
    expect(isDiscountDayValid("2030-01-01", "2026-10-05")).toBe(false);
    expect(isDiscountDayValid("2027-02-30", "2026-10-05")).toBe(false);
    expect(isDiscountDayValid("tomorrow", "2026-10-05")).toBe(false);
  });

  it("reads credit in the currency's own decimals, above zero and within the limit", () => {
    expect(parseCreditMinor("50", "GEL")).toBe(5_000);
    expect(parseCreditMinor("12,50", "GEL")).toBe(1_250);
    expect(parseCreditMinor("1500", "JPY")).toBe(1_500);
    expect(parseCreditMinor("0", "GEL")).toBeNull();
    expect(parseCreditMinor("1.234", "GEL")).toBeNull();
    expect(parseCreditMinor("abc", "GEL")).toBeNull();
    expect(parseCreditMinor("", "GEL")).toBeNull();
    expect(parseCreditMinor("100001", "GEL")).toBeNull();
  });

  it("needs a reference of up to 120 characters", () => {
    expect(isReferenceValid("   ")).toBe(false);
    expect(isReferenceValid("TBC-2026-10-05-0042")).toBe(true);
    expect(isReferenceValid("x".repeat(121))).toBe(false);
  });
});

describe("which actions the account takes", () => {
  const bills = [invoice("inv_paid", "paid", 1), invoice("inv_failed", "failed", 3), invoice("inv_issued", "issued", 2)];

  it("lists open bills oldest first", () => {
    expect(openInvoices(bills).map((bill) => bill.id)).toEqual(["inv_issued", "inv_failed"]);
  });

  it("offers nothing without a subscription", () => {
    expect(availableActions(null, bills, false)).toEqual([]);
  });

  it("offers a payment only for an open bill and a waiver only once", () => {
    expect(availableActions({ is_setup_fee_waived: false }, bills, true)).toEqual([
      "extend",
      "discount",
      "credit",
      "waive",
      "payment",
      "plan",
    ]);
    expect(availableActions({ is_setup_fee_waived: true }, [bills[0]!], true)).toEqual(["extend", "discount", "credit", "plan"]);
  });
});
