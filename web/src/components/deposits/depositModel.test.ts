import { describe, expect, it } from "vitest";

import type { BookingView } from "@/components/insights/types";

import {
  bookingAfterPaid,
  canMarkPaid,
  hasDepositActivity,
  noShowLine,
  pagesForRule,
  policyForm,
  policyFormErrors,
  policyOf,
  policyRequestBody,
  policySummary,
  type DepositPolicyView,
  type DepositReport,
  type DepositSettingsView,
  type PaymentLinkView,
} from "./depositModel";

const TEMPLATE: PaymentLinkView = {
  id: "link_template",
  label: "Flitt",
  kind: "template",
  host: "pay.example.com",
  preview: "https://pay.example.com/?sum={amount}",
  is_sealed: false,
};
const STATIC: PaymentLinkView = { ...TEMPLATE, id: "link_static", label: "Stripe", kind: "static" };

function settings(policies: DepositPolicyView[]): DepositSettingsView {
  return {
    currency_code: "GEL",
    currency_digits: 2,
    is_enabled: true,
    hold_minutes: 60,
    refund_cutoff_hours: 24,
    default_payment_link_id: TEMPLATE.id,
    payment_links: [TEMPLATE, STATIC],
    policies,
  };
}

const PER_GUEST: DepositPolicyView = {
  target: "resource",
  resource_id: "res_1",
  rule: "per_guest",
  amount_minor: 2000,
  currency_code: "GEL",
  min_party_size: 6,
};

function booking(overrides: Partial<BookingView> = {}): BookingView {
  return {
    business_id: "biz_1",
    contact_id: "contact_1",
    created_at: 0,
    date: "2026-10-08",
    end_date: "2026-10-08",
    id: "booking_1",
    is_sandbox: false,
    party_size: 6,
    resource_id: "res_1",
    resource_name: "Terrace",
    source_channel: "web_chat",
    status: "pending_deposit",
    timezone: "Asia/Tbilisi",
    deposit: { request_id: "dep_1", amount_minor: 12000, currency_code: "GEL", status: "awaiting", hold_expires_at: 1 },
    ...overrides,
  };
}

