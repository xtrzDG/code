import { describe, expect, it } from "vitest";

import { countByStatus, leadFiltersQuery, leadsOfTab, parseLeadFilters, withLeadStatus } from "./leadModel";

const leads = [
  { id: "a", status: "new" as const },
  { id: "b", status: "won" as const },
  { id: "c", status: "new" as const },
];

describe("lead tabs", () => {
  it("count every status", () => {
    expect(countByStatus(leads)).toEqual({ all: 3, new: 2, in_progress: 0, won: 1, lost: 0 });
  });

  it("filter by tab", () => {
    expect(leadsOfTab(leads, "new").map((lead) => lead.id)).toEqual(["a", "c"]);
    expect(leadsOfTab(leads, "all")).toHaveLength(3);
  });

  it("apply a status change locally", () => {
    expect(withLeadStatus(leads, "a", "lost")[0]).toEqual({ id: "a", status: "lost" });
    expect(withLeadStatus(leads, "x", "lost")).toEqual(leads);
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
