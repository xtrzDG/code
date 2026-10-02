import { describe, expect, it } from "vitest";

import {
  afterResolve,
  handoffFiltersQuery,
  handoffTabCounts,
  isOpenQuery,
  parseHandoffFilters,
  resolvedLocally,
  withResolvedCounts,
  withResolvedHandoff,
} from "./handoffModel";

describe("handoff tabs", () => {
  it("ask the API for open or resolved handoffs", () => {
    expect(isOpenQuery("open")).toBe("true");
    expect(isOpenQuery("resolved")).toBe("false");
    expect(isOpenQuery("all")).toBeUndefined();
  });

  it("count open and resolved handoffs from the totals", () => {
    expect(handoffTabCounts({ open_count: 2, resolved_count: 1 })).toEqual({ open: 2, resolved: 1, all: 3 });
    expect(withResolvedCounts({ open_count: 2, resolved_count: 1 })).toEqual({ open_count: 1, resolved_count: 2 });
  });

  it("drop a resolved handoff from the open tab only", () => {
    const shown = [
      { id: "a", status: "notified" },
      { id: "b", status: "pending" },
    ];
    const resolved = { id: "a", status: "resolved" };
    expect(afterResolve(shown, resolved, "open").map((item) => item.id)).toEqual(["b"]);
    expect(afterResolve(shown, resolved, "all")[0]).toEqual(resolved);
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

describe("resolving in a cached list", () => {
  const open = { id: "h1", status: "notified" as const, resolved_at: null };
  const other = { id: "h2", status: "notified" as const, resolved_at: null };
  const data = { page: { open_count: 2, resolved_count: 5 }, items: [open, other], nextCursor: null };

  it("marks the handoff resolved now", () => {
    expect(resolvedLocally(open, 42)).toEqual({ id: "h1", status: "resolved", resolved_at: 42 });
  });

  it("drops it from the open tab and moves one count", () => {
    const after = withResolvedHandoff(data, resolvedLocally(open, 42), "open");
    expect(after.items.map((item) => item.id)).toEqual(["h2"]);
    expect(after.page).toEqual({ open_count: 1, resolved_count: 6 });
  });

  it("keeps it, resolved, in the all tab", () => {
    const after = withResolvedHandoff(data, resolvedLocally(open, 42), "all");
    expect(after.items[0]).toMatchObject({ id: "h1", status: "resolved" });
  });

  it("does not count a handoff twice", () => {
    const resolved = { ...open, status: "resolved" as const, resolved_at: 1 };
    const after = withResolvedHandoff({ ...data, items: [resolved] }, resolved, "all");
    expect(after.page).toBe(data.page);
  });
});