describe("deposit policies", () => {
  it("finds the policy of a resource, a service and the banquets", () => {
    const service: DepositPolicyView = { target: "service", service_item_id: "svc_1", rule: "fixed", amount_minor: 500, currency_code: "GEL" };
    const banquet: DepositPolicyView = { target: "banquet", rule: "percent_of_value", percent: 30, currency_code: "GEL" };
    const view = settings([PER_GUEST, service, banquet]);
    expect(policyOf(view, { target: "resource", resourceId: "res_1" })).toBe(PER_GUEST);
    expect(policyOf(view, { target: "resource", resourceId: "res_2" })).toBeNull();
    expect(policyOf(view, { target: "service", serviceItemId: "svc_1" })).toBe(service);
    expect(policyOf(view, { target: "banquet" })).toBe(banquet);
    expect(policyOf(undefined, { target: "banquet" })).toBeNull();
  });

  it("shows a stored amount in major units and sends it back in minor units", () => {
    const form = policyForm(PER_GUEST);
    expect(form).toEqual({ rule: "per_guest", amount: "20", percent: "", minPartySize: "6", paymentLinkId: "" });
    expect(policyRequestBody({ ...form, amount: "12,50" }, { target: "resource", resourceId: "res_1" }, "GEL")).toEqual({
      target: "resource",
      resource_id: "res_1",
      policy: { rule: "per_guest", amount_minor: 1250, percent: null, min_party_size: 6, payment_link_id: null },
    });
  });

  it("sends a percent without an amount, and no deposit as a null policy", () => {
    const percent = { rule: "percent_of_value" as const, amount: "99", percent: "30", minPartySize: "", paymentLinkId: "" };
    expect(policyRequestBody(percent, { target: "banquet" }, "GEL")).toEqual({
      target: "banquet",
      policy: { rule: "percent_of_value", amount_minor: null, percent: 30, min_party_size: null, payment_link_id: null },
    });
    expect(policyRequestBody({ ...percent, rule: "none" }, { target: "service", serviceItemId: "svc_1" }, "GEL")).toEqual({
      target: "service",
      service_item_id: "svc_1",
      policy: null,
    });
  });

  it("names a page only when the rule fits it", () => {
    expect(pagesForRule([TEMPLATE, STATIC], "fixed")).toEqual([TEMPLATE, STATIC]);
    expect(pagesForRule([TEMPLATE, STATIC], "per_guest")).toEqual([TEMPLATE]);
    const fixed = { rule: "fixed" as const, amount: "50", percent: "", minPartySize: "", paymentLinkId: STATIC.id };
    const target = { target: "resource" as const, resourceId: "res_1" };
    expect(policyRequestBody(fixed, target, "GEL", [TEMPLATE, STATIC]).policy?.payment_link_id).toBe(STATIC.id);
    // A static page left chosen after switching to a per-guest deposit is not sent.
    expect(policyRequestBody({ ...fixed, rule: "per_guest" }, target, "GEL", [TEMPLATE, STATIC]).policy?.payment_link_id).toBeNull();
  });

  it("checks the amount, the percent and the party size", () => {
    const base = { rule: "fixed" as const, amount: "", percent: "", minPartySize: "", paymentLinkId: "" };
    expect(policyFormErrors({ ...base, rule: "none" }, "GEL")).toEqual({});
    expect(policyFormErrors(base, "GEL")).toEqual({ amount: "validation.number" });
    expect(policyFormErrors({ ...base, amount: "0" }, "GEL")).toEqual({ amount: "validation.number" });
    expect(policyFormErrors({ ...base, amount: "1.0005" }, "GEL")).toEqual({ amount: "knowledge.form.priceTooPrecise" });
    expect(policyFormErrors({ ...base, amount: "1.005" }, "GEL")).toEqual({ amount: "knowledge.form.priceAmbiguous" });
    expect(policyFormErrors({ ...base, amount: "20", minPartySize: "0" }, "GEL")).toEqual({ minPartySize: "deposits.policy.errors.minParty" });
    expect(policyFormErrors({ ...base, amount: "20", minPartySize: "2.5" }, "GEL")).toEqual({ minPartySize: "deposits.policy.errors.minParty" });
    for (const percent of ["0", "101", "", "12.5"]) {
      expect(policyFormErrors({ ...base, rule: "percent_of_value", percent }, "GEL")).toEqual({ percent: "deposits.policy.errors.percent" });
    }
    expect(policyFormErrors({ ...base, rule: "percent_of_value", percent: "100" }, "GEL")).toEqual({});
  });

  it("sums a policy up in one line", () => {
    expect(policySummary(PER_GUEST)).toEqual({ key: "deposits.policy.summary.per_guest", amountMinor: 2000, percent: null, fromGuests: 6 });
    expect(policySummary({ ...PER_GUEST, rule: "percent_of_value", amount_minor: null, percent: 25, min_party_size: null })).toEqual({
      key: "deposits.policy.summary.percent_of_value",
      amountMinor: null,
      percent: 25,
      fromGuests: null,
    });
  });
});

describe("a booking's deposit", () => {
  it("is marked paid only while it waits", () => {
    expect(canMarkPaid(booking().deposit)).toBe(true);
    expect(canMarkPaid({ ...booking().deposit!, status: "expired" })).toBe(false);
    expect(canMarkPaid(null)).toBe(false);
  });

  it("confirms a booking held for its deposit and leaves any other status", () => {
    const paid = bookingAfterPaid(booking());
    expect(paid.status).toBe("confirmed");
    expect(paid.deposit?.status).toBe("paid");
    expect(bookingAfterPaid(booking({ status: "confirmed" })).status).toBe("confirmed");
    expect(bookingAfterPaid(booking({ status: "cancelled" })).status).toBe("cancelled");
    expect(bookingAfterPaid(booking({ deposit: null })).status).toBe("pending_deposit");
  });
});

describe("the deposit report", () => {
  it("says there is not enough data below the sample instead of a share", () => {
    expect(noShowLine({ finished_count: 4, no_show_count: 2, has_enough_data: false, no_show_percent: null }, 10)).toEqual({
      kind: "notEnough",
      finished: 4,
      min: 10,
    });
    expect(noShowLine({ finished_count: 20, no_show_count: 3, has_enough_data: true, no_show_percent: 15 }, 10)).toEqual({
      kind: "rate",
      percent: 15,
      noShows: 3,
      finished: 20,
    });
  });

  it("shows figures while deposits are on or were asked in the window", () => {
    const report = { is_enabled: false, requested_count: 0 } as DepositReport;
    expect(hasDepositActivity(report)).toBe(false);
    expect(hasDepositActivity({ ...report, requested_count: 1 })).toBe(true);
    expect(hasDepositActivity({ ...report, is_enabled: true })).toBe(true);
  });
});
