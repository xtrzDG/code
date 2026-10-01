import { describe, expect, it } from "vitest";

import { countHandoffTabs, handoffFiltersQuery, handoffsOfTab, parseHandoffFilters } from "./handoffModel";

const handoffs = [
  { id: "low", status: "notified" as const, urgency: "low" as const, created_at: 1, resolved_at: null },
  { id: "done", status: "resolved" as const, urgency: "high" as const, created_at: 2, resolved_at: 9 },
  { id: "failed", status: "notification_failed" as const, urgency: "critical" as const, created_at: 3, resolved_at: null },
];

describe("handoff tabs", () => {
  it("count open and resolved handoffs", () => {
    expect(countHandoffTabs(handoffs)).toEqual({ open: 2, resolved: 1, all: 3 });
  });

  it("show open handoffs by urgency", () => {
    expect(handoffsOfTab(handoffs, "open").map((item) => item.id)).toEqual(["failed", "low"]);
    expect(handoffsOfTab(handoffs, "resolved").map((item) => item.id)).toEqual(["done"]);
    expect(handoffsOfTab(handoffs, "all").map((item) => item.id)).toEqual(["failed", "low", "done"]);
  });
});

describe("handoff filters in the URL", () => {
  it("default to open handoffs without test activity", () => {
    expect(parseHandoffFilters({})).toEqual({ tab: "open", includeTest: false });
    expect(parseHandoffFilters({ tab: "resolved", test: "1" })).toEqual({ tab: "resolved", includeTest: true });
    expect(parseHandoffFilters({ tab: "closed" })).toEqual({ tab: "open", includeTest: false });
    expect(handoffFiltersQuery({ tab: "all", includeTest: true })).toBe("tab=all&test=1");
    expect(handoffFiltersQuery({ tab: "open", includeTest: false })).toBe("");
  });
});
