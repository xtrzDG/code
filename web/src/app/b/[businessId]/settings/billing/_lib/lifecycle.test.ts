import { describe, expect, it } from "vitest";

import {
  billingNotices,
  canPay,
  planActions,
  type BillingOverview,
  type InvoiceView,
  type PlanQuote,
  type SubscriptionView,
} from "./billing";
import {
  CANCELLATION_DETAILS_MAX,
  CANCELLATION_REASONS,
  allowedPauseMonths,
  cancellationDetails,
  offerFor,
  pauseCardState,
  pauseEndFor,
  pauseMonthChoices,
  type PauseOptions,
  type SubscriptionLifecycle,
} from "./lifecycle";

const DAY = 86_400_000_000;
const NOW = 1_790_000_000_000_000;
const money = (amount: number) => ({ money: { amount_minor: amount, currency_code: "GEL" }, text: "", is_estimated: false });

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

const overview = (overrides: Partial<SubscriptionView> = {}, rest: Partial<BillingOverview> = {}): BillingOverview => ({
  business_id: "business_1",
  currency_code: "GEL",
  display_language: "en",
  service_mode: "full",
  is_trial_available: false,
  does_trial_start_at_go_live: false,
  subscription: subscription(overrides),
  usage: null,
  invoices: [],
  ...rest,
});

const pause = (overrides: Partial<PauseOptions> = {}): PauseOptions => ({
  is_enabled: true,
  is_available: true,
  unavailable_reason: null,
  price_percent: 15,
  monthly_price: money(7_755),
  starts_at: NOW + 20 * DAY,
  ends_at: [NOW + 50 * DAY, NOW + 81 * DAY],
  max_months: 2,
  paused_months: 2,
  cap_months: 4,
  window_months: 12,
  ...overrides,
});

const lifecycle = (pauseOverrides: Partial<PauseOptions> = {}): SubscriptionLifecycle => ({
  business_id: "business_1",
  pause: pause(pauseOverrides),
  offers: [
    { reason: "seasonal_break", offer: { kind: "pause", pause_months: 2, pause_price: money(7_755) } },
    { reason: "too_expensive", offer: { kind: "downgrade", plan_key: "chat", plan_name: "Chat", plan_price: money(24_700) } },
    { reason: "closing_business", offer: null },
  ],
});

describe("the cancel dialog", () => {
  it("lists every reason once, seasonal first and 'other' last", () => {
    expect(new Set(CANCELLATION_REASONS).size).toBe(8);
    expect(CANCELLATION_REASONS[0]).toBe("seasonal_break");
    expect(CANCELLATION_REASONS.at(-1)).toBe("other");
  });

  it("offers what the reason brings, nothing before a reason or without the offers", () => {
    expect(offerFor(lifecycle(), "seasonal_break")?.kind).toBe("pause");
    expect(offerFor(lifecycle(), "too_expensive")?.plan_name).toBe("Chat");
    expect(offerFor(lifecycle(), "closing_business")).toBeNull();
    expect(offerFor(lifecycle(), "other")).toBeNull();
    expect(offerFor(lifecycle(), null)).toBeNull();
    expect(offerFor(undefined, "seasonal_break")).toBeNull();
  });

  it("sends the owner's words trimmed, none when blank, never past the limit", () => {
    expect(cancellationDetails("  closed till May  ")).toBe("closed till May");
    expect(cancellationDetails("   ")).toBeNull();
    expect(cancellationDetails("x".repeat(CANCELLATION_DETAILS_MAX + 5))).toHaveLength(CANCELLATION_DETAILS_MAX);
  });
});

describe("the pause card", () => {
  it("is hidden until the platform turns pausing on, and without data", () => {
    expect(pauseCardState(overview(), lifecycle({ is_enabled: false, is_available: false, unavailable_reason: "feature_off" }))).toEqual({
      kind: "hidden",
    });
    expect(pauseCardState(undefined, lifecycle())).toEqual({ kind: "hidden" });
    expect(pauseCardState(overview(), undefined)).toEqual({ kind: "hidden" });
  });

  it("offers a pause from the end of the paid period", () => {
    const state = pauseCardState(overview(), lifecycle());
    expect(state.kind).toBe("available");
  });

  it("says why a pause is not possible", () => {
    expect(pauseCardState(overview(), lifecycle({ is_available: false, unavailable_reason: "not_monthly" }))).toEqual({
      kind: "unavailable",
      reason: "not_monthly",
    });
    expect(pauseCardState(overview(), lifecycle({ is_available: false, unavailable_reason: "allowance_used" })).kind).toBe(
      "unavailable",
    );
  });

  it("shows a scheduled pause and a running one, even with pausing turned off since", () => {
    const off = lifecycle({ is_enabled: false, is_available: false, unavailable_reason: "feature_off" });
    const scheduled = overview({ pause_starts_at: NOW + 20 * DAY, pause_until: NOW + 50 * DAY });
    expect(pauseCardState(scheduled, off)).toEqual({ kind: "scheduled", startsAt: NOW + 20 * DAY, until: NOW + 50 * DAY });
    const paused = overview({ status: "paused", pause_starts_at: NOW - DAY, pause_until: NOW + 29 * DAY });
    expect(pauseCardState(paused, off)).toEqual({ kind: "paused", until: NOW + 29 * DAY });
  });

  it("lists the allowed months and the end of each length", () => {
    expect(pauseMonthChoices(3)).toEqual([1, 2, 3]);
    expect(pauseMonthChoices(0)).toEqual([]);
    expect(pauseEndFor(pause(), 2)).toBe(NOW + 81 * DAY);
    expect(pauseEndFor(pause(), 3)).toBeNull();
    expect(pauseEndFor(undefined, 1)).toBeNull();
    expect(allowedPauseMonths(4, 2)).toBe(1);
    expect(allowedPauseMonths(2, 2)).toBe(2);
  });
});

describe("billing while paused", () => {
  const paused = overview(
    { status: "paused", has_auto_debit: false, pause_starts_at: NOW - DAY, pause_until: NOW + 29 * DAY },
    { service_mode: "leads_only" },
  );
  const chat: PlanQuote = {
    plan_key: "chat",
    name: "Chat",
    description: "",
    included_voice_minutes: 0,
    included_dialogs: 300,
    monthly_price: money(24_700),
    annual_price: money(247_000),
    trial_days: 14,
  } as unknown as PlanQuote;

  it("pays only the pause's own bill", () => {
    expect(canPay(paused)).toBe(false);
    const bill = { id: "invoice_1", status: "issued" } as InvoiceView;
    expect(canPay({ ...paused, invoices: [bill] })).toBe(true);
    const scheduled = overview({ has_auto_debit: false, pause_starts_at: NOW + 20 * DAY, pause_until: NOW + 50 * DAY });
    expect(canPay(scheduled)).toBe(false);
  });

  it("raises no requests-only alarm and offers no plan change", () => {
    expect(billingNotices(paused, NOW).map((notice) => notice.kind)).not.toContain("leadsOnly");
    expect(planActions(chat, "monthly", paused).actions).toEqual([]);
  });
});
