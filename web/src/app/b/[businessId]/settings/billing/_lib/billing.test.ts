import { describe, expect, it } from "vitest";

import {
  billingNotices,
  canCancel,
  canPay,
  checkoutReturnUrl,
  daysUntil,
  hasEstimatedPrices,
  isInvoiceOpen,
  maxAnnualDiscount,
  monthlyEquivalentMinor,
  needsSubscription,
  noSubscriptionText,
  planActions,
  planPrice,
  quotedMoneyText,
  sortInvoices,
  type BillingOverview,
  type InvoiceView,
  type PlanQuote,
  type QuotedMoney,
  type SubscriptionView,
} from "./billing";

const DAY = 86_400_000_000;
const NOW = 1_790_000_000_000_000;

const money = (amount: number, currency = "GEL", estimated = false): QuotedMoney => ({
  money: { amount_minor: amount, currency_code: currency },
  text: "",
  is_estimated: estimated,
});

const subscription = (overrides: Partial<SubscriptionView> = {}): SubscriptionView => ({
  id: "subscription_1",
  plan_key: "voice_and_chat",
  plan_name: "Voice + chat",
  billing_period: "monthly",
  status: "active",
  price: money(51_700),
  trial_ends_at: null,
  period_start: NOW - 10 * DAY,
  period_end: NOW + 20 * DAY,
  grace_until: null,
  has_auto_debit: true,
  ...overrides,
});

const invoice = (overrides: Partial<InvoiceView> = {}): InvoiceView => ({
  id: "invoice_1",
  kind: "service_period",
  description: "Service",
  status: "paid",
  amount: money(51_700),
  period_start: NOW,
  period_end: NOW + 30 * DAY,
  issued_at: NOW,
  is_receipt_available: false,
  ...overrides,
});

const overview = (overrides: Partial<BillingOverview> = {}): BillingOverview => ({
  business_id: "business_1",
  currency_code: "GEL",
  display_language: "en",
  service_mode: "full",
  is_trial_available: false,
  does_trial_start_at_go_live: false,
  subscription: subscription(),
  usage: null,
  invoices: [],
  ...overrides,
});

const quote = (overrides: Partial<PlanQuote> = {}): PlanQuote => ({
  plan_key: "chat",
  name: "Chat",
  description: "",
  included_voice_minutes: 0,
  included_dialogs: 1000,
  channels: ["telegram"],
  is_voice_included: false,
  trial_days: 14,
  grace_period_days: 7,
  annual_discount_percent: 15,
  monthly_price: money(9_900, "EUR"),
  annual_price: money(100_980, "EUR"),
  setup_fee: money(15_000, "EUR"),
  overage_price_per_minute: money(15, "EUR"),
  local_monthly_price: money(29_300),
  local_annual_price: money(298_860),
  local_setup_fee: money(44_300),
  local_overage_price_per_minute: money(44, "GEL", true),
  ...overrides,
});

describe("invoices", () => {
  it("treats issued and failed invoices as open", () => {
    expect(isInvoiceOpen({ status: "issued" })).toBe(true);
    expect(isInvoiceOpen({ status: "failed" })).toBe(true);
    expect(isInvoiceOpen({ status: "paid" })).toBe(false);
    expect(isInvoiceOpen({ status: "void" })).toBe(false);
  });

  it("sorts newest first", () => {
    const sorted = sortInvoices([invoice({ id: "a", issued_at: 1 }), invoice({ id: "b", issued_at: 3 }), invoice({ id: "c", issued_at: 2 })]);
    expect(sorted.map((item) => item.id)).toEqual(["b", "c", "a"]);
    expect(sortInvoices(undefined)).toEqual([]);
  });
});

