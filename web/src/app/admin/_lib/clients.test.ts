import { describe, expect, it } from "vitest";

import {
  EMPTY_FILTERS,
  adminClientPath,
  clientUsagePercent,
  clientsQuery,
  hasFilters,
  isCriticalIssue,
  type AdminClientSummary,
} from "./clients";

type ClientOverrides = Partial<Omit<AdminClientSummary, "cost">> & {
  margin?: number | null;
  marginPercent?: number | null;
  cost?: number;
  revenue?: number;
};

const client = (overrides: ClientOverrides): AdminClientSummary => {
  const { margin = null, marginPercent = null, cost = 0, revenue = 0, ...rest } = overrides;
  return {
    business_id: "business_1",
    name: "Café",
    country_code: "GE",
    niche_key: "restaurant",
    currency_code: "GEL",
    business_status: "live",
    service_mode: "full",
    plan_key: "voice_and_chat",
    subscription_status: "active",
    billing_period: "monthly",
    period_end: null,
    grace_until: null,
    has_auto_debit: true,
    published_version_number: 1,
    published_at: null,
    last_test_score: null,
    failed_tests: 0,
    handoffs_last_7_days: 0,
    tool_errors_last_7_days: 0,
    open_unanswered_questions: 0,
    used_voice_minutes: 0,
    included_voice_minutes: 400,
    used_dialogs: 0,
    included_dialogs: 1500,
    health_status: "healthy",
    health_issues: [],
    cost: {
      business_id: "business_1",
      period_start: 0,
      period_end: 1,
      usage_cost_lines: [],
      llm_cost_micro_usd: 0,
      provider_cost_micro_usd: cost,
      revenue: { amount_minor: revenue, currency_code: "GEL" },
      provider_cost: null,
      margin: margin === null ? null : { amount_minor: margin, currency_code: "GEL" },
      margin_percent: marginPercent,
      exchange_rate: null,
      planned_monthly_provider_cost: null,
    },
    ...rest,
  };
};

const clients = [
  client({ business_id: "b_a", name: "Alpha", health_status: "healthy", used_voice_minutes: 200, marginPercent: 60, margin: 300, cost: 10, revenue: 500 }),
  client({ business_id: "b_b", name: "Bravo", health_status: "critical", health_issues: ["negative_margin"], marginPercent: -20, margin: -50, cost: 90, revenue: 100 }),
  client({ business_id: "b_c", name: "Charlie", health_status: "attention", business_status: "testing", used_dialogs: 1500, cost: 30, revenue: 0 }),
];

describe("clientsQuery", () => {
  it("sends only the filters that are set", () => {
    expect(clientsQuery(EMPTY_FILTERS, undefined, "health")).toEqual({ sort: "health" });
    expect(
      clientsQuery({ query: "brav", health: "critical", status: "testing", country: "GE", niche: "restaurant" }, "brav", "margin"),
    ).toEqual({ search: "brav", health: "critical", status: "testing", country: "GE", niche: "restaurant", sort: "margin" });
    expect(hasFilters(EMPTY_FILTERS)).toBe(false);
    expect(hasFilters({ ...EMPTY_FILTERS, query: " x " })).toBe(true);
    expect(hasFilters({ ...EMPTY_FILTERS, country: "IT" })).toBe(true);
  });
});

describe("summaries", () => {
  it("takes the fuller package", () => {
    expect(clientUsagePercent(clients[0]!)).toBe(50);
    expect(clientUsagePercent(clients[2]!)).toBe(100);
    expect(clientUsagePercent(client({ included_voice_minutes: 0, included_dialogs: 0 }))).toBeNull();
    expect(clientUsagePercent(client({ included_voice_minutes: 0, used_dialogs: 150 }))).toBe(10);
  });

  it("marks limiting issues as critical", () => {
    expect(isCriticalIssue("leads_only_mode")).toBe(true);
    expect(isCriticalIssue("negative_margin")).toBe(true);
    expect(isCriticalIssue("open_questions")).toBe(false);
  });

  it("links to the client page", () => {
    expect(adminClientPath("business_1")).toBe("/admin/clients/business_1");
  });
});
