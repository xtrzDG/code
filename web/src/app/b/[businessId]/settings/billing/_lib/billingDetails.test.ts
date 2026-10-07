import { describe, expect, it } from "vitest";

import {
  billingCountryCodes,
  billingDetailsErrors,
  billingDetailsForm,
  billingProfileBody,
  canDownloadInvoice,
  fileNameFromDisposition,
  formatTaxRate,
  hasDetailsErrors,
  isSameBillingDetails,
  type BillingDetailsForm,
  type BillingProfileView,
} from "./billingDetails";

const view = (overrides: Partial<BillingProfileView> = {}): BillingProfileView => ({
  business_id: "business_1",
  is_saved: true,
  legal_name: "Mtsvane Ezo LLC",
  tax_id: "405123456",
  address: "12 Rustaveli Ave\n0108 Tbilisi",
  billing_email: "accounts@mtsvane-ezo.ge",
  country_code: "GE",
  tax_treatment: "not_registered",
  tax_rate_basis_points: 0,
  ...overrides,
});

const form = (overrides: Partial<BillingDetailsForm> = {}): BillingDetailsForm => ({
  ...billingDetailsForm(view()),
  ...overrides,
});

describe("billing details form", () => {
  it("starts from the stored details, blanks for what is missing", () => {
    expect(billingDetailsForm(view({ tax_id: null, address: null, billing_email: null }))).toEqual({
      legalName: "Mtsvane Ezo LLC",
      taxId: "",
      address: "",
      billingEmail: "",
      countryCode: "GE",
    });
  });

  it("sends trimmed values, blanks as null and the e-mail in lower case", () => {
    expect(
      billingProfileBody(
        form({ legalName: "  Mtsvane Ezo LLC ", taxId: " ", address: "Line 1\r\nLine 2 ", billingEmail: " Accounts@Ezo.GE " }),
      ),
    ).toEqual({
      legal_name: "Mtsvane Ezo LLC",
      tax_id: null,
      address: "Line 1\nLine 2",
      billing_email: "accounts@ezo.ge",
      country_code: "GE",
    });
  });

  it("names each field the API would refuse", () => {
    const errors = billingDetailsErrors(form({ legalName: " ", taxId: "-12", address: "ab", billingEmail: "accounts" }));
    expect(errors).toEqual({
      legalName: "billing.details.errors.legalName",
      taxId: "billing.details.errors.taxId",
      address: "billing.details.errors.address",
      billingEmail: "billing.details.errors.billingEmail",
    });
    expect(hasDetailsErrors(errors)).toBe(true);
    expect(hasDetailsErrors(billingDetailsErrors(form({ taxId: "DE 123/456.78-9", address: "", billingEmail: "" })))).toBe(false);
  });

  it("has nothing to save when the form says what is stored, always something before the first save", () => {
    expect(isSameBillingDetails(form(), view())).toBe(true);
    expect(isSameBillingDetails(form({ countryCode: "DE" }), view())).toBe(false);
    expect(isSameBillingDetails(form(), view({ is_saved: false }))).toBe(false);
  });
});

describe("billing countries", () => {
  it("lists real countries by name and leaves out regions and pseudo-codes", () => {
    const codes = billingCountryCodes((code) => code, "GE", "en");
    expect(codes).toContain("GE");
    expect(codes).toContain("DE");
    for (const code of ["EU", "EZ", "UN", "ZZ", "QO", "XA", "AQ", "001"]) {
      expect(codes).not.toContain(code);
    }
    expect([...codes].sort()).toEqual(codes);
  });

  it("keeps the stored country listed even when the table lacks it", () => {
    expect(billingCountryCodes((code) => code, "XK", "en")).toContain("XK");
  });
});

describe("billing documents", () => {
  it("reads the file name from Content-Disposition, the encoded form first", () => {
    expect(
      fileNameFromDisposition(`attachment; filename="invoice-AW-2026-000042.pdf"; filename*=UTF-8''invoice-AW-2026-000042.pdf`, "x.pdf"),
    ).toBe("invoice-AW-2026-000042.pdf");
    expect(fileNameFromDisposition('attachment; filename="receipt-AW-2026-000007.pdf"', "x.pdf")).toBe("receipt-AW-2026-000007.pdf");
    expect(fileNameFromDisposition("attachment; filename*=UTF-8''..%2F..%2Fetc%2Fpasswd", "x.pdf")).toBe("etc-passwd");
    expect(fileNameFromDisposition("attachment; filename*=UTF-8''%E0%A4%A", "x.pdf")).toBe("x.pdf");
    expect(fileNameFromDisposition(null, "invoice.pdf")).toBe("invoice.pdf");
  });

  it("offers the invoice PDF unless the invoice was voided before it got a number", () => {
    expect(canDownloadInvoice({ status: "issued", number: null })).toBe(true);
    expect(canDownloadInvoice({ status: "void", number: "AW-2026-000003" })).toBe(true);
    expect(canDownloadInvoice({ status: "void", number: null })).toBe(false);
  });

  it("writes the VAT rate in the reader's number format", () => {
    expect(formatTaxRate(1800, "en")).toBe("18%");
    expect(formatTaxRate(1850, "en")).toBe("18.5%");
    expect(formatTaxRate(1800, "ka")).toBe("18%");
  });
});
