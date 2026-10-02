import { describe, expect, it } from "vitest";

import {
  afterStatusChange,
  countsByTab,
  leadFiltersQuery,
  parseLeadFilters,
  withLeadStatus,
  withStatusCounts,
} from "./leadModel";

const leads = [
  { id: "a", status: "new" as const },
  { id: "b", status: "won" as const },
  { id: "c", status: "new" as const },
];

const statusCounts = [
  { status: "new" as const, count: 2 },
  { status: "in_progress" as const, count: 0 },
  { status: "won" as const, count: 1 },
  { status: "lost" as const, count: 0 },
];

describe("lead tabs", () => {
  it("count every status from the API's counts", () => {
    expect(countsByTab(statusCounts)).toEqual({ all: 3, new: 2, in_progress: 0, won: 1, lost: 0 });
    expect(countsByTab([])).toEqual({ all: 0, new: 0, in_progress: 0, won: 0, lost: 0 });
  });

  it("move a lead between counts", () => {
    const moved = withStatusCounts({ status_counts: statusCounts }, "new", "lost");
    expect(countsByTab(moved.status_counts)).toEqual({ all: 3, new: 1, in_progress: 0, won: 1, lost: 1 });
    expect(withStatusCounts({ status_counts: statusCounts }, "won", "won").status_counts).toBe(statusCounts);
  });

  it("apply a status change locally and drop the lead from another status tab", () => {
    expect(afterStatusChange(leads, "a", "lost", "all")[0]).toEqual({ id: "a", status: "lost" });
    expect(afterStatusChange(leads, "a", "lost", "new").map((lead) => lead.id)).toEqual(["b", "c"]);
    expect(afterStatusChange(leads, "x", "lost", "new")).toEqual(leads);
  });
});

describe("lead filters in the URL", () => {
  it("round-trip and ignore unknown statuses", () => {
    expect(leadFiltersQuery({ tab: "in_progress", includeTest: true })).toBe("status=in_progress&test=1");
    expect(parseLeadFilters({ status: "in_progress", test: "1" })).toEqual({ tab: "in_progress", includeTest: true });
    expect(parseLeadFilters({ status: "open" })).toEqual({ tab: "all", includeTest: false });
    expect(leadFiltersQuery({ tab: "all", includeTest: false })).toBe("");
  });
});

describe("withLeadStatus", () => {
  const data = { page: { status_counts: statusCounts }, items: leads, nextCursor: "c" };

  it("moves the lead and its count in the cached tab", () => {
    const moved = withLeadStatus(data, "a", "new", "won", "all");
    expect(moved.items.map((lead) => [lead.id, lead.status])).toEqual([
      ["a", "won"],
      ["b", "won"],
      ["c", "new"],
    ]);
    expect(countsByTab(moved.page.status_counts)).toEqual({ all: 3, new: 1, in_progress: 0, won: 2, lost: 0 });
    expect(moved.nextCursor).toBe("c");
  });

  it("drops the lead from a tab of its old status", () => {
    expect(withLeadStatus(data, "a", "new", "lost", "new").items.map((lead) => lead.id)).toEqual(["b", "c"]);
  });
});
