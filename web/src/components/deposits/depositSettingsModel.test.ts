import { describe, expect, it } from "vitest";

import type { DepositSettingsView } from "./depositModel";
import {
  defaultPageBody,
  depositSettingsBody,
  depositSettingsErrors,
  depositSettingsForm,
  paymentLinkBody,
  paymentLinkErrors,
} from "./depositSettingsModel";

const STORED: DepositSettingsView = {
  currency_code: "GEL",
  currency_digits: 2,
  is_enabled: false,
  hold_minutes: 60,
  refund_cutoff_hours: 24,
  default_payment_link_id: "link_1",
  payment_links: [],
  policies: [],
};

describe("deposit choices", () => {
  it("saves only what changed and keeps the default page", () => {
    const form = depositSettingsForm(STORED);
    expect(form).toEqual({ isEnabled: false, holdMinutes: "60", refundHours: "24" });
    expect(depositSettingsBody(form, STORED)).toBeNull();
    expect(depositSettingsBody({ ...form, isEnabled: true, holdMinutes: " 30 " }, STORED)).toEqual({
      is_enabled: true,
      hold_minutes: 30,
      refund_cutoff_hours: 24,
      default_payment_link_id: null,
    });
  });

  it("holds 15 minutes to a day and refunds up to 30 days ahead", () => {
    const form = depositSettingsForm(STORED);
    expect(depositSettingsErrors(form)).toEqual({});
    for (const holdMinutes of ["14", "1441", "", "1.5", "-20"]) {
      expect(depositSettingsErrors({ ...form, holdMinutes })).toEqual({ holdMinutes: "deposits.settings.errors.hold" });
    }
    expect(depositSettingsErrors({ ...form, holdMinutes: "15", refundHours: "0" })).toEqual({});
    expect(depositSettingsErrors({ ...form, refundHours: "721" })).toEqual({ refundHours: "deposits.settings.errors.refund" });
    // A number out of range never reaches the API: the stored one is kept.
    expect(depositSettingsBody({ ...form, holdMinutes: "5" }, STORED)).toBeNull();
  });

  it("makes a page the default without touching the other choices", () => {
    expect(defaultPageBody(STORED, "link_2")).toEqual({
      is_enabled: false,
      hold_minutes: 60,
      refund_cutoff_hours: 24,
      default_payment_link_id: "link_2",
    });
  });
});

describe("a new payment page", () => {
  it("needs a name and an https link", () => {
    expect(paymentLinkErrors({ label: " ", kind: "static", address: "" })).toEqual({
      label: "deposits.pages.errors.label",
      address: "deposits.pages.errors.address",
    });
    expect(paymentLinkErrors({ label: "Stripe", kind: "static", address: "http://buy.example.com/x" })).toEqual({
      address: "deposits.pages.refusals.linkNotHttps",
    });
    expect(paymentLinkErrors({ label: "x".repeat(81), kind: "static", address: "https://buy.example.com/x" })).toEqual({
      label: "deposits.pages.errors.label",
    });
  });

  it("fills in the amount only with a placeholder for it", () => {
    expect(paymentLinkErrors({ label: "Flitt", kind: "template", address: "https://pay.example.com/?ref={reference}" })).toEqual({
      address: "deposits.pages.refusals.templateInvalid",
    });
    expect(paymentLinkErrors({ label: "Flitt", kind: "template", address: "https://pay.example.com/?sum={amount}" })).toEqual({});
    expect(paymentLinkErrors({ label: "Flitt", kind: "template", address: "https://pay.example.com/?c={amount_minor}" })).toEqual({});
  });

  it("sends the page trimmed", () => {
    expect(paymentLinkBody({ label: " Flitt ", kind: "template", address: " https://pay.example.com/?sum={amount} " })).toEqual({
      label: "Flitt",
      kind: "template",
      address: "https://pay.example.com/?sum={amount}",
    });
  });
});
