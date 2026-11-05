import { describe, expect, it } from "vitest";

import { createPartnerBody, isReferralCode, partnerFormProblem, payoutMonths, type PartnerForm } from "./partnerForms";

const FORM: PartnerForm = { name: " Tbilisi Digital ", by: "phone", contact: "+995 599 00 01 11", ratePercent: "20", code: "agency-tbilisi" };

describe("the partner form", () => {
  it("names its first problem", () => {
    expect(partnerFormProblem(FORM)).toBeNull();
    expect(partnerFormProblem({ ...FORM, name: " " })).toBe("nameRequired");
    expect(partnerFormProblem({ ...FORM, contact: "" })).toBe("contactRequired");
    expect(partnerFormProblem({ ...FORM, ratePercent: "60" })).toBe("rateInvalid");
    expect(partnerFormProblem({ ...FORM, code: "agency tbilisi" })).toBe("codeInvalid");
  });

  it("sends the phone or the e-mail and the rate in basis points", () => {
    expect(createPartnerBody(FORM)).toEqual({
      name: "Tbilisi Digital",
      phone_number: "+995 599 00 01 11",
      commission_rate_basis_points: 2000,
      code: "agency-tbilisi",
    });
    expect(createPartnerBody({ ...FORM, by: "email", contact: "p@example.com", ratePercent: "12,5" })).toMatchObject({
      email: "p@example.com",
      commission_rate_basis_points: 1250,
    });
    expect(isReferralCode("Agency_2.0")).toBe(true);
  });
});

describe("payout months", () => {
  it("are this UTC month and the eleven before", () => {
    const months = payoutMonths(new Date("2026-02-10T12:00:00Z"));

    expect(months).toHaveLength(12);
    expect(months.slice(0, 3)).toEqual(["2026-02", "2026-01", "2025-12"]);
  });
});