describe("actions", () => {
  it("offers payment unless automatic payment covers everything", () => {
    expect(canPay(overview({ subscription: null }))).toBe(false);
    expect(canPay(overview())).toBe(false);
    expect(canPay(overview({ invoices: [invoice({ status: "issued" })] }))).toBe(true);
    expect(canPay(overview({ subscription: subscription({ has_auto_debit: false }) }))).toBe(true);
    expect(canPay(overview({ subscription: subscription({ status: "trialing", has_auto_debit: false }) }))).toBe(true);
    expect(canPay(overview({ subscription: subscription({ status: "cancelled" }) }))).toBe(true);
  });

  it("cancels only a subscription that is not cancelled yet", () => {
    expect(canCancel(overview())).toBe(true);
    expect(canCancel(overview({ subscription: subscription({ status: "cancelled" }) }))).toBe(false);
    expect(canCancel(overview({ subscription: subscription({ status: "incomplete" }) }))).toBe(false);
    expect(canCancel(overview({ subscription: null }))).toBe(false);
  });

  it("lets a subscription waiting for its first payment be paid", () => {
    expect(
      canPay(overview({ subscription: subscription({ status: "incomplete", has_auto_debit: false }), invoices: [invoice({ status: "issued" })] })),
    ).toBe(true);
  });

  it("switches plans during a trial or an active subscription", () => {
    const voice = quote({ plan_key: "voice_and_chat" });
    expect(planActions(voice, "monthly", overview())).toEqual({ isCurrent: true, actions: [] });
    expect(planActions(voice, "annual", overview())).toEqual({ isCurrent: false, actions: ["switch"] });
    expect(planActions(quote(), "monthly", overview())).toEqual({ isCurrent: false, actions: ["switch"] });
    expect(planActions(quote(), "monthly", overview({ subscription: subscription({ status: "trialing" }) })).actions).toEqual(["switch"]);
  });

  it("offers the trial first and subscribing without a subscription", () => {
    const fresh = overview({ subscription: null, is_trial_available: true });
    expect(planActions(quote(), "monthly", fresh)).toEqual({ isCurrent: false, actions: ["trial", "subscribe"] });
    expect(planActions(quote({ trial_days: 0 }), "monthly", fresh).actions).toEqual(["subscribe"]);
    expect(planActions(quote(), "annual", overview({ subscription: null })).actions).toEqual(["subscribe"]);
  });

  it("subscribes again after the trial, an overdue payment or a cancellation", () => {
    for (const status of ["past_due", "cancelled", "incomplete"] as const) {
      const ended = overview({ subscription: subscription({ status, plan_key: "chat" }) });
      expect(needsSubscription(ended)).toBe(true);
      expect(planActions(quote(), "monthly", ended)).toEqual({ isCurrent: true, actions: ["subscribe"] });
      expect(planActions(quote({ plan_key: "plus" }), "monthly", ended)).toEqual({ isCurrent: false, actions: ["subscribe"] });
    }
    expect(needsSubscription(overview())).toBe(false);
    expect(needsSubscription(overview({ subscription: null }))).toBe(true);
  });
});

