import { describe, expect, it } from "vitest";

import { dataTaskPercent, dataTaskTarget, dataTaskTone } from "./dataTasks";

describe("data tasks: what a task fills and how far it is", () => {
  it("names the column of a backfill and the collection of a migration", () => {
    expect(dataTaskTarget({ collection_name: "contacts", field: "last_seen_at" })).toBe("contacts.last_seen_at");
    expect(dataTaskTarget({ collection_name: "contacts", field: null })).toBe("contacts");
  });

  it("measures the walk against the estimated rows, never 100 before the end", () => {
    expect(dataTaskPercent({ status: "running", scanned_count: 2_500, row_estimate: 10_000 })).toBe(25);
    expect(dataTaskPercent({ status: "running", scanned_count: 12_000, row_estimate: 10_000 })).toBe(99);
    expect(dataTaskPercent({ status: "done", scanned_count: 0, row_estimate: null })).toBe(100);
    expect(dataTaskPercent({ status: "pending", scanned_count: 0, row_estimate: null })).toBeNull();
    expect(dataTaskPercent({ status: "pending", scanned_count: 0, row_estimate: 0 })).toBeNull();
  });

  it("colours failed red, open amber and done green", () => {
    expect(dataTaskTone("failed")).toBe("danger");
    expect(dataTaskTone("pending")).toBe("warning");
    expect(dataTaskTone("running")).toBe("warning");
    expect(dataTaskTone("done")).toBe("success");
  });
});