describe("billingNotices", () => {
  it("is quiet for a paid active subscription", () => {
    expect(billingNotices(overview(), NOW)).toEqual([]);
  });

  it("puts the leads-only mode and overdue payment first", () => {
    const notices = billingNotices(
      overview({
        service_mode: "leads_only",
        subscription: subscription({ status: "past_due", grace_until: NOW + 3 * DAY }),
        invoices: [invoice({ status: "failed" })],
      }),
      NOW,
    );
    expect(notices).toEqual([{ kind: "leadsOnly" }, { kind: "pastDue", graceUntil: NOW + 3 * DAY }]);
  });

  it("counts the trial days and unpaid invoices", () => {
    const notices = billingNotices(
      overview({
        subscription: subscription({ status: "trialing", trial_ends_at: NOW + 13 * DAY + 5 }),
        invoices: [invoice({ status: "issued" }), invoice({ id: "2", status: "issued" })],
      }),
      NOW,
    );
    expect(notices).toEqual([
      { kind: "unpaid", count: 2 },
      { kind: "trial", endsAt: NOW + 13 * DAY + 5, daysLeft: 14 },
    ]);
  });

  it("warns about the package from 80 %", () => {
    const usage = {
      period_start: NOW,
      period_end: NOW + 30 * DAY,
      used_voice_minutes: 330,
      included_voice_minutes: 400,
      voice_usage_percent: 82,
      used_dialogs: 1600,
      included_dialogs: 1500,
      dialog_usage_percent: 106,
      overage_voice_minutes: 0,
      overage_price_per_minute: money(44),
      overage_cost: money(0),
    };
    expect(billingNotices(overview({ usage }), NOW)).toEqual([
      { kind: "usage", unit: "voice", percent: 82, isExceeded: false },
      { kind: "usage", unit: "dialogs", percent: 106, isExceeded: true },
    ]);
    expect(billingNotices(overview({ usage: { ...usage, voice_usage_percent: null, dialog_usage_percent: 10 } }), NOW)).toEqual([]);
  });

  it("asks for the first payment of a new subscription instead of listing unpaid invoices", () => {
    expect(
      billingNotices(
        overview({ subscription: subscription({ status: "incomplete" }), invoices: [invoice({ status: "issued" })] }),
        NOW,
      ),
    ).toEqual([{ kind: "incomplete" }]);
  });

  it("tells when a cancelled subscription ends", () => {
    expect(billingNotices(overview({ subscription: subscription({ status: "cancelled" }) }), NOW)).toEqual([
      { kind: "cancelled", until: NOW + 20 * DAY },
    ]);
  });
});

describe("plan prices", () => {
  it("prefers local prices and falls back to the plan currency", () => {
    expect(planPrice(quote(), "monthly").money).toEqual({ amount_minor: 29_300, currency_code: "GEL" });
    expect(planPrice(quote(), "annual").money.amount_minor).toBe(298_860);
    expect(planPrice(quote({ local_monthly_price: null }), "monthly").money.currency_code).toBe("EUR");
  });

  it("computes the monthly equivalent and the best discount", () => {
    expect(monthlyEquivalentMinor(money(298_860))).toBe(24_905);
    expect(maxAnnualDiscount([quote(), quote({ annual_discount_percent: 20 })])).toBe(20);
    expect(maxAnnualDiscount([])).toBe(0);
  });

  it("spots converted prices", () => {
    expect(hasEstimatedPrices([quote()], "monthly")).toBe(true);
    expect(hasEstimatedPrices([quote({ local_overage_price_per_minute: money(44) })], "monthly")).toBe(false);
  });

  it("marks converted amounts with ≈", () => {
    const format = (minor: number, currency: string) => `${minor} ${currency}`;
    expect(quotedMoneyText(money(44, "GEL", true), format)).toBe("≈ 44 GEL");
    expect(quotedMoneyText(money(9_900, "EUR"), format)).toBe("9900 EUR");
  });
});

describe("misc", () => {
  it("rounds days up and never goes negative", () => {
    expect(daysUntil(NOW + DAY, NOW)).toBe(1);
    expect(daysUntil(NOW + DAY + 1, NOW)).toBe(2);
    expect(daysUntil(NOW - DAY, NOW)).toBe(0);
  });

  it("builds the return page of the checkout", () => {
    expect(checkoutReturnUrl("https://app.example.com/", "/b/business_1/billing")).toBe(
      "https://app.example.com/b/business_1/billing?checkout=return",
    );
  });
});

describe("noSubscriptionText", () => {
  it("says the trial starts at go-live before the first launch", () => {
    expect(noSubscriptionText(overview({ subscription: null, is_trial_available: true, does_trial_start_at_go_live: true }))).toBe(
      "billing.noSubscriptionTrialAtGoLive",
    );
  });

  it("offers the trial or a plan otherwise", () => {
    expect(noSubscriptionText(overview({ subscription: null, is_trial_available: true }))).toBe("billing.noSubscriptionDescription");
    expect(noSubscriptionText(overview({ subscription: null, is_trial_available: false }))).toBe("billing.noSubscriptionNoTrial");
  });
});
